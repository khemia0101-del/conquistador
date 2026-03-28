"""Model-agnostic AI engine supporting Ollama, OpenRouter, Anthropic (Claude), and NVIDIA."""

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
            self.api_key = settings.anthropic_api_key or settings.ai_api_key
            self.client = None  # Use httpx directly for Anthropic
        else:
            if self.provider == "ollama":
                self.base_url = settings.ai_base_url
                self.api_key = "ollama"
            elif self.provider == "openrouter":
                self.base_url = "https://openrouter.ai/api/v1"
                self.api_key = settings.openrouter_api_key or settings.ai_api_key
            elif self.provider == "nvidia":
                self.base_url = "https://integrate.api.nvidia.com/v1"
                self.api_key = settings.nvidia_api_key or settings.ai_api_key
            else:
                self.base_url = settings.ai_base_url
                self.api_key = settings.ai_api_key
            logger.info("AI engine: provider=%s, model=%s, key=%s...", self.provider, self.model, self.api_key[:12] if self.api_key else "EMPTY")

            self.client = AsyncOpenAI(base_url=self.base_url, api_key=self.api_key)

    async def chat(self, messages: list[dict], system_prompt: str, max_tokens: int = 300) -> str:
        """Send a chat completion request and return the response text."""
        try:
            if self.provider == "anthropic":
                return await self._chat_anthropic(messages, system_prompt, max_tokens)
            else:
                return await self._chat_openai(messages, system_prompt, max_tokens)
        except Exception as e:
            logger.error("AI engine error (%s): %s", self.provider, e, exc_info=True)
            return (
                "Hi there! Thanks for reaching out to Conquistador Oil, Heating & Air Conditioning. "
                "I'd love to help you — please tell me what service you need (heating oil delivery, "
                "HVAC repair, AC service, or installation) and your zip code, and we'll get you taken care of!"
            )

    async def _chat_openai(self, messages: list[dict], system_prompt: str, max_tokens: int) -> str:
        """Chat via OpenAI-compatible API (Ollama, OpenRouter, NVIDIA)."""
        full_messages = [{"role": "system", "content": system_prompt}] + messages

        # Kimi K2.5 on NVIDIA returns content in 'reasoning' field, not 'content'.
        # Use httpx directly to access the raw JSON response.
        if "kimi" in self.model:
            return await self._chat_kimi(full_messages, max_tokens)

        kwargs: dict = {
            "model": self.model,
            "messages": full_messages,
            "max_tokens": max_tokens,
        }

        response = await self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    async def _chat_kimi(self, messages: list[dict], max_tokens: int) -> str:
        """Chat via NVIDIA API for Kimi K2.5 — uses httpx to access 'reasoning' field."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": 0.6,
                },
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            logger.info("Kimi raw response keys: %s", list(data.get("choices", [{}])[0].get("message", {}).keys()))
            msg = data["choices"][0]["message"]
            # Kimi puts text in 'reasoning', not 'content'
            text = msg.get("content") or msg.get("reasoning") or msg.get("reasoning_content") or ""
            if not text.strip():
                logger.warning("Kimi returned empty text. Full message: %s", msg)
            return text

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
