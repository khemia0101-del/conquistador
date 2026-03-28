"""Model-agnostic AI engine supporting Ollama, OpenRouter, Anthropic (Claude), and NVIDIA."""

import os
import logging
import httpx
from openai import AsyncOpenAI
from conquistador.config import get_settings

logger = logging.getLogger(__name__)


class AIEngine:
    """Unified AI interface — same code, any model provider."""

    def __init__(self):
        settings = get_settings()
        self.provider = settings.ai_provider
        self.model = settings.ai_model

        if self.provider == "anthropic":
            # Claude uses its own API format, not OpenAI-compatible
            self.api_key = os.environ.get("ANTHROPIC_API_KEY", settings.ai_api_key)
            self.client = None  # Use httpx directly for Anthropic
        else:
            if self.provider == "ollama":
                self.base_url = settings.ai_base_url
                self.api_key = "ollama"
            elif self.provider == "openrouter":
                self.base_url = "https://openrouter.ai/api/v1"
                self.api_key = os.environ.get("OPENROUTER_API_KEY", "")
            elif self.provider == "nvidia":
                self.base_url = "https://integrate.api.nvidia.com/v1"
                self.api_key = os.environ.get("NVIDIA_API_KEY", "")
            else:
                self.base_url = settings.ai_base_url
                self.api_key = settings.ai_api_key

            self.client = AsyncOpenAI(base_url=self.base_url, api_key=self.api_key)

    async def chat(self, messages: list[dict], system_prompt: str, max_tokens: int = 300) -> str:
        """Send a chat completion request and return the response text."""
        try:
            if self.provider == "anthropic":
                return await self._chat_anthropic(messages, system_prompt, max_tokens)
            else:
                return await self._chat_openai(messages, system_prompt, max_tokens)
        except Exception as e:
            logger.error("AI engine error (%s): %s", self.provider, e)
            return "I'm sorry, I'm having trouble right now. Please call us at 717-397-9800 for immediate help."

    async def _chat_openai(self, messages: list[dict], system_prompt: str, max_tokens: int) -> str:
        """Chat via OpenAI-compatible API (Ollama, OpenRouter, NVIDIA)."""
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        kwargs: dict = {
            "model": self.model,
            "messages": full_messages,
            "max_tokens": max_tokens,
        }

        # Kimi K2.5 on NVIDIA: recommended temp
        if "kimi" in self.model:
            kwargs["temperature"] = 0.6

        response = await self.client.chat.completions.create(**kwargs)
        msg = response.choices[0].message
        content = msg.content
        # Kimi K2.5 puts output in 'reasoning' field instead of 'content'
        if content is None:
            content = getattr(msg, 'reasoning', None) or getattr(msg, 'reasoning_content', None)
        return content or "I'm sorry, I'm having trouble right now. Please call us at 717-397-9800 for immediate help."

    async def _chat_anthropic(self, messages: list[dict], system_prompt: str, max_tokens: int) -> str:
        """Chat via Anthropic's native Messages API (Claude)."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "system": system_prompt,
                    "messages": messages,
                },
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            return data["content"][0]["text"]

    async def extract_json(self, conversation: list[dict], extraction_prompt: str) -> str:
        """Extract structured JSON from a conversation."""
        conv_text = "\n".join(f"{m['role']}: {m['content']}" for m in conversation)
        messages = [{"role": "user", "content": f"{extraction_prompt}\n\nConversation:\n{conv_text}"}]
        return await self.chat(messages, "You are a data extraction assistant. Return ONLY valid JSON.", max_tokens=500)


_engine: AIEngine | None = None


def get_ai_engine() -> AIEngine:
    global _engine
    if _engine is None:
        _engine = AIEngine()
    return _engine
