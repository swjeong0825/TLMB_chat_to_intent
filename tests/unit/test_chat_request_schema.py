import pytest
from pydantic import ValidationError

from app.api.schemas.chat_request_schema import (
    MAX_CLIENT_MESSAGE_CHARS,
    MAX_CONVERSATION_HISTORY_TURNS,
    MAX_CONVERSATION_TURN_CONTENT_CHARS,
    ChatRequest,
    ConversationTurn,
)


def test_chat_request_within_limits_accepted():
    msg = "x" * MAX_CLIENT_MESSAGE_CHARS
    ChatRequest(client_message=msg, conversation_history=[])


def test_client_message_over_max_rejected():
    with pytest.raises(ValidationError) as exc:
        ChatRequest(
            client_message="x" * (MAX_CLIENT_MESSAGE_CHARS + 1),
            conversation_history=[],
        )
    assert "client_message" in str(exc.value).lower()


def test_conversation_turn_content_over_max_rejected():
    with pytest.raises(ValidationError) as exc:
        ConversationTurn(role="user", content="y" * (MAX_CONVERSATION_TURN_CONTENT_CHARS + 1))
    assert "content" in str(exc.value).lower()


def test_conversation_history_count_over_max_rejected():
    turns = [
        ConversationTurn(role="user" if i % 2 == 0 else "assistant", content="ok")
        for i in range(MAX_CONVERSATION_HISTORY_TURNS + 1)
    ]
    with pytest.raises(ValidationError) as exc:
        ChatRequest(client_message="hi", conversation_history=turns)
    assert "conversation_history" in str(exc.value).lower()
