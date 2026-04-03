import json
import logging

from app.application.intent_identification.intent_registry import IntentDefinition, ParamDef
from app.ports.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class ChatParamsExtractor:
    """
    Sub-layer 2: uses the LLM to best-effort extract all chat-driven parameters
    from the client_message. Returns raw extracted values — does NOT validate
    presence or raise errors for missing parameters.
    """

    def __init__(self, llm_provider: LLMProvider) -> None:
        self._llm = llm_provider

    async def extract(
        self, intent: IntentDefinition, client_message: str
    ) -> dict[str, object]:
        all_chat_params: list[ParamDef] = (
            intent.required_chat_params + intent.optional_chat_params
        )

        if not all_chat_params:
            return {}

        system_prompt = self._build_extraction_system_prompt(intent, all_chat_params)
        raw_response = await self._llm.complete(system_prompt, client_message)

        try:
            extracted = json.loads(raw_response)
            return {
                param.name: extracted.get(param.name)
                for param in all_chat_params
            }
        except Exception as e:
            logger.warning("Failed to parse LLM extraction response: %s", e)
            return {param.name: None for param in all_chat_params}

    def _build_extraction_system_prompt(
        self, intent: IntentDefinition, params: list[ParamDef]
    ) -> str:
        lines = [
            "You are a parameter extractor for a tennis league chatbot.",
            f"The user's message has been identified as intent: {intent.name}.",
            "",
            "Extract the following parameters from the user's message.",
            "Return ONLY valid JSON with the parameter names as keys.",
            "If a parameter cannot be found in the message, set its value to null.",
            "",
            "Parameters to extract:",
        ]

        for param in params:
            desc = f": {param.description}" if param.description else ""
            lines.append(f"- {param.name} ({param.type.__name__}){desc}")

        lines.append("\nResponse schema (JSON):")
        fields = ",\n".join(
            f'  "{p.name}": <value or null>' for p in params
        )
        lines.append("{")
        lines.append(fields)
        lines.append("}")

        return "\n".join(lines)
