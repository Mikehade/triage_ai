from __future__ import annotations
import json
import logging

# import google.generativeai as genai
# from google.generativeai.types import GenerationConfig
from google import genai
from google.genai import types
from google.api_core.exceptions import GoogleAPIError

from src.infrastructure.language_models.base import (
    ILLMClient,
    LLMConfig,
    LLMResponse,
    Message,
    MessageRole,
)
from utils.logger import get_logger

logger = get_logger()

# Maps our role enum to Gemini's expected role strings
_ROLE_MAP = {
    MessageRole.USER: "user",
    MessageRole.ASSISTANT: "model",
    # System messages are handled separately in Gemini
}

class GeminiClient(ILLMClient):
    """
    Google Gemini implementation of ILLMClient.
    Uses the google-genai SDK (v1+).

    System messages are extracted from the message list and passed
    as system_instruction — Gemini's native system prompt mechanism.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-3.5-flash",
        default_config: LLMConfig | None = None,
    ):
        self._model_name = model
        self._default_config = default_config or LLMConfig()
        self._client = genai.Client(api_key=api_key)

    def _extract_system(
        self,
        messages: list[Message],
    ) -> tuple[str | None, list[Message]]:
        """
        Separate system messages from the conversation.
        Gemini takes system instructions separately from the chat history.
        """
        system_parts = [m.content for m in messages if m.role == MessageRole.SYSTEM]
        conversation = [m for m in messages if m.role != MessageRole.SYSTEM]
        system = "\n\n".join(system_parts) if system_parts else None
        return system, conversation

    def _build_generation_config(
        self,
        config: LLMConfig,
        system_instruction: str | None = None,
        json_mode: bool = False,
    ) -> types.GenerateContentConfig:
        return types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=config.temperature,
            max_output_tokens=config.max_output_tokens,
            top_p=config.top_p,
            top_k=config.top_k,
            candidate_count=config.candidate_count,
            response_mime_type="application/json" if json_mode else None,
        )

    def _to_gemini_history(
        self,
        messages: list[Message],
    ) -> list[dict]:
        """Convert our Message list to Gemini's content format."""
        return [
            {
                "role": _ROLE_MAP.get(m.role, "user"),
                "parts": [{"text": m.content}],
            }
            for m in messages
        ]

    async def complete(
        self,
        messages: list[Message],
        config: LLMConfig | None = None,
    ) -> LLMResponse:
        cfg = config or self._default_config
        system, conversation = self._extract_system(messages)

        try:
            generation_config = self._build_generation_config(cfg, system_instruction=system)

            # Split into history and final user turn
            history = self._to_gemini_history(conversation[:-1])
            last_message = conversation[-1].content

            chat = self._client.aio.chats.create(
                model=self._model_name,
                history=history,
                config=generation_config,
            )
            response = await chat.send_message(last_message)

            return LLMResponse(
                content=response.text,
                input_tokens=response.usage_metadata.prompt_token_count,
                output_tokens=response.usage_metadata.candidates_token_count,
                model=self._model_name,
                raw=response,
            )
        except genai.errors.APIError as e:
            logger.error(f"Gemini API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in GeminiClient.complete: {e}")
            raise

    # async def complete_json(
    #     self,
    #     messages: list[Message],
    #     config: LLMConfig | None = None,
    # ) -> dict:
    #     cfg = config or self._default_config
    #     system, conversation = self._extract_system(messages)

    #     try:
    #         generation_config = self._build_generation_config(
    #             cfg, system_instruction=system, json_mode=True
    #         )

    #         history = self._to_gemini_history(conversation[:-1])
    #         last_message = conversation[-1].content

    #         chat = self._client.aio.chats.create(
    #             model=self._model_name,
    #             history=history,
    #             config=generation_config,
    #         )
    #         response = await chat.send_message(last_message)

    #         return json.loads(response.text)
    #     except json.JSONDecodeError as e:
    #         logger.error(f"Gemini JSON parse error: {e}. Raw: {response.text}")
    #         raise
    #     except genai.errors.APIError as e:
    #         logger.error(f"Gemini API error in complete_json: {e}")
    #         raise
    #     except Exception as e:
    #         logger.error(f"Unexpected error in GeminiClient.complete_json: {e}")
    #         raise
    async def complete_json(
        self,
        messages: list[Message],
        config: LLMConfig | None = None,
    ) -> dict:
        cfg = config or self._default_config
        system, conversation = self._extract_system(messages)

        # JSON responses need more headroom — differentials especially
        json_config = LLMConfig(
            temperature=cfg.temperature,
            max_output_tokens=max(cfg.max_output_tokens, 4096),  # ← floor at 4096
            top_p=cfg.top_p,
            top_k=cfg.top_k,
            candidate_count=cfg.candidate_count,
        )

        try:
            generation_config = self._build_generation_config(
                json_config,
                system_instruction=system,
                json_mode=True,
            )

            history = self._to_gemini_history(conversation[:-1])
            last_message = conversation[-1].content

            chat = self._client.aio.chats.create(
                model=self._model_name,
                history=history,
                config=generation_config,
            )
            response = await chat.send_message(last_message)
            raw_text = response.text

            # Attempt direct parse first
            try:
                return json.loads(raw_text)
            except json.JSONDecodeError:
                # Recovery — attempt to close truncated JSON
                recovered = _attempt_json_recovery(raw_text)
                if recovered is not None:
                    logger.warning(
                        "GeminiClient: JSON was truncated — recovered successfully. "
                        "Consider increasing max_output_tokens."
                    )
                    return recovered
                logger.error(
                    f"Gemini JSON parse error — could not recover. "
                    f"Raw (first 500 chars): {raw_text[:500]}"
                )
                raise

        except genai.errors.APIError as e:
            logger.error(f"Gemini API error in complete_json: {e}")
            raise
        except json.JSONDecodeError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in GeminiClient.complete_json: {e}")
            raise

    def _attempt_json_recovery(raw: str) -> dict | None:
        """
        Attempt to recover a truncated JSON string by closing open structures.
        Returns the parsed dict on success, None if unrecoverable.
        """
        text = raw.strip()

        # Remove markdown fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(
                line for line in lines
                if not line.strip().startswith("```")
            ).strip()

        # Count open structures to determine what needs closing
        open_braces = text.count("{") - text.count("}")
        open_brackets = text.count("[") - text.count("]")

        # If we're mid-string, close the string first
        # Count unescaped quotes to determine if we're inside a string
        in_string = False
        i = 0
        while i < len(text):
            if text[i] == '\\':
                i += 2
                continue
            if text[i] == '"':
                in_string = not in_string
            i += 1

        closing = ""
        if in_string:
            closing += '"'          # close the open string

        # Close any open arrays and objects
        closing += "]" * max(open_brackets, 0)
        closing += "}" * max(open_braces, 0)

        if not closing:
            return None

        recovered_text = text + closing
        try:
            return json.loads(recovered_text)
        except json.JSONDecodeError:
            return None

    async def health_check(self) -> bool:
        try:
            response = await self._client.aio.models.generate_content(
                model=self._model_name,
                contents="ping",
            )
            return bool(response.text)
        except Exception as e:
            logger.warning(f"Gemini health check failed: {e}")
            return False