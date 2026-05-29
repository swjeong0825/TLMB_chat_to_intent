from app.api.schemas.chat_response_schema import ChatResponse
from app.application.parameter_resolution.resolved_params import ResolvedParams
from app.intents.base_intent_handler import BaseIntentHandler
from app.ports.read_only_backend_gateway import ReadOnlyBackendGateway


class DeletePairHandler(BaseIntentHandler):
    """
    Write intent handler for DELETE_PAIR.

    Supplementary GET: GET /leagues/{league_id}/roster to resolve pair_id from both player nicknames.
    Target: DELETE /admin/leagues/{league_id}/pairs/{pair_id}

    No request body — DELETE operation.
    Pair lookup is case-insensitive and considers both player orderings within the pair.
    """

    def __init__(self, gateway: ReadOnlyBackendGateway, backend_base_url: str) -> None:
        self._gateway = gateway
        self._backend_base_url = backend_base_url

    async def handle(self, params: ResolvedParams, host_token: str | None) -> ChatResponse:
        league_id = params.get_str("league_id")
        player1 = params.get_str("player1_nickname")
        player2 = params.get_str("player2_nickname")

        roster_response = await self._gateway.get(
            f"/leagues/{league_id}/roster", auth_token=host_token
        )
        if not roster_response.is_success:
            return ChatResponse.error(
                502,
                f"Could not fetch roster to resolve pair: backend returned status "
                f"{roster_response.status_code}",
            )

        pair_id = _resolve_pair_id(roster_response.body, player1, player2)
        if pair_id is None:
            return ChatResponse.error(
                502,
                f"No pair found with players '{player1}' and '{player2}' in the league roster.",
            )

        server_message = params.issues_summary()
        if not server_message.strip():
            server_message = (
                "Note: the pair must have no associated match records before deletion. "
                "Delete all related matches first if needed."
            )

        url = f"{self._backend_base_url}/admin/leagues/{league_id}/pairs/{pair_id}"

        return ChatResponse(
            data_type="DELETE_PAIR",
            data={"method": "DELETE", "url": url, "body": {}},
            server_message=server_message,
        )


def _resolve_pair_id(body: dict, player1: str | None, player2: str | None) -> str | None:
    pairs: list[dict] = body.get("pairs", [])
    requested = {(player1 or "").lower(), (player2 or "").lower()}

    for pair in pairs:
        p1 = (pair.get("player1_nickname") or "").lower()
        p2 = (pair.get("player2_nickname") or "").lower()
        if requested == {p1, p2}:
            return pair.get("pair_id")

    return None
