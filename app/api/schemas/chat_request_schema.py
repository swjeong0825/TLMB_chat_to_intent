from typing import Literal

from pydantic import BaseModel, field_validator


class ConversationTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    client_message: str
    conversation_history: list[ConversationTurn] = []

    @field_validator("client_message", mode="before")
    @classmethod
    def coerce_none_to_empty(cls, v: object) -> str:
        return "" if v is None else str(v)
