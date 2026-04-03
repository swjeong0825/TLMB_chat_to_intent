from pydantic import BaseModel, field_validator


class ChatRequest(BaseModel):
    client_message: str
    last_server_message: str = ""

    @field_validator("client_message", "last_server_message", mode="before")
    @classmethod
    def coerce_none_to_empty(cls, v: object) -> str:
        return "" if v is None else str(v)
