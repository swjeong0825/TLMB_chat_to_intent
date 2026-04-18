from fastapi import APIRouter, Depends, Header
from starlette.requests import Request

from app.api.schemas.chat_request_schema import ChatRequest
from app.api.schemas.chat_response_schema import ChatResponse
from app.application.chat_handler import ChatHandler
from app.dependencies import get_chat_handler
from app.rate_limit import CHAT_ROUTE_LIMIT, limiter

router = APIRouter()


@router.post("/leagues/{league_id}/chat", response_model=ChatResponse)
@limiter.limit(CHAT_ROUTE_LIMIT)
async def chat(
    request: Request,
    league_id: str,
    body: ChatRequest,
    x_host_token: str | None = Header(default=None, alias="X-Host-Token"),
    chat_handler: ChatHandler = Depends(get_chat_handler),
) -> ChatResponse:
    return await chat_handler.handle(
        client_message=body.client_message,
        conversation_history=[t.model_dump() for t in body.conversation_history],
        league_id=league_id,
        host_token=x_host_token,
    )
