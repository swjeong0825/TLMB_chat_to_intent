from app.api.schemas.chat_response_schema import ChatResponse
from app.application.parameter_resolution.resolved_params import ResolvedParams
from app.intents.base_intent_handler import BaseIntentHandler
from app.ports.read_only_backend_gateway import ReadOnlyBackendGateway


class EditMatchScoreHandler(BaseIntentHandler):
    """
    Write intent handler for EDIT_MATCH_SCORE.

    Supplementary GET: GET /leagues/{league_id}/matches to resolve match_id from four player nicknames.
    Target: PATCH /admin/leagues/{league_id}/matches/{match_id}

    Match lookup is case-insensitive and considers both player orderings within each team pair.
    If multiple matches exist for the same player combination, uses the most recent one.
    """

    def __init__(self, gateway: ReadOnlyBackendGateway, backend_base_url: str) -> None:
        self._gateway = gateway
        self._backend_base_url = backend_base_url

    async def handle(self, params: ResolvedParams, host_token: str | None) -> ChatResponse:
        league_id = params.get_str("league_id")
        t1p1 = params.get_str("team1_player1_nickname")
        t1p2 = params.get_str("team1_player2_nickname")
        t2p1 = params.get_str("team2_player1_nickname")
        t2p2 = params.get_str("team2_player2_nickname")
        new_team1_score = params.get_str("new_team1_score")
        new_team2_score = params.get_str("new_team2_score")

        server_message = params.issues_summary()

        if not _is_valid_score(new_team1_score):
            new_team1_score = None
            server_message = _append_issue(
                server_message,
                "new_team1_score: expected a non-negative integer string — field left empty",
            )
        if not _is_valid_score(new_team2_score):
            new_team2_score = None
            server_message = _append_issue(
                server_message,
                "new_team2_score: expected a non-negative integer string — field left empty",
            )

        # Resolve match_id
        matches_response = await self._gateway.get(
            f"/leagues/{league_id}/matches", auth_token=host_token
        )
        if not matches_response.is_success:
            return ChatResponse.error(
                502,
                f"Could not fetch match history to resolve match: backend returned status "
                f"{matches_response.status_code}",
            )

        result = _resolve_match_id(matches_response.body, t1p1, t1p2, t2p1, t2p2)
        if result is None:
            return ChatResponse.error(
                502,
                f"No match found for players: {t1p1}/{t1p2} vs {t2p1}/{t2p2}",
            )

        match_id, ambiguous = result
        if ambiguous:
            server_message = _append_issue(
                server_message,
                "Multiple matches found for this player combination — using the most recent one.",
            )

        url = f"{self._backend_base_url}/admin/leagues/{league_id}/matches/{match_id}"
        body = {
            "team1_score": {"type": "string", "required": True, "value": new_team1_score},
            "team2_score": {"type": "string", "required": True, "value": new_team2_score},
        }

        return ChatResponse(
            data_type="EDIT_MATCH_SCORE",
            data={"method": "PATCH", "url": url, "body": body},
            server_message=server_message,
        )


def _resolve_match_id(
    body: dict,
    t1p1: str | None,
    t1p2: str | None,
    t2p1: str | None,
    t2p2: str | None,
) -> tuple[str, bool] | None:
    matches: list[dict] = body.get("matches", [])
    matched = [m for m in matches if _matches_four_players(m, t1p1, t1p2, t2p1, t2p2)]
    matched.sort(key=lambda m: m.get("created_at", ""), reverse=True)

    if not matched:
        return None

    return matched[0]["match_id"], len(matched) > 1


def _matches_four_players(
    match: dict,
    t1p1: str | None,
    t1p2: str | None,
    t2p1: str | None,
    t2p2: str | None,
) -> bool:
    mt1p1 = (match.get("team1_player1_nickname") or "").lower()
    mt1p2 = (match.get("team1_player2_nickname") or "").lower()
    mt2p1 = (match.get("team2_player1_nickname") or "").lower()
    mt2p2 = (match.get("team2_player2_nickname") or "").lower()

    req_team1 = {(t1p1 or "").lower(), (t1p2 or "").lower()}
    req_team2 = {(t2p1 or "").lower(), (t2p2 or "").lower()}
    match_team1 = {mt1p1, mt1p2}
    match_team2 = {mt2p1, mt2p2}

    return (req_team1 == match_team1 and req_team2 == match_team2) or (
        req_team1 == match_team2 and req_team2 == match_team1
    )


def _is_valid_score(score: str | None) -> bool:
    if not score or not score.strip():
        return False
    try:
        return int(score.strip()) >= 0
    except ValueError:
        return False


def _append_issue(existing: str, issue: str) -> str:
    return issue if not existing.strip() else f"{existing}; {issue}"
