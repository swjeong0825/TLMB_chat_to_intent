"""
Shared fixtures for E2E tests.

Loads .env so all API keys and TEST_LEAGUE_ID / TEST_HOST_TOKEN are available.
Provides an httpx.AsyncClient wired to the real FastAPI app (ASGI transport —
no actual server process needed, but the real Groq API and real backend are called).

Only two env vars are required to run the full suite:
  TEST_LEAGUE_ID  — uuid of a freshly created league
  TEST_HOST_TOKEN — host token returned when the league was created

The `seeded_league` fixture handles all data setup automatically.
"""

import os

import pytest
import pytest_asyncio
from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient

# Load .env before importing the app (providers read env vars at import time)
load_dotenv()

# Tests hit the app in a tight loop; disable throttling so the suite stays deterministic.
os.environ["RATELIMIT_ENABLED"] = "false"

# Clear the lru_cache so each test session builds a fresh handler
from app import dependencies
dependencies._build_chat_handler.cache_clear()

from app.main import app
from app.infrastructure.config.settings import get_settings


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        pytest.skip(f"Required env var '{name}' is not set — skipping E2E test.")
    return value


@pytest.fixture(scope="session")
def league_id() -> str:
    return _require_env("TEST_LEAGUE_ID")


@pytest.fixture(scope="session")
def host_token() -> str:
    return _require_env("TEST_HOST_TOKEN")


@pytest_asyncio.fixture(scope="session")
async def client() -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


@pytest_asyncio.fixture(scope="session")
async def seeded_league(league_id: str) -> None:
    """
    Seeds the test league with two matches via the backend API.

    Submitting matches auto-creates all players and teams, so this produces:
      Players : Alice, Bob, Charlie, Diana, Emma, John
      Teams   : Alice/Bob, Charlie/Diana, Emma/John
      Matches : Alice/Bob vs Charlie/Diana (6-3), Alice/Bob vs Emma/John (6-4)

    Tests that assert specific players, teams, or matches exist should declare
    this fixture as a dependency. It runs once per session.
    """
    backend_url = get_settings().backend_base_url
    async with AsyncClient(base_url=backend_url) as backend:
        await backend.post(
            f"/leagues/{league_id}/matches",
            json={
                "team1_nicknames": ["Alice", "Bob"],
                "team2_nicknames": ["Charlie", "Diana"],
                "team1_score": "6",
                "team2_score": "3",
            },
        )
        await backend.post(
            f"/leagues/{league_id}/matches",
            json={
                "team1_nicknames": ["Alice", "Bob"],
                "team2_nicknames": ["Emma", "John"],
                "team1_score": "6",
                "team2_score": "4",
            },
        )
