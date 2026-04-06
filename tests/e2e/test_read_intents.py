"""
E2E tests for Read intents: GET_STANDINGS, GET_MATCH_HISTORY, GET_ROSTER.

These tests send real natural-language messages to the chat endpoint, hit the
real Groq API for intent classification, and fetch real data from the backend.

Prerequisites (set in .env):
  TEST_LEAGUE_ID  — uuid of a freshly created league
  TEST_HOST_TOKEN — host token returned when the league was created
  GROQ_API_KEY    — valid Groq key

Tests that assert specific data exist use the `seeded_league` fixture, which
submits matches to the backend at the start of the session automatically.
"""

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# GET_STANDINGS
# ---------------------------------------------------------------------------

class TestGetStandings:

    async def test_show_standings(self, client: AsyncClient, league_id: str):
        response = await client.post(
            f"/leagues/{league_id}/chat",
            json={"client_message": "show me the standings", "last_server_message": ""},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["data_type"] == "GET_STANDINGS"
        assert "standings" in body["data"]
        assert isinstance(body["data"]["standings"], list)
        assert body["server_message"] == ""

    async def test_standings_phrase_variant(self, client: AsyncClient, league_id: str):
        response = await client.post(
            f"/leagues/{league_id}/chat",
            json={"client_message": "who's winning the league?", "last_server_message": ""},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["data_type"] == "GET_STANDINGS"

    async def test_standings_contains_expected_fields(self, client: AsyncClient, league_id: str):
        response = await client.post(
            f"/leagues/{league_id}/chat",
            json={"client_message": "what's the current leaderboard?", "last_server_message": ""},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["data_type"] == "GET_STANDINGS"
        standings = body["data"]["standings"]
        if standings:
            entry = standings[0]
            assert "rank" in entry
            assert "wins" in entry
            assert "losses" in entry


# ---------------------------------------------------------------------------
# GET_MATCH_HISTORY
# ---------------------------------------------------------------------------

@pytest.mark.usefixtures("seeded_league")
class TestGetMatchHistory:

    async def test_show_match_history(self, client: AsyncClient, league_id: str):
        response = await client.post(
            f"/leagues/{league_id}/chat",
            json={"client_message": "show me the match history", "last_server_message": ""},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["data_type"] == "GET_MATCH_HISTORY"
        assert "matches" in body["data"]
        assert isinstance(body["data"]["matches"], list)

    async def test_match_history_has_seeded_match(self, client: AsyncClient, league_id: str):
        response = await client.post(
            f"/leagues/{league_id}/chat",
            json={"client_message": "what matches have been played?", "last_server_message": ""},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["data_type"] == "GET_MATCH_HISTORY"
        matches = body["data"]["matches"]
        # Seeded: Alice/Bob vs Charlie/Diana and Alice/Bob vs Emma/John
        assert len(matches) >= 2

    async def test_match_history_entry_shape(self, client: AsyncClient, league_id: str):
        response = await client.post(
            f"/leagues/{league_id}/chat",
            json={"client_message": "show me the match history", "last_server_message": ""},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["data_type"] == "GET_MATCH_HISTORY"
        matches = body["data"]["matches"]
        if matches:
            m = matches[0]
            assert "match_id" in m
            assert "team1_player1_nickname" in m
            assert "team1_score" in m
            assert "team2_score" in m


# ---------------------------------------------------------------------------
# GET_ROSTER
# ---------------------------------------------------------------------------

@pytest.mark.usefixtures("seeded_league")
class TestGetRoster:

    async def test_show_roster(self, client: AsyncClient, league_id: str):
        response = await client.post(
            f"/leagues/{league_id}/chat",
            json={"client_message": "show me the roster", "last_server_message": ""},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["data_type"] == "GET_ROSTER"
        assert "players" in body["data"]
        assert "teams" in body["data"]

    async def test_roster_has_seeded_players(self, client: AsyncClient, league_id: str):
        response = await client.post(
            f"/leagues/{league_id}/chat",
            json={"client_message": "who's in the league?", "last_server_message": ""},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["data_type"] == "GET_ROSTER"
        players = body["data"]["players"]
        nicknames = {p["nickname"].lower() for p in players}
        # All four seeded players must appear
        assert "alice" in nicknames
        assert "bob" in nicknames
        assert "charlie" in nicknames
        assert "diana" in nicknames

    async def test_roster_has_seeded_teams(self, client: AsyncClient, league_id: str):
        response = await client.post(
            f"/leagues/{league_id}/chat",
            json={"client_message": "list all teams", "last_server_message": ""},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["data_type"] == "GET_ROSTER"
        teams = body["data"]["teams"]
        assert len(teams) >= 2


# ---------------------------------------------------------------------------
# GET_MATCH_HISTORY_BY_PLAYER
# ---------------------------------------------------------------------------

@pytest.mark.usefixtures("seeded_league")
class TestGetMatchHistoryByPlayer:

    async def test_show_player_match_history(self, client: AsyncClient, league_id: str):
        response = await client.post(
            f"/leagues/{league_id}/chat",
            json={"client_message": "show me Alice's match history", "last_server_message": ""},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["data_type"] == "GET_MATCH_HISTORY_BY_PLAYER"
        assert "matches" in body["data"]
        assert isinstance(body["data"]["matches"], list)

    async def test_player_name_extracted_correctly(self, client: AsyncClient, league_id: str):
        response = await client.post(
            f"/leagues/{league_id}/chat",
            json={"client_message": "show me Alice's match history", "last_server_message": ""},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["data_type"] == "GET_MATCH_HISTORY_BY_PLAYER"
        # player_name is echoed back in the response data
        assert body["data"]["player_name"].lower() == "alice"

    async def test_seeded_player_has_expected_matches(self, client: AsyncClient, league_id: str):
        response = await client.post(
            f"/leagues/{league_id}/chat",
            json={"client_message": "what matches has Alice played?", "last_server_message": ""},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["data_type"] == "GET_MATCH_HISTORY_BY_PLAYER"
        matches = body["data"]["matches"]
        # Alice played in both seeded matches
        assert len(matches) >= 2

    async def test_match_history_entry_shape(self, client: AsyncClient, league_id: str):
        response = await client.post(
            f"/leagues/{league_id}/chat",
            json={"client_message": "show me Bob's results", "last_server_message": ""},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["data_type"] == "GET_MATCH_HISTORY_BY_PLAYER"
        matches = body["data"]["matches"]
        if matches:
            m = matches[0]
            assert "match_id" in m
            assert "team1_player1_nickname" in m
            assert "team1_score" in m
            assert "team2_score" in m

    async def test_phrase_variant(self, client: AsyncClient, league_id: str):
        response = await client.post(
            f"/leagues/{league_id}/chat",
            json={"client_message": "what games has Charlie played?", "last_server_message": ""},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["data_type"] == "GET_MATCH_HISTORY_BY_PLAYER"
        assert body["data"]["player_name"].lower() == "charlie"
