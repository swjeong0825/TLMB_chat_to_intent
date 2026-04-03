from abc import ABC, abstractmethod

from app.api.schemas.chat_response_schema import ChatResponse
from app.application.parameter_resolution.resolved_params import ResolvedParams


class BaseIntentHandler(ABC):
    @abstractmethod
    async def handle(self, params: ResolvedParams, host_token: str | None) -> ChatResponse: ...
