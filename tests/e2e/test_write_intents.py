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
# EDIT_MATCH_SCORE
# ---------------------------------------------------------------------------

@pytest.mark.usefixtures("seeded_league")
class TestEditMatchScore:

    async def test_correct_existing_match_score(
        self, client: AsyncClient, league_id: str, host_token: str
    ):
        response = await client.post(
            f"/leagues/{league_id}/chat",
            headers={"X-Host-Token": host_token},
            json={
                "client_message": (
                    "fix the score for Alice and Bob vs Charlie and Diana "
                    "— it should be 6-2 not 6-3"
                ),
                "last_server_message": "",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["data_type"] == "EDIT_MATCH_SCORE"
        payload_body = _assert_prefilled_payload(
            body, "PATCH", f"/admin/leagues/{league_id}/matches/"
        )
        assert payload_body["team1_score"]["value"] == "6"
        assert payload_body["team2_score"]["value"] == "2"

    async def test_edit_score_match_not_found_returns_error(
        self, client: AsyncClient, league_id: str, host_token: str
    ):
        response = await client.post(
            f"/leagues/{league_id}/chat",
            headers={"X-Host-Token": host_token},
            json={
                "client_message": (
                    "correct the score for Xavier and Yolanda vs Zack and Wendy to 6-1"
                ),
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
