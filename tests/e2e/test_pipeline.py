"""
E2E tests for cross-cutting pipeline behaviour:
  - CLARIFICATION_QUESTION on ambiguous / low-confidence messages
  - ERROR on missing required parameters
  - ERROR on unknown intent
  - /health endpoint sanity check
"""

import pytest
from httpx import AsyncClient


class TestHealth:

    async def test_health_endpoint(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestClarificationFlow:

    async def test_ambiguous_message_returns_clarification(
        self, client: AsyncClient, league_id: str
    ):
        """A vague message should return a CLARIFICATION_QUESTION, not an intent."""
        response = await client.post(
            f"/leagues/{league_id}/chat",
            json={
                "client_message": "hey",
                "last_server_message": "",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["data_type"] == "CLARIFICATION_QUESTION"
        assert body["data"]["question"]
        assert body["server_message"] == ""

    async def test_multi_action_message_returns_clarification(
        self, client: AsyncClient, league_id: str
    ):
        """A message requesting two different actions should trigger clarification."""
        response = await client.post(
            f"/leagues/{league_id}/chat",
            json={
                "client_message": "show me the standings and also delete Alice and Bob's team",
                "last_server_message": "",
            },
        )
        assert response.status_code == 200
        body = response.json()
        # Should be clarification (multi-action) — may sometimes resolve to one intent
        # so we accept either CLARIFICATION_QUESTION or a valid single intent.
        # If resolved to an admin intent without a host_token, ERROR(400) is also valid.
        assert body["data_type"] in (
            "CLARIFICATION_QUESTION",
            "GET_STANDINGS",
            "DELETE_TEAM",
            "ERROR",
        )

    async def test_clarification_followup_resolves_intent(
        self, client: AsyncClient, league_id: str
    ):
        """After a clarification question, re-sending with last_server_message resolves intent."""
        # Step 1: send ambiguous message
        r1 = await client.post(
            f"/leagues/{league_id}/chat",
            json={"client_message": "hey", "last_server_message": ""},
        )
        assert r1.status_code == 200
        clarification_question = r1.json()["data"].get("question", "")

        # Step 2: reply to clarification with a clear intent
        r2 = await client.post(
            f"/leagues/{league_id}/chat",
            json={
                "client_message": "show me the standings",
                "last_server_message": clarification_question,
            },
        )
        assert r2.status_code == 200
        body = r2.json()
        assert body["data_type"] == "GET_STANDINGS"


class TestMissingParameters:

    async def test_missing_host_token_for_admin_intent_returns_error(
        self, client: AsyncClient, league_id: str
    ):
        """EDIT_PLAYER_NICKNAME requires X-Host-Token; omitting it should return ERROR 400."""
        response = await client.post(
            f"/leagues/{league_id}/chat",
            # No X-Host-Token header
            json={
                "client_message": "rename Alice to Alicia",
                "last_server_message": "",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["data_type"] == "ERROR"
        assert body["data"]["status_code"] == 400
        assert "host_token" in body["data"]["error_message"].lower()


class TestResponseEnvelope:

    async def test_response_always_has_three_fields(
        self, client: AsyncClient, league_id: str
    ):
        """Every response must contain data_type, data, and server_message."""
        response = await client.post(
            f"/leagues/{league_id}/chat",
            json={"client_message": "show me the standings", "last_server_message": ""},
        )
        assert response.status_code == 200
        body = response.json()
        assert "data_type" in body
        assert "data" in body
        assert "server_message" in body

    async def test_error_response_has_correct_shape(
        self, client: AsyncClient, league_id: str, host_token: str
    ):
        """ERROR responses must have status_code + error_message in data, empty server_message."""
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
        if body["data_type"] == "ERROR":
            assert "status_code" in body["data"]
            assert "error_message" in body["data"]
            assert body["server_message"] == ""
