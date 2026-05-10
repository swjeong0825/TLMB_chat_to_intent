from app.api.schemas.chat_response_schema import ChatResponse
from app.application.intent_identification.intent_registry import (
    IntentDefinition,
    IntentRegistry,
)
from app.application.parameter_resolution.resolved_params import ResolvedParams
from app.intents.base_intent_handler import BaseIntentHandler


class HelpHandler(BaseIntentHandler):
    """
    Pure in-process handler for the HELP intent.

    Builds the help payload directly from IntentRegistry, so the list of
    supported commands shown to the user automatically stays in sync with the
    registry — adding or editing an IntentDefinition immediately changes what
    HELP returns; no separate copy of the intent catalogue is maintained.

    Response shape:
        {
            "data_type": "HELP",
            "data": {
                "intents": [
                    {
                        "name": "GET_STANDINGS",
                        "intent_type": "READ",
                        "requires_admin": false,
                        "description": "short UI line (see intent.summary)",
                        "example_messages": ["...", "..."]
                    },
                    ...
                ]
            }
        }
    """

    async def handle(self, params: ResolvedParams, host_token: str | None) -> ChatResponse:
        intents_payload: list[dict] = []
        for intent in IntentRegistry.INTENTS:
            # Don't list HELP itself in its own output — it's noise.
            if intent.name == "HELP":
                continue
            intents_payload.append(
                {
                    "name": intent.name,
                    "intent_type": intent.intent_type.value,
                    "requires_admin": _requires_admin(intent),
                    "description": intent.summary or intent.description,
                    "example_messages": list(intent.example_messages),
                }
            )

        return ChatResponse(
            data_type="HELP",
            data={"intents": intents_payload},
            server_message="",
        )


def _requires_admin(intent: IntentDefinition) -> bool:
    """
    An intent is admin-only when it requires the host token at the request layer
    (i.e. its required_request_params include the `host_token` ParamDef).
    """
    return any(p.name == "host_token" for p in intent.required_request_params)
