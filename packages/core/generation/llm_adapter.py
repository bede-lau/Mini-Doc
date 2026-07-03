"""LLM adapter over HTTP.

Uses httpx directly against the OpenAI-compatible and Anthropic chat APIs so the
project avoids pinning heavy SDKs. The default provider is "offline" (handled in
qa.py) which needs no key; API providers are used only when EOS_LLM_API_KEY is
set. Any API failure degrades gracefully to the deterministic offline path, so
the pipeline never hard-fails on a flaky model call.
"""
from __future__ import annotations

from packages.core.config import Settings, get_settings
from packages.core.utils.logging import get_logger

log = get_logger(__name__)

GROUNDING_SYSTEM_PROMPT = (
    "You are an evidence-grounded compliance analyst. Answer only using retrieved "
    "evidence. Every material claim must cite source filename and page. If the "
    'evidence is insufficient, say "Insufficient evidence in the reviewed documents." '
    "Separate facts from inferences. Do not invent regulations, numbers, obligations, "
    "or policy terms. If sources conflict, flag the conflict. Respond ONLY with the "
    "JSON object described by the user, no markdown fences, no prose."
)

ABSTAIN_TEXT = "Insufficient evidence in the reviewed documents."


class LLMClient:
    """Thin wrapper that routes to the configured provider."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.s = settings or get_settings()

    @property
    def provider(self) -> str:
        return self.s.effective_llm_provider

    def complete(self, system: str, user: str) -> str:
        """Return raw model text for the given system+user prompt."""
        provider = self.provider
        if provider == "openai":
            return self._openai(system, user)
        if provider == "anthropic":
            return self._anthropic(system, user)
        raise RuntimeError("LLMClient.complete called in offline mode")

    # ------------------------------------------------------------------ #
    def _openai(self, system: str, user: str) -> str:
        import httpx

        base = (self.s.llm_base_url or "https://api.openai.com/v1").rstrip("/")
        if self.s.llm_base_url and "openai.com" not in base:
            # Guard against accidental key exfiltration to an untrusted host.
            log.warning("sending API key to non-default EOS_LLM_BASE_URL=%s; verify this is trusted.", base)
        url = f"{base}/chat/completions"
        headers = {"Authorization": f"Bearer {self.s.llm_api_key}"}
        body = {
            "model": self.s.llm_model,
            "temperature": self.s.llm_temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
        }
        resp = httpx.post(url, headers=headers, json=body, timeout=90)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    def _anthropic(self, system: str, user: str) -> str:
        import httpx

        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.s.llm_api_key or "",
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        body = {
            "model": self.s.llm_model,
            "max_tokens": 1024,
            "temperature": self.s.llm_temperature,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        resp = httpx.post(url, headers=headers, json=body, timeout=90)
        resp.raise_for_status()
        data = resp.json()
        return "".join(block.get("text", "") for block in data.get("content", []))
