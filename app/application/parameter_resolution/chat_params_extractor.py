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
        self,
        intent: IntentDefinition,
        client_message: str,
        conversation_history: list[dict] | None = None,
    ) -> dict[str, object]:
        all_chat_params: list[ParamDef] = (
            intent.required_chat_params + intent.optional_chat_params
        )

        if not all_chat_params:
            return {}

        system_prompt = self._build_extraction_system_prompt(intent, all_chat_params)
        context_message = self._build_context_message(client_message, conversation_history or [])
        raw_response = await self._llm.complete(system_prompt, context_message)

        try:
            extracted = json.loads(raw_response)
            return {
                param.name: extracted.get(param.name)
                for param in all_chat_params
            }
        except Exception as e:
            logger.warning("Failed to parse LLM extraction response: %s", e)
            return {param.name: None for param in all_chat_params}

    def _build_context_message(
        self, client_message: str, conversation_history: list[dict]
    ) -> str:
        if not conversation_history:
            return client_message
        lines = ["Conversation history:"]
        for turn in conversation_history:
            role = turn.get("role", "user")
            content = turn.get("content", "")
            lines.append(f"[{role}]: {content}")
        lines.append(f"\nCurrent message: {client_message}")
        return "\n".join(lines)

    def _build_extraction_system_prompt(
        self, intent: IntentDefinition, params: list[ParamDef]
    ) -> str:
        """
        Build the extractor system prompt.

        The rules below were tightened after observing small models
        (notably llama-3.1-8b-instant) fabricating placeholder nicknames
        such as "john_doe", "alice_smith", or common training-data first
        names like "John"/"Michael"/"Emma"/"Oliver" when the user message
        carried no real parameter values (e.g. a bare "record a match").
        JSON mode forces a value for every key, so we have to give the
        model an explicit, repeated instruction that `null` is the
        correct answer for fields that are not literally present in the
        user's message. The one-shot examples reinforce that.
        """
        lines = [
            "You are a parameter extractor for a tennis league chatbot.",
            f"The user's message has been identified as intent: {intent.name}.",
            "",
            "Your only job is to extract parameter values that appear in the "
            "user's CURRENT message (the last message after 'Current message:' "
            "when conversation history is provided). Return ONLY valid JSON "
            "with the parameter names as keys.",
            "",
            "CRITICAL RULES (you MUST follow all of these):",
            "1. A parameter value MUST be literally present in the user's "
            "current message. If it is not, set its value to null.",
            "2. NEVER invent, guess, or substitute placeholder values. Do NOT "
            "fall back to example/training-data names such as 'john_doe', "
            "'alice_smith', 'jane_doe', 'John Doe', 'player1', 'user1', "
            "'foo', 'bar', or any name that is not literally in the user's "
            "message.",
            "3. Returning null is ALWAYS preferred over guessing. Downstream "
            "code handles missing fields gracefully (it renders an empty form "
            "the user can fill in); fabricated fields are bugs.",
            "4. Numeric/score fields: if the user did not state a specific "
            "number, return null — not 0, not 1, not any default.",
            "5. Bare/info-less requests like 'record a match', 'submit a "
            "match', 'log a result', 'enter a match', 'show standings', or "
            "'help' carry NO parameter values. For such messages every "
            "parameter MUST be null.",
            "6. Use conversation history only to disambiguate a value that "
            "the user is clearly carrying over (e.g. they previously said "
            "'Alice' and now say 'her score was 6'). Never copy values from "
            "history that the user has not referenced in the current message.",
            "",
            "Parameters to extract:",
        ]

        for param in params:
            desc = f": {param.description}" if param.description else ""
            type_hint = "JSON array of strings" if param.type is list else param.type.__name__
            lines.append(f"- {param.name} ({type_hint}){desc}")

        lines.append("")
        lines.append("Examples (do NOT echo the example values; follow the same pattern):")
        lines.append(
            '- User says "record a match" (no other detail) → every parameter '
            "is null."
        )
        lines.append(
            '- User says "submit a match result" (no other detail) → every '
            "parameter is null."
        )
        lines.append(
            '- User says "Alice and Bob beat Charlie and Diana 6 to 3" → '
            "extract the four nicknames and the two scores from the literal "
            "words; do NOT add or invent extra names."
        )

        lines.append("\nResponse schema (JSON):")
        fields = ",\n".join(
            f'  "{p.name}": <JSON array of strings or null>' if p.type is list
            else f'  "{p.name}": <value or null>'
            for p in params
        )
        lines.append("{")
        lines.append(fields)
        lines.append("}")

        return "\n".join(lines)
