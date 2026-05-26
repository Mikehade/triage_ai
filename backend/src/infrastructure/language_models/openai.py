import json

from openai import AsyncOpenAI, APIError

from src.infrastructure.language_models.base import (
    ILLMClient,
    LLMConfig,
    LLMResponse,
    Message,
    MessageRole,
)
from utils.logger import get_logger

logger = get_logger()

_ROLE_MAP = {
    MessageRole.SYSTEM: "system",
    MessageRole.USER: "user",
    MessageRole.ASSISTANT: "assistant",
}


class OpenAIClient(ILLMClient):
    """
    OpenAI implementation of ILLMClient.
    Drop-in replacement for GeminiClient — swap in container.py only.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        default_config: LLMConfig | None = None,
    ):
        self._model = model
        self._default_config = default_config or LLMConfig()
        self._client = AsyncOpenAI(api_key=api_key)

    def _to_openai_messages(self, messages: list[Message]) -> list[dict]:
        return [
            {"role": _ROLE_MAP[m.role], "content": m.content}
            for m in messages
        ]

    async def complete(
        self,
        messages: list[Message],
        config: LLMConfig | None = None,
    ) -> LLMResponse:
        cfg = config or self._default_config
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=self._to_openai_messages(messages),
                temperature=cfg.temperature,
                max_tokens=cfg.max_output_tokens,
                top_p=cfg.top_p,
                n=cfg.candidate_count,
            )
            choice = response.choices[0]
            return LLMResponse(
                content=choice.message.content,
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                model=self._model,
                raw=response,
            )
        except APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    async def complete_json(
        self,
        messages: list[Message],
        config: LLMConfig | None = None,
    ) -> dict:
        cfg = config or self._default_config
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=self._to_openai_messages(messages),
                temperature=cfg.temperature,
                max_tokens=cfg.max_output_tokens,
                top_p=cfg.top_p,
                response_format={"type": "json_object"},
            )
            return json.loads(response.choices[0].message.content)
        except json.JSONDecodeError as e:
            logger.error(f"OpenAI JSON parse error: {e}")
            raise
        except APIError as e:
            logger.error(f"OpenAI API error in complete_json: {e}")
            raise

    async def health_check(self) -> bool:
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            return bool(response.choices[0].message.content)
        except Exception as e:
            logger.warning(f"OpenAI health check failed: {e}")
            return False