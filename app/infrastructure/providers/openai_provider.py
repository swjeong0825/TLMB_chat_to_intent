import logging
import os

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class OpenAIProvider:
    """
    Implements LLMProvider using the OpenAI API.

    Activate by setting LLM_PROVIDER=openai in .env and supplying OPENAI_API_KEY.
    Uses JSON mode (response_format: json_object) to guarantee structured JSON responses.
    """

    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY is not set in the environment.")

        self._client = AsyncOpenAI(
            api_key=api_key,
            timeout=int(os.getenv("OPENAI_TIMEOUT_SECONDS", "30")),
        )
        self._model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    async def complete(self, system_prompt: str, user_message: str) -> str:
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error("OpenAI API call failed: %s", e)
            raise LLMCallException(f"OpenAI API call failed: {e}") from e


class LLMCallException(RuntimeError):
    pass
