from app.api.schemas.chat_response_schema import ChatResponse
from app.application.parameter_resolution.resolved_params import ResolvedParams
from app.intents.base_intent_handler import BaseIntentHandler
from app.ports.read_only_backend_gateway import ReadOnlyBackendGateway


class EditMatchScoreHandler(BaseIntentHandler):
    """
    Write intent handler for EDIT_MATCH_SCORE.

    Picker flow:
      - The admin mentions 1-4 player nicknames in chat.
      - Supplementary GET: GET /leagues/{league_id}/matches.
      - The handler filters to matches whose four-nickname set contains ALL
        of the mentioned nicknames (case-insensitive).
      - Returns the candidate list to the frontend as the picker payload;
        the frontend renders an inline form per row prefilled with the
        match's current scores. The admin edits the form and PATCHes the
        backend directly via /admin/leagues/{league_id}/matches/{match_id}.

    No matches found is NOT an error — we return an empty list with a
    server_message that explains the ALL semantics so the user understands
    the result.
    """

    _MAX_NICKNAMES = 4

    def __init__(self, gateway: ReadOnlyBackendGateway, backend_base_url: str) -> None:
        self._gateway = gateway
        self._backend_base_url = backend_base_url

    async def handle(self, params: ResolvedParams, host_token: str | None) -> ChatResponse:
        league_id = params.get_str("league_id")

        nicknames = _collect_nicknames(params, self._MAX_NICKNAMES)
        if not nicknames:
            return ChatResponse.error(
                400,
                "Please mention at least one player nickname so I can find the "
                "match to edit. You can mention up to four players to narrow it down.",
            )

        matches_response = await self._gateway.get(
            f"/leagues/{league_id}/matches", auth_token=host_token
        )
        if not matches_response.is_success:
            return ChatResponse.error(
                502,
                f"Could not fetch match history to look up matches: backend returned "
                f"status {matches_response.status_code}",
            )

        all_matches: list[dict] = matches_response.body.get("matches", [])
        filtered = [m for m in all_matches if _match_contains_all(m, nicknames)]
        filtered.sort(key=lambda m: m.get("created_at", ""), reverse=True)

        url_template = (
            f"{self._backend_base_url}/admin/leagues/{league_id}/matches/{{match_id}}"
        )

        joined = ", ".join(nicknames)
        if filtered:
            server_message = (
                f"Showing matches that contain ALL of: {joined}. "
                "Pick one to edit its score."
            )
        else:
            server_message = (
                f"No recorded match contains ALL of: {joined}. "
                "Try mentioning fewer or different player nicknames."
            )

        return ChatResponse(
            data_type="EDIT_MATCH_SCORE",
            data={
                "league_id": league_id,
                "method": "PATCH",
                "url_template": url_template,
                "player_filters": nicknames,
                "matches": filtered,
                "body_schema": {
                    "team1_score": {"type": "string", "required": True},
                    "team2_score": {"type": "string", "required": True},
                },
            },
            server_message=server_message,
        )


def _collect_nicknames(params: ResolvedParams, max_count: int) -> list[str]:
    """Read player1..playerN_nickname, drop blanks/dupes (case-insensitive), preserve order."""
    seen: set[str] = set()
    out: list[str] = []
    for i in range(1, max_count + 1):
        raw = params.get_str(f"player{i}_nickname")
        if raw is None:
            continue
        cleaned = raw.strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(cleaned)
    return out


def _match_contains_all(match: dict, nicknames: list[str]) -> bool:
    in_match = {
        (match.get("team1_player1_nickname") or "").lower(),
        (match.get("team1_player2_nickname") or "").lower(),
        (match.get("team2_player1_nickname") or "").lower(),
        (match.get("team2_player2_nickname") or "").lower(),
    }
    in_match.discard("")
    requested = {n.lower() for n in nicknames}
    return requested.issubset(in_match)
