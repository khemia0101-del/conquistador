"""Model-agnostic AI engine supporting Ollama, OpenRouter, Anthropic, and NVIDIA."""

import os
import logging
from openai import AsyncOpenAI
from conquistador.config import get_settings

logger = logging.getLogger(__name__)


class AIEngine:
    """Unified AI interface — same code, any model provider."""

    def __init__(self):
        settings = get_settings()
        self.provider = settings.ai_provider
        self.model = settings.ai_model

        if self.provider == "ollama":
            self.base_url = settings.ai_base_url
            self.api_key = "ollama"
        elif self.provider == "openrouter":
            self.base_url = "https://openrouter.ai/api/v1"
            self.api_key = os.environ.get("OPENROUTER_API_KEY", "")
        elif self.provider == "anthropic":
            self.base_url = "https://api.anthropic.com"
            self.api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        elif self.provider == "nvidia":
            self.base_url = "https://integrate.api.nvidia.com/v1"
            self.api_key = os.environ.get("NVIDIA_API_KEY", "")
        else:
            self.base_url = settings.ai_base_url
            self.api_key = settings.ai_api_key

        self.client = AsyncOpenAI(base_url=self.base_url, api_key=self.api_key)

    async def chat(self, messages: list[dict], system_prompt: str, max_tokens: int = 300) -> str:
        """Send a chat completion request and return the response text."""
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=full_messages,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error("AI engine error: %s", e)
            return "I'm sorry, I'm having trouble right now. Please call us at 717-397-9800 for immediate help."

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
