from fastapi import APIRouter, Depends, Header

from app.api.schemas.chat_request_schema import ChatRequest
from app.api.schemas.chat_response_schema import ChatResponse
from app.application.chat_handler import ChatHandler
from app.dependencies import get_chat_handler

router = APIRouter()


@router.post("/leagues/{league_id}/chat", response_model=ChatResponse)
async def chat(
    league_id: str,
    request: ChatRequest,
    x_host_token: str | None = Header(default=None, alias="X-Host-Token"),
    chat_handler: ChatHandler = Depends(get_chat_handler),
) -> ChatResponse:
    return await chat_handler.handle(
        client_message=request.client_message,
        conversation_history=[t.model_dump() for t in request.conversation_history],
        league_id=league_id,
        host_token=x_host_token,
    )
