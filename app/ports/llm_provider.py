from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    async def complete(self, system_prompt: str, user_message: str) -> str: ...
