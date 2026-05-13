from app.api.schemas.chat_response_schema import ChatResponse
from app.application.parameter_resolution.resolved_params import ResolvedParams
from app.intents.base_intent_handler import BaseIntentHandler
from app.ports.read_only_backend_gateway import ReadOnlyBackendGateway


class RemoveAllowlistEntryHandler(BaseIntentHandler):
    """
    Write intent handler for REMOVE_ALLOWLIST_ENTRY.

    Supplementary GET: GET /leagues/{league_id}/allowlist to resolve
    allowlist_entry_id from the spoken nickname.
    Target: DELETE /admin/leagues/{league_id}/allowlist/{allowlist_entry_id}

    If the nickname is not found in the allowlist, returns a CLARIFICATION_QUESTION
    listing the actual allowlist nicknames so the host can pick the correct one.
    """

    def __init__(self, gateway: ReadOnlyBackendGateway, backend_base_url: str) -> None:
        self._gateway = gateway
        self._backend_base_url = backend_base_url

    async def handle(self, params: ResolvedParams, host_token: str | None) -> ChatResponse:
        league_id = params.get_str("league_id")
        nickname = params.get_str("nickname")

        allowlist_response = await self._gateway.get(
            f"/leagues/{league_id}/allowlist", auth_token=host_token
        )
        if not allowlist_response.is_success:
            return ChatResponse.error(
                502,
                f"Could not fetch allowlist to resolve nickname: backend returned status "
                f"{allowlist_response.status_code}",
            )

        allowlist: list[dict] = allowlist_response.body.get("allowlist", [])
        allowlist_entry_id = _resolve_allowlist_entry_id(allowlist, nickname)

        if allowlist_entry_id is None:
            actual_nicknames = [
                entry.get("nickname", "") for entry in allowlist if entry.get("nickname")
            ]
            if actual_nicknames:
                names_list = ", ".join(actual_nicknames)
                question = (
                    f"'{nickname}' was not found in the allowlist. "
                    f"Current allowlist entries are: {names_list}. "
                    f"Which one did you want to remove?"
                )
            else:
                question = (
                    f"'{nickname}' was not found in the allowlist, "
                    f"and the allowlist is currently empty."
                )
            return ChatResponse.clarification_question(question)

        url = (
            f"{self._backend_base_url}/admin/leagues/{league_id}"
            f"/allowlist/{allowlist_entry_id}"
        )
        return ChatResponse(
            data_type="REMOVE_ALLOWLIST_ENTRY",
            data={"method": "DELETE", "url": url, "body": {}},
            server_message=params.issues_summary(),
        )


def _resolve_allowlist_entry_id(
    allowlist: list[dict], nickname: str | None
) -> str | None:
    if not nickname:
        return None
    target = (nickname or "").strip().lower()
    for entry in allowlist:
        if (entry.get("nickname") or "").lower() == target:
            return entry.get("allowlist_entry_id")
    return None
