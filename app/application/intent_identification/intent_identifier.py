import json
import logging
from dataclasses import dataclass
from enum import Enum

from app.application.intent_identification.intent_registry import IntentDefinition, IntentRegistry
from app.ports.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class Confidence(str, Enum):
    HIGH = "HIGH"
    LOW = "LOW"


@dataclass
class IntentIdentificationResult:
    confidence: Confidence
    intent: IntentDefinition | None = None
    clarification_question: str = ""

    @classmethod
    def high(cls, intent: IntentDefinition) -> "IntentIdentificationResult":
        return cls(confidence=Confidence.HIGH, intent=intent)

    @classmethod
    def low(cls, question: str) -> "IntentIdentificationResult":
        return cls(confidence=Confidence.LOW, clarification_question=question)


class UnresolvableIntentException(Exception):
    pass


class IntentIdentifier:
    """
    Classifies a client_message into a registered intent using the LLM.

    Responsibilities:
    - Build the classification prompt from IntentRegistry
    - Call LLMProvider and parse the JSON response
    - Validate the returned intent name against the registry (hard gate)
    - Evaluate confidence against the per-intent threshold
    - Generate a clarification question on LOW confidence
    """

    def __init__(self, llm_provider: LLMProvider) -> None:
        self._llm = llm_provider

    async def identify(
        self, client_message: str, last_server_message: str
    ) -> IntentIdentificationResult:
        system_prompt = self._build_classification_system_prompt()
        user_message = self._build_classification_user_message(client_message, last_server_message)

        raw_response = await self._llm.complete(system_prompt, user_message)

        try:
            parsed = json.loads(raw_response)
            intent_name: str = parsed.get("intent_name", "")
            confidence: int = int(parsed.get("confidence", 0))
            clarification_question: str = parsed.get("clarification_question", "")

            # Hard gate: blank intent_name means the LLM couldn't classify → LOW confidence
            if not intent_name or not intent_name.strip():
                question = (
                    clarification_question.strip()
                    if clarification_question and clarification_question.strip()
                    else await self._generate_clarification_question(
                        client_message, last_server_message
                    )
                )
                return IntentIdentificationResult.low(question)

            # Hard gate: intent name must match a registered intent
            intent = IntentRegistry.get(intent_name)
            if intent is None:
                raise UnresolvableIntentException(
                    f"LLM returned unrecognized intent name: '{intent_name}'"
                )

            is_high = confidence >= intent.confidence_threshold
            if is_high:
                return IntentIdentificationResult.high(intent)

            question = (
                clarification_question.strip()
                if clarification_question and clarification_question.strip()
                else await self._generate_clarification_question(client_message, last_server_message)
            )
            return IntentIdentificationResult.low(question)

        except UnresolvableIntentException:
            raise
        except Exception as e:
            raise UnresolvableIntentException(
                f"Failed to parse LLM classification response: {e}"
            ) from e

    def _build_classification_system_prompt(self) -> str:
        lines = [
            "You are an intent classifier for a tennis league chatbot.",
            "Classify the user's message into exactly one of the supported intents listed below.",
            "",
            "Rules:",
            "- Respond ONLY with valid JSON matching the schema below.",
            "- If the message appears to request more than one action, assign a confidence score "
            "below the threshold and provide a clarification_question asking the user to specify "
            "which action they want to perform first.",
            "- Use the example messages as guidance but do not require exact matches.",
            "",
            'Response schema (JSON):',
            '{',
            '  "intent_name": "<one of the supported intent names>",',
            '  "confidence": <integer 0-100>,',
            '  "clarification_question": "<question to ask when confidence is low, empty string otherwise>"',
            '}',
            "",
            "Supported intents:",
        ]

        for intent in IntentRegistry.INTENTS:
            lines.append(f"\n## {intent.name} (threshold: {intent.confidence_threshold})")
            lines.append(f"Description: {intent.description}")
            lines.append("Example messages:")
            for example in intent.example_messages:
                lines.append(f"  - {example}")

        return "\n".join(lines)

    def _build_classification_user_message(
        self, client_message: str, last_server_message: str
    ) -> str:
        if last_server_message and last_server_message.strip():
            return (
                f"Previous clarification question: {last_server_message}\n"
                f"User reply: {client_message}"
            )
        return client_message

    async def _generate_clarification_question(
        self, client_message: str, last_server_message: str
    ) -> str:
        system_prompt = (
            "You are an assistant for a tennis league chatbot. The user's message was ambiguous "
            "or unclear. Generate a short, friendly clarification question to help determine "
            "what action the user wants to perform.\n\n"
            'Respond ONLY with valid JSON in this exact format: {"question": "<your question here>"}'
        )
        user_message = (
            f"Previous question: {last_server_message}\nUser message: {client_message}"
            if last_server_message and last_server_message.strip()
            else client_message
        )
        raw = await self._llm.complete(system_prompt, user_message)
        try:
            parsed = json.loads(raw)
            return parsed.get("question", raw)
        except Exception:
            return raw
