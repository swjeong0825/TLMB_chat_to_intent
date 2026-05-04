from typing import Literal

from pydantic import BaseModel, Field, field_validator

# Bounds LLM/token cost and memory vs. unusually large client payloads (SECURITY_AUDIT.md §7).
MAX_CLIENT_MESSAGE_CHARS = 8192
MAX_CONVERSATION_TURN_CONTENT_CHARS = 8192
MAX_CONVERSATION_HISTORY_TURNS = 50


class ConversationTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., max_length=MAX_CONVERSATION_TURN_CONTENT_CHARS)


class ChatRequest(BaseModel):
    client_message: str = Field(..., max_length=MAX_CLIENT_MESSAGE_CHARS)
    conversation_history: list[ConversationTurn] = Field(
        default_factory=list,
        max_length=MAX_CONVERSATION_HISTORY_TURNS,
    )

    @field_validator("client_message", mode="before")
    @classmethod
    def coerce_none_to_empty(cls, v: object) -> str:
        return "" if v is None else str(v)
