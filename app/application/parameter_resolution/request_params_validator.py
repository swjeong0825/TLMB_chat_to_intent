from app.application.intent_identification.intent_registry import IntentDefinition, ParamDef
from app.application.parameter_resolution.parameter_resolution_exception import ParameterResolutionException
from app.application.parameter_resolution.resolved_params import ResolvedParams


class RequestParamsValidator:
    """
    Sub-layer 1: validates Required and Optional Request Parameters from the HTTP request.
    Request parameters are sourced from path params and headers — not from the LLM.

    For this domain all intents share the same request params:
    - league_id (path) — required for all intents
    - host_token (header X-Host-Token) — required for admin write intents
    """

    def validate(
        self,
        intent: IntentDefinition,
        league_id: str,
        host_token: str | None,
    ) -> ResolvedParams:
        params = ResolvedParams()
        missing_required: list[str] = []

        for param in intent.required_request_params:
            value = self._extract(param, league_id, host_token)
            if not value or not str(value).strip():
                missing_required.append(param.name)
            else:
                params.put(param.name, value)

        for param in intent.optional_request_params:
            value = self._extract(param, league_id, host_token)
            if value and str(value).strip():
                params.put(param.name, value)

        if missing_required:
            raise ParameterResolutionException(
                400,
                f"Missing required request parameter(s): {', '.join(missing_required)}",
            )

        return params

    def _extract(
        self,
        param: ParamDef,
        league_id: str,
        host_token: str | None,
    ) -> str | None:
        match param.name:
            case "league_id":
                return league_id
            case "host_token":
                return host_token
            case _:
                return None
