from pydantic import BaseModel


class ChatResponse(BaseModel):
    data_type: str
    data: dict
    server_message: str

    @classmethod
    def clarification_question(cls, question: str) -> "ChatResponse":
        return cls(
            data_type="CLARIFICATION_QUESTION",
            data={"question": question},
            server_message="",
        )

    @classmethod
    def error(cls, status_code: int, error_message: str) -> "ChatResponse":
        return cls(
            data_type="ERROR",
            data={"status_code": status_code, "error_message": error_message},
            server_message="",
        )
