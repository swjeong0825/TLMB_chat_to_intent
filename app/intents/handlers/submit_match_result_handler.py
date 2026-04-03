from app.api.schemas.chat_response_schema import ChatResponse
from app.application.parameter_resolution.resolved_params import ResolvedParams
from app.intents.base_intent_handler import BaseIntentHandler


class SubmitMatchResultHandler(BaseIntentHandler):
    """
    Write intent handler for SUBMIT_MATCH_RESULT.
    Assembles a prefilled payload for POST /leagues/{league_id}/matches.
    No supplementary GET calls needed — the backend auto-registers new players/teams.
    """

    def __init__(self, backend_base_url: str) -> None:
        self._backend_base_url = backend_base_url

    async def handle(self, params: ResolvedParams, host_token: str | None) -> ChatResponse:
        league_id = params.get_str("league_id")
        t1p1 = params.get_str("team1_player1_nickname")
        t1p2 = params.get_str("team1_player2_nickname")
        t2p1 = params.get_str("team2_player1_nickname")
        t2p2 = params.get_str("team2_player2_nickname")
        team1_score = params.get_str("team1_score")
        team2_score = params.get_str("team2_score")

        server_message = params.issues_summary()

        if not _is_valid_score(team1_score):
            team1_score = None
            server_message = _append_issue(
                server_message,
                "team1_score: expected a non-negative integer string — field left empty",
            )
        if not _is_valid_score(team2_score):
            team2_score = None
            server_message = _append_issue(
                server_message,
                "team2_score: expected a non-negative integer string — field left empty",
            )

        url = f"{self._backend_base_url}/leagues/{league_id}/matches"

        body = {
            "team1_nicknames": _field(
                "array[string]",
                True,
                [t1p1, t1p2] if t1p1 and t1p2 else None,
            ),
            "team2_nicknames": _field(
                "array[string]",
                True,
                [t2p1, t2p2] if t2p1 and t2p2 else None,
            ),
            "team1_score": _field("string", True, team1_score),
            "team2_score": _field("string", True, team2_score),
        }

        return ChatResponse(
            data_type="SUBMIT_MATCH_RESULT",
            data={"method": "POST", "url": url, "body": body},
            server_message=server_message,
        )


def _is_valid_score(score: str | None) -> bool:
    if not score or not score.strip():
        return False
    try:
        return int(score.strip()) >= 0
    except ValueError:
        return False


def _field(type_: str, required: bool, value: object) -> dict:
    return {"type": type_, "required": required, "value": value}


def _append_issue(existing: str, issue: str) -> str:
    return issue if not existing.strip() else f"{existing}; {issue}"
