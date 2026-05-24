"""
E2E tests for Write intents: SUBMIT_MATCH_RESULT, EDIT_PLAYER_NICKNAME,
EDIT_MATCH_SCORE, DELETE_MATCH, DELETE_TEAM.

Write intent handlers never mutate the backend — they return a pre-filled
payload (method, url, body) for the frontend to review and submit. These
tests verify the shape and content of that payload.

Prerequisites (set in .env):
  TEST_LEAGUE_ID  — uuid of a freshly created league
  TEST_HOST_TOKEN — host token returned when the league was created
  GROQ_API_KEY    — valid Groq key

Tests that look up existing players/matches by nickname use the `seeded_league`
fixture, which submits matches to the backend at the start of the session automatically.
"""

import pytest
from httpx import AsyncClient


def _assert_prefilled_payload(body: dict, expected_method: str, url_contains: str) -> dict:
    """Helper: asserts the standard write-intent payload shape and returns the body dict."""
    assert body["data_type"] != "ERROR", f"Got ERROR: {body['data'].get('error_message')}"
    assert body["data_type"] != "CLARIFICATION_QUESTION", (
        f"Got clarification: {body['data'].get('question')}"
    )
    data = body["data"]
    assert data["method"] == expected_method
    assert url_contains in data["url"], f"Expected '{url_contains}' in URL: {data['url']}"
    assert "{" not in data["url"], f"URL still has unresolved placeholder: {data['url']}"
    return data["body"]


# ---------------------------------------------------------------------------
# SUBMIT_MATCH_RESULT
# ---------------------------------------------------------------------------

