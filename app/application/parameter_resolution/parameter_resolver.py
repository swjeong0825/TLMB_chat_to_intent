from app.application.intent_identification.intent_registry import IntentDefinition
from app.application.parameter_resolution.chat_params_extractor import ChatParamsExtractor
from app.application.parameter_resolution.chat_params_validator import ChatParamsValidator
from app.application.parameter_resolution.request_params_validator import RequestParamsValidator
from app.application.parameter_resolution.resolved_params import ResolvedParams


class ParameterResolver:
    """
    Orchestrates the three parameter sub-layers in strict sequence:
    1. RequestParamsValidator  — validates request-level params (path, header)
    2. ChatParamsExtractor     — LLM-based best-effort extraction from client_message
    3. ChatParamsValidator     — validates extracted chat-driven params

    Returns a merged ResolvedParams on success.
    Propagates ParameterResolutionException immediately on any required-param failure.
    """

    def __init__(
        self,
        request_params_validator: RequestParamsValidator,
        chat_params_extractor: ChatParamsExtractor,
        chat_params_validator: ChatParamsValidator,
    ) -> None:
        self._request_validator = request_params_validator
        self._chat_extractor = chat_params_extractor
        self._chat_validator = chat_params_validator

    async def resolve(
        self,
        intent: IntentDefinition,
        client_message: str,
        conversation_history: list[dict],
        league_id: str,
        host_token: str | None,
    ) -> ResolvedParams:
        # Sub-layer 1: request params (raises on missing required)
        params = self._request_validator.validate(intent, league_id, host_token)

        # Sub-layer 2: LLM extraction of chat-driven params (best-effort, no errors)
        extracted = await self._chat_extractor.extract(intent, client_message, conversation_history)

        # Sub-layer 3: validate extracted chat params (raises on missing required)
        self._chat_validator.validate(intent, extracted, params)

        return params
