from app.api.schemas.chat_response_schema import ChatResponse
from app.application.parameter_resolution.resolved_params import ResolvedParams
from app.intents.base_intent_handler import BaseIntentHandler
from app.ports.read_only_backend_gateway import ReadOnlyBackendGateway


class DeleteTeamHandler(BaseIntentHandler):
    """
    Write intent handler for DELETE_TEAM.

    Supplementary GET: GET /leagues/{league_id}/roster to resolve team_id from both player nicknames.
    Target: DELETE /admin/leagues/{league_id}/teams/{team_id}

    No request body — DELETE operation.
    Team lookup is case-insensitive and considers both player orderings within the team.
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
                f"Could not fetch roster to resolve team: backend returned status "
                f"{roster_response.status_code}",
            )

        team_id = _resolve_team_id(roster_response.body, player1, player2)
        if team_id is None:
            return ChatResponse.error(
                502,
                f"No team found with players '{player1}' and '{player2}' in the league roster.",
            )

        server_message = params.issues_summary()
        if not server_message.strip():
            server_message = (
                "Note: the team must have no associated match records before deletion. "
                "Delete all related matches first if needed."
            )

        url = f"{self._backend_base_url}/admin/leagues/{league_id}/teams/{team_id}"

        return ChatResponse(
            data_type="DELETE_TEAM",
            data={"method": "DELETE", "url": url, "body": {}},
            server_message=server_message,
        )


def _resolve_team_id(body: dict, player1: str | None, player2: str | None) -> str | None:
    teams: list[dict] = body.get("teams", [])
    requested = {(player1 or "").lower(), (player2 or "").lower()}

    for team in teams:
        p1 = (team.get("player1_nickname") or "").lower()
        p2 = (team.get("player2_nickname") or "").lower()
        if requested == {p1, p2}:
            return team.get("team_id")

    return None
