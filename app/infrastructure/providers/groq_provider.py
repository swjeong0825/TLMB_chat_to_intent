import logging
import os

from groq import AsyncGroq

logger = logging.getLogger(__name__)


class GroqProvider:
    """
    Implements LLMProvider using the Groq API.

    Activate by setting LLM_PROVIDER=groq in .env and supplying GROQ_API_KEY.
    Uses JSON mode (response_format: json_object) to guarantee structured JSON responses.
    """

    def __init__(self) -> None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise EnvironmentError("GROQ_API_KEY is not set in the environment.")

        self._client = AsyncGroq(
            api_key=api_key,
            timeout=int(os.getenv("GROQ_TIMEOUT_SECONDS", "30")),
        )
        self._model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

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
            logger.error("Groq API call failed: %s", e)
            raise LLMCallException(f"Groq API call failed: {e}") from e


class LLMCallException(RuntimeError):
    pass