class TestSubmitMatchResult:

    async def test_submit_basic_match(self, client: AsyncClient, league_id: str):
        response = await client.post(
            f"/leagues/{league_id}/chat",
            json={
                "client_message": "Alice and Bob beat Charlie and Diana 6 to 3",
                "last_server_message": "",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["data_type"] == "SUBMIT_MATCH_RESULT"
        payload_body = _assert_prefilled_payload(body, "POST", f"/leagues/{league_id}/matches")

        assert payload_body["team1_nicknames"]["value"] == ["Alice", "Bob"]
        assert payload_body["team2_nicknames"]["value"] == ["Charlie", "Diana"]
        assert payload_body["team1_score"]["value"] == "6"
        assert payload_body["team2_score"]["value"] == "3"

    async def test_submit_match_slash_notation(self, client: AsyncClient, league_id: str):
        response = await client.post(
            f"/leagues/{league_id}/chat",
            json={
                "client_message": "submit result: John/Sarah beat Mike/Emma 6-2",
                "last_server_message": "",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["data_type"] == "SUBMIT_MATCH_RESULT"
        payload_body = _assert_prefilled_payload(body, "POST", f"/leagues/{league_id}/matches")
        # Scores are optional chat params — verify values when the LLM extracted them.
        if payload_body["team1_score"]["value"] is not None:
            assert payload_body["team1_score"]["value"] == "6"
        if payload_body["team2_score"]["value"] is not None:
            assert payload_body["team2_score"]["value"] == "2"

    async def test_submit_prefilled_body_marks_fields_required_for_downstream_api(
        self, client: AsyncClient, league_id: str
    ):
        """Chat params are optional for resolution; the prefilled POST body still marks API fields required."""
        response = await client.post(
            f"/leagues/{league_id}/chat",
            json={
                "client_message": "record a match: Alice and Bob vs Charlie and Diana, 7-5",
                "last_server_message": "",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["data_type"] == "SUBMIT_MATCH_RESULT"
        payload_body = body["data"]["body"]
        assert payload_body["team1_nicknames"]["required"] is True
        assert payload_body["team2_nicknames"]["required"] is True
        assert payload_body["team1_score"]["required"] is True
        assert payload_body["team2_score"]["required"] is True


# ---------------------------------------------------------------------------
# EDIT_PLAYER_NICKNAME
# ---------------------------------------------------------------------------

@pytest.mark.usefixtures("seeded_league")
class TestEditPlayerNickname:

    async def test_rename_existing_player(
        self, client: AsyncClient, league_id: str, host_token: str
    ):
        response = await client.post(
            f"/leagues/{league_id}/chat",
            headers={"X-Host-Token": host_token},
            json={
                "client_message": "rename Alice to Alicia",
                "last_server_message": "",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["data_type"] == "EDIT_PLAYER_NICKNAME"
        payload_body = _assert_prefilled_payload(
            body, "PATCH", f"/admin/leagues/{league_id}/players/"
        )
        assert payload_body["new_nickname"]["value"] == "Alicia"

    async def test_rename_player_not_found_returns_error(
        self, client: AsyncClient, league_id: str, host_token: str
    ):
        response = await client.post(
            f"/leagues/{league_id}/chat",
            headers={"X-Host-Token": host_token},
            json={
                "client_message": "rename NonExistentXYZ to Something",
                "last_server_message": "",
            },
        )
        assert response.status_code == 200
        body = response.json()
        # LLM may return CLARIFICATION_QUESTION (low confidence on invented names)
        # or ERROR (502) when the intent is classified but the backend can't find the player.
        # Both are valid safe outcomes — the system must never return a success payload.
        assert body["data_type"] in ("ERROR", "CLARIFICATION_QUESTION")
        if body["data_type"] == "ERROR":
            assert body["data"]["status_code"] == 502


# ---------------------------------------------------------------------------
# EDIT_MATCH_SCORE (picker flow)
# ---------------------------------------------------------------------------

def _assert_edit_match_score_picker_shape(
    body: dict, league_id: str
) -> dict:
    """Asserts the picker-flow EDIT_MATCH_SCORE response shape and returns body['data']."""
    assert body["data_type"] != "ERROR", f"Got ERROR: {body['data'].get('error_message')}"
    assert body["data_type"] != "CLARIFICATION_QUESTION", (
        f"Got clarification: {body['data'].get('question')}"
    )
    assert body["data_type"] == "EDIT_MATCH_SCORE"
    data = body["data"]
    assert data["method"] == "PATCH"
    assert data["league_id"] == league_id
    # The intent now targets the player-facing edit route (no `/admin/`);
    # admin requests still work because the backend bypasses the
    # player-edit window when `X-Host-Token` is attached on submission.
    assert data["url_template"].endswith(
        f"/leagues/{league_id}/matches/{{match_id}}"
    )
    assert "/admin/" not in data["url_template"], (
        "EDIT_MATCH_SCORE url_template must target the player route, "
        "not /admin/. The frontend chooses whether to attach X-Host-Token."
    )
    assert isinstance(data["matches"], list)
    assert isinstance(data["player_filters"], list) and data["player_filters"]
    body_schema = data["body_schema"]
    assert body_schema["team1_score"] == {"type": "string", "required": True}
    assert body_schema["team2_score"] == {"type": "string", "required": True}
    return data


def _match_has_all(match: dict, nicknames: list[str]) -> bool:
    in_match = {
        (match.get("team1_player1_nickname") or "").lower(),
        (match.get("team1_player2_nickname") or "").lower(),
        (match.get("team2_player1_nickname") or "").lower(),
        (match.get("team2_player2_nickname") or "").lower(),
    }
    return {n.lower() for n in nicknames}.issubset(in_match)


@pytest.mark.usefixtures("seeded_league")
class TestEditMatchScore:
    """EDIT_MATCH_SCORE is now a player-accessible intent (no X-Host-Token
    required at the chat layer). The picker tests therefore run WITHOUT
    the host-token header to exercise the realistic player flow. One
    admin-parity test below confirms that requests WITH the token still
    work — the chat server should be indifferent to the header for this
    intent."""

    async def test_picker_returns_matches_for_one_player(
        self, client: AsyncClient, league_id: str
    ):
        response = await client.post(
            f"/leagues/{league_id}/chat",
            json={
                "client_message": "edit match score for Alice",
                "last_server_message": "",
            },
        )
        assert response.status_code == 200
        body = response.json()
        data = _assert_edit_match_score_picker_shape(body, league_id)
        assert len(data["matches"]) >= 1, (
            "Expected at least one seeded match containing Alice."
        )
        for match in data["matches"]:
            assert _match_has_all(match, ["Alice"])
            assert "match_id" in match
            assert "team1_score" in match
            assert "team2_score" in match

    async def test_picker_filters_by_two_players_all_of(
        self, client: AsyncClient, league_id: str
    ):
        response = await client.post(
            f"/leagues/{league_id}/chat",
            json={
                "client_message": "fix a match score for Alice and Charlie",
                "last_server_message": "",
            },
        )
        assert response.status_code == 200
        body = response.json()
        data = _assert_edit_match_score_picker_shape(body, league_id)
        # Only the Alice/Bob vs Charlie/Diana match contains both Alice AND Charlie.
        assert len(data["matches"]) >= 1
        for match in data["matches"]:
            assert _match_has_all(match, ["Alice", "Charlie"])

    async def test_picker_returns_empty_when_no_match_contains_all(
        self, client: AsyncClient, league_id: str
    ):
        # Charlie and Emma are seeded but never played in the same match.
        response = await client.post(
            f"/leagues/{league_id}/chat",
            json={
                "client_message": "edit a match score involving Charlie and Emma",
                "last_server_message": "",
            },
        )
        assert response.status_code == 200
        body = response.json()
        # Empty list is NOT an error — it's a normal result with explanation.
        assert body["data_type"] == "EDIT_MATCH_SCORE"
        data = body["data"]
        assert data["matches"] == []
        # server_message must clearly explain the ALL semantics so the user understands.
        msg = (body.get("server_message") or "").lower()
        assert "all" in msg, f"Expected ALL semantics in server_message, got: {msg}"

    async def test_picker_no_player_returns_error_or_clarification(
        self, client: AsyncClient, league_id: str
    ):
        response = await client.post(
            f"/leagues/{league_id}/chat",
            json={
                "client_message": "I want to edit a match score",
                "last_server_message": "",
            },
        )
        assert response.status_code == 200
        body = response.json()
        # With no extractable nicknames the handler returns 400, but the LLM
        # may also short-circuit with a clarification question — both are fine.
        assert body["data_type"] in ("ERROR", "CLARIFICATION_QUESTION")
        if body["data_type"] == "ERROR":
            assert body["data"]["status_code"] in (400, 422)

    async def test_picker_with_host_token_still_works_admin_parity(
        self, client: AsyncClient, league_id: str, host_token: str
    ):
        """Admin parity: a request with X-Host-Token must still return
        the same picker shape (url_template targets the player route
        regardless; admin bypasses the window at submission time)."""
        response = await client.post(
            f"/leagues/{league_id}/chat",
            headers={"X-Host-Token": host_token},
            json={
                "client_message": "edit match score for Alice",
                "last_server_message": "",
            },
        )
        assert response.status_code == 200
        body = response.json()
        data = _assert_edit_match_score_picker_shape(body, league_id)
        # url_template must be the player route even when the chat call
        # carries an admin token — the admin context only matters when
        # the frontend later PATCHes the backend.
        assert "/admin/" not in data["url_template"]
        assert len(data["matches"]) >= 1


# ---------------------------------------------------------------------------
# DELETE_MATCH
# ---------------------------------------------------------------------------

@pytest.mark.usefixtures("seeded_league")
class TestDeleteMatch:

    async def test_delete_existing_match_returns_payload(
        self, client: AsyncClient, league_id: str, host_token: str
    ):
        response = await client.post(
            f"/leagues/{league_id}/chat",
            headers={"X-Host-Token": host_token},
            json={
                "client_message": "delete the match between Alice/Bob and Charlie/Diana",
                "last_server_message": "",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["data_type"] == "DELETE_MATCH"
        _assert_prefilled_payload(body, "DELETE", f"/admin/leagues/{league_id}/matches/")
        # DELETE has no body fields
        assert body["data"]["body"] == {}

    async def test_delete_match_not_found_returns_error(
        self, client: AsyncClient, league_id: str, host_token: str
    ):
        response = await client.post(
            f"/leagues/{league_id}/chat",
            headers={"X-Host-Token": host_token},
            json={
                "client_message": "erase the match Xavier and Yolanda versus Zack and Wendy",
                "last_server_message": "",
            },
        )
        assert response.status_code == 200
        body = response.json()
        # LLM may return CLARIFICATION_QUESTION (low confidence on invented names)
        # or ERROR (502) when the intent is classified but the backend can't find the match.
        assert body["data_type"] in ("ERROR", "CLARIFICATION_QUESTION")
        if body["data_type"] == "ERROR":
            assert body["data"]["status_code"] == 502


# ---------------------------------------------------------------------------
# ADD_PLAYERS_TO_ROSTER (replaces v5 ADD_ALLOWLIST_ENTRIES)
# ---------------------------------------------------------------------------

class TestAddPlayersToRoster:

    async def test_add_players_to_roster_payload(
        self, client: AsyncClient, league_id: str, host_token: str
    ):
        response = await client.post(
            f"/leagues/{league_id}/chat",
            headers={"X-Host-Token": host_token},
            json={
                "client_message": "add Alex and Daniel to the roster",
                "last_server_message": "",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["data_type"] == "ADD_PLAYERS_TO_ROSTER"
        payload_body = _assert_prefilled_payload(
            body, "POST", f"/admin/leagues/{league_id}/players"
        )
        assert payload_body["nicknames"]["required"] is True
        assert isinstance(payload_body["nicknames"]["value"], list)
        assert len(payload_body["nicknames"]["value"]) >= 1

    async def test_add_players_to_roster_single_name(
        self, client: AsyncClient, league_id: str, host_token: str
    ):
        response = await client.post(
            f"/leagues/{league_id}/chat",
            headers={"X-Host-Token": host_token},
            json={
                "client_message": "allow Jason to play",
                "last_server_message": "",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["data_type"] == "ADD_PLAYERS_TO_ROSTER"
        payload_body = _assert_prefilled_payload(
            body, "POST", f"/admin/leagues/{league_id}/players"
        )
        assert payload_body["nicknames"]["value"] is not None

    async def test_add_players_to_roster_url_has_no_placeholder(
        self, client: AsyncClient, league_id: str, host_token: str
    ):
        response = await client.post(
            f"/leagues/{league_id}/chat",
            headers={"X-Host-Token": host_token},
            json={
                "client_message": "add Michael to the roster",
                "last_server_message": "",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["data_type"] == "ADD_PLAYERS_TO_ROSTER"
        url = body["data"]["url"]
        assert "{" not in url, f"URL still has unresolved placeholder: {url}"

    async def test_legacy_allowlist_phrase_still_maps_to_add_players_to_roster(
        self, client: AsyncClient, league_id: str, host_token: str
    ):
        """The retired 'allowlist' vocabulary remains in the registry's
        example_messages so existing user wording keeps working."""
        response = await client.post(
            f"/leagues/{league_id}/chat",
            headers={"X-Host-Token": host_token},
            json={
                "client_message": "add Michael to the allowlist",
                "last_server_message": "",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["data_type"] == "ADD_PLAYERS_TO_ROSTER"


# ---------------------------------------------------------------------------
# REMOVE_PLAYER_FROM_ROSTER (replaces v5 REMOVE_ALLOWLIST_ENTRY)
# ---------------------------------------------------------------------------

@pytest.mark.usefixtures("seeded_league")
class TestRemovePlayerFromRoster:

    async def test_remove_existing_roster_player_returns_payload(
        self, client: AsyncClient, league_id: str, host_token: str
    ):
        response = await client.post(
            f"/leagues/{league_id}/chat",
            headers={"X-Host-Token": host_token},
            json={
                "client_message": "remove alex from the roster",
                "last_server_message": "",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["data_type"] == "REMOVE_PLAYER_FROM_ROSTER"
        _assert_prefilled_payload(
            body, "DELETE", f"/admin/leagues/{league_id}/players/"
        )
        assert body["data"]["body"] == {}
        url = body["data"]["url"]
        assert "{" not in url, f"URL still has unresolved placeholder: {url}"

    async def test_remove_nonexistent_roster_player_returns_clarification(
        self, client: AsyncClient, league_id: str, host_token: str
    ):
        response = await client.post(
            f"/leagues/{league_id}/chat",
            headers={"X-Host-Token": host_token},
            json={
                "client_message": "remove NonExistentXYZ123 from the roster",
                "last_server_message": "",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["data_type"] in ("CLARIFICATION_QUESTION", "ERROR")


# ---------------------------------------------------------------------------
# DELETE_TEAM
# ---------------------------------------------------------------------------

@pytest.mark.usefixtures("seeded_league")
class TestDeleteTeam:

    async def test_delete_existing_team_returns_payload(
        self, client: AsyncClient, league_id: str, host_token: str
    ):
        response = await client.post(
            f"/leagues/{league_id}/chat",
            headers={"X-Host-Token": host_token},
            json={
                "client_message": "delete the team Alice and Bob",
                "last_server_message": "",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["data_type"] == "DELETE_TEAM"
        _assert_prefilled_payload(body, "DELETE", f"/admin/leagues/{league_id}/teams/")
        assert body["data"]["body"] == {}

    async def test_delete_team_not_found_returns_error(
        self, client: AsyncClient, league_id: str, host_token: str
    ):
        response = await client.post(
            f"/leagues/{league_id}/chat",
            headers={"X-Host-Token": host_token},
            json={
                "client_message": "delete the team formed by Nobody and Ghost",
                "last_server_message": "",
            },
        )
        assert response.status_code == 200
        body = response.json()
        # LLM may return CLARIFICATION_QUESTION (low confidence on invented names)
        # or ERROR (502) when the intent is classified but the backend can't find the team.
        assert body["data_type"] in ("ERROR", "CLARIFICATION_QUESTION")
        if body["data_type"] == "ERROR":
            assert body["data"]["status_code"] == 502
