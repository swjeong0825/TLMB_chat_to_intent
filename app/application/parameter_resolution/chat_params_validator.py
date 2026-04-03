from app.application.intent_identification.intent_registry import IntentDefinition
from app.application.parameter_resolution.parameter_resolution_exception import ParameterResolutionException
from app.application.parameter_resolution.resolved_params import ResolvedParams


class ChatParamsValidator:
    """
    Sub-layer 3: validates the chat-driven parameters extracted by the previous sub-layer.
    Mirrors RequestParamsValidator but operates on chat-driven parameters only.
    Raises ParameterResolutionException(400) if any required chat param is missing.
    """

    def validate(
        self,
        intent: IntentDefinition,
        extracted: dict[str, object],
        params: ResolvedParams,
    ) -> None:
        missing_required: list[str] = []

        for param in intent.required_chat_params:
            value = extracted.get(param.name)
            if value is None or str(value).strip() == "":
                missing_required.append(param.name)
                params.record_issue(
                    f"{param.name}: required chat parameter not found in message"
                )
            else:
                params.put(param.name, value)

        for param in intent.optional_chat_params:
            value = extracted.get(param.name)
            if value is not None and str(value).strip() != "":
                params.put(param.name, value)

        if missing_required:
            raise ParameterResolutionException(
                400,
                f"Could not extract required chat parameter(s): {', '.join(missing_required)}. "
                "Please include the missing information in your message.",
            )
