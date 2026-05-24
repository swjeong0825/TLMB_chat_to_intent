from app.api.schemas.chat_response_schema import ChatResponse
from app.application.parameter_resolution.resolved_params import ResolvedParams
from app.intents.base_intent_handler import BaseIntentHandler


class AddPlayersToRosterHandler(BaseIntentHandler):
    """
    Write intent handler for ADD_PLAYERS_TO_ROSTER.
    Assembles a prefilled payload for POST /admin/leagues/{league_id}/players.
    No supplementary GET needed — the payload is submitted directly by the frontend.

    This is the v6 replacement for ADD_ALLOWLIST_ENTRIES: pre-registration now
    writes `Player` rows directly (the `allowlist_entries` side table was
    retired in alembic 007). The shape of the prefilled form mirrors the
    backend's `POST /admin/leagues/{league_id}/players` body.
    """

    def __init__(self, backend_base_url: str) -> None:
        self._backend_base_url = backend_base_url

    async def handle(self, params: ResolvedParams, host_token: str | None) -> ChatResponse:
        league_id = params.get_str("league_id")
        raw_nicknames = params.get("nicknames")

        if isinstance(raw_nicknames, str):
            nicknames: list[str] = [raw_nicknames]
        elif isinstance(raw_nicknames, list):
            nicknames = [str(n) for n in raw_nicknames if n is not None and str(n).strip()]
        else:
            nicknames = []

        url = f"{self._backend_base_url}/admin/leagues/{league_id}/players"
        body = {
            "nicknames": {
                "type": "array[string]",
                "required": True,
                "value": nicknames if nicknames else None,
            }
        }

        return ChatResponse(
            data_type="ADD_PLAYERS_TO_ROSTER",
            data={"method": "POST", "url": url, "body": body},
            server_message=params.issues_summary(),
        )
