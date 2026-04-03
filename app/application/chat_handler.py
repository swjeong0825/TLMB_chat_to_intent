import logging

from app.api.schemas.chat_response_schema import ChatResponse
from app.application.intent_identification.intent_identifier import (
    Confidence,
    IntentIdentifier,
    UnresolvableIntentException,
)
from app.application.parameter_resolution.parameter_resolution_exception import ParameterResolutionException
from app.application.parameter_resolution.parameter_resolver import ParameterResolver
from app.intents.base_intent_handler import BaseIntentHandler

logger = logging.getLogger(__name__)


class ChatHandler:
    """
    Main orchestrator for the full intent pipeline.

    Flow:
      1. IntentIdentifier classifies client_message → intent + confidence
      2. LOW confidence → return CLARIFICATION_QUESTION immediately
      3. HIGH confidence → ParameterResolver validates and extracts all params
      4. Dispatches to the correct intent handler
      5. Returns the handler's ChatResponse

    All errors are caught here and converted to structured ChatResponse objects —
    no exceptions bubble to the router.
    """

    def __init__(
        self,
        intent_identifier: IntentIdentifier,
        parameter_resolver: ParameterResolver,
        handler_registry: dict[str, BaseIntentHandler],
    ) -> None:
        self._intent_identifier = intent_identifier
        self._parameter_resolver = parameter_resolver
        self._handler_registry = handler_registry

    async def handle(
        self,
        client_message: str,
        last_server_message: str,
        league_id: str,
        host_token: str | None,
    ) -> ChatResponse:
        try:
            # Step 1: classify intent
            identification = await self._intent_identifier.identify(
                client_message, last_server_message
            )

            # Step 2: short-circuit on LOW confidence
            if identification.confidence == Confidence.LOW:
                return ChatResponse.clarification_question(identification.clarification_question)

            # Step 3: resolve parameters
            params = await self._parameter_resolver.resolve(
                intent=identification.intent,
                client_message=client_message,
                league_id=league_id,
                host_token=host_token,
            )

            # Step 4: dispatch to intent handler
            intent_name = identification.intent.name
            handler = self._handler_registry.get(intent_name)
            if handler is None:
                logger.error("No handler registered for intent: %s", intent_name)
                return ChatResponse.error(422, f"No handler available for intent: {intent_name}")

            return await handler.handle(params=params, host_token=host_token)

        except UnresolvableIntentException as e:
            logger.warning("Unresolvable intent: %s", e)
            return ChatResponse.error(422, str(e))

        except ParameterResolutionException as e:
            logger.warning("Parameter resolution failed: %s", e)
            return ChatResponse.error(e.status_code, e.message)

        except Exception as e:
            logger.error("Unexpected error in chat handler", exc_info=True)
            return ChatResponse.error(502, "An unexpected error occurred. Please try again.")
