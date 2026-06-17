"""
src/llm/litellm_client.py

Provider-agnostic LLM client built on top of LiteLLM.

Supports any model that LiteLLM routes to, including:
    - Regolo   : openai/Llama-3.3-70B-Instruct  (uses REGOLO_API_KEY and REGOLO_API_BASE_URL)
  - Gemini   : gemini/gemini-2.0-flash         (uses GEMINI_API_KEY)
  - OpenAI   : openai/gpt-4o-mini              (uses OPENAI_API_KEY)
  - Anthropic: anthropic/claude-3-5-haiku-20241022 (uses ANTHROPIC_API_KEY)

Usage
-----
    client = LiteLLMClient()
    response = client.chat(messages=[{"role": "user", "content": "Hello"}])
    print(response.text)

    # With tools (structured tool-calling)
    response = client.chat(messages=..., tools=tool_schemas)
    if response.tool_calls:
        for tc in response.tool_calls:
            print(tc.name, tc.arguments)
"""

import os
import json
from dataclasses import dataclass, field
from typing import Any

from litellm import completion

from src.config import config, normalise_litellm_model


# ── Normalised response dataclasses ───────────────────────────────────────────

@dataclass
class ToolCall:
    """Normalised tool-call returned by the model."""
    id:        str
    name:      str
    arguments: dict = field(default_factory=dict)


@dataclass
class LLMResponse:
    """Normalised response from any LiteLLM-backed model."""
    text:       str                    # Final assistant text (empty if tool calls)
    tool_calls: list[ToolCall]         # Non-empty when model wants to call tools
    raw:        Any = None             # Raw litellm ModelResponse for debugging


# ── LiteLLM client ────────────────────────────────────────────────────────────

class LiteLLMClient:
    """
    Thin wrapper around litellm.completion that normalises tool-call responses.

    Parameters
    ----------
    model : str
        LiteLLM model string, e.g. "openai/Llama-3.3-70B-Instruct", "gemini/gemini-2.0-flash".
        Defaults to LITELLM_MODEL from config / .env.
    temperature : float
        Sampling temperature (0 = deterministic). Defaults to LLM_TEMPERATURE.
    api_key_env : str | None
        Override the environment variable name for the API key, e.g.
        "REGOLO_API_KEY". When None, LiteLLM auto-detects from the model prefix.
    task : str | None
        Task type for automatic model selection: "primary", "fast", "medical", "reasoning", etc.
        When provided, overrides the model parameter.
    """

    def __init__(
        self,
        model: str | None = None,
        temperature: float | None = None,
        api_key_env: str | None = None,
        task: str | None = None,
    ):
        # Task-based model selection (takes priority)
        if task:
            requested_model = config.get_litellm_model(task=task)
        else:
            requested_model = config.get_litellm_model(model=model)

        self.original_model = requested_model
        self.model, self.provider_alias = self._normalise_model(requested_model)
        self.provider = self.model.split("/")[0].lower() if self.model else ""

        self.temperature = temperature if temperature is not None else config.LLM_TEMPERATURE
        self.task = task
        self.api_key: str | None = None
        self.api_base: str | None = None

        # Inject provider credentials into env where LiteLLM expects them.
        if api_key_env:
            # caller explicitly told us which env var to use
            pass
        else:
            # Auto-inject from config based on model prefix
            if self._uses_regolo_backend():
                self.api_key = config.REGOLO_API_KEY or None
                self.api_base = config.LITELLM_API_BASE or config.REGOLO_API_BASE_URL
            elif self.provider == "gemini" and hasattr(config, 'GEMINI_API_KEY') and config.GEMINI_API_KEY:
                os.environ.setdefault("GEMINI_API_KEY", config.GEMINI_API_KEY)
            # For openai/anthropic the keys are expected to already be in env

    # ── Core chat method ──────────────────────────────────────────────────────

    def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        tool_choice: str = "auto",
    ) -> LLMResponse:
        """
        Send messages to the configured model.

        Parameters
        ----------
        messages    : OpenAI-format message list.
        tools       : Optional list of tool schemas (OpenAI function-calling format).
        tool_choice : "auto" | "none" | "required"  (default "auto").

        Returns
        -------
        LLMResponse with .text and .tool_calls populated.
        """
        kwargs: dict[str, Any] = {
            "model":       self.model,
            "messages":    messages,
            "temperature": self.temperature,
        }
        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.api_base:
            kwargs["api_base"] = self.api_base
        if tools:
            kwargs["tools"]       = tools
            kwargs["tool_choice"] = tool_choice

        raw = completion(**kwargs)
        return self._normalise(raw)

    @staticmethod
    def _normalise_model(model: str) -> tuple[str, str | None]:
        """
        Map repo-specific aliases onto LiteLLM-supported provider prefixes.

        Regolo exposes an OpenAI-compatible API, so LiteLLM must route it through
        the openai provider rather than a custom regolo prefix.
        """
        if not model:
            return model, None

        provider, separator, model_name = model.partition("/")
        if separator and provider.lower() == "regolo":
            return normalise_litellm_model(model), "regolo"
        return normalise_litellm_model(model), None

    def _uses_regolo_backend(self) -> bool:
        """Detect when an openai-routed model should use Regolo credentials."""
        if self.provider_alias == "regolo":
            return True

        if self.provider != "openai":
            return False

        litellm_api_base = (config.LITELLM_API_BASE or "").rstrip("/")
        regolo_api_base = (config.REGOLO_API_BASE_URL or "").rstrip("/")
        return bool(config.REGOLO_API_KEY) and litellm_api_base == regolo_api_base

    # ── Helper to normalise raw LiteLLM response ──────────────────────────────

    @staticmethod
    def _normalise(raw) -> LLMResponse:
        choice  = raw.choices[0]
        message = choice.message

        text = message.content or ""

        tool_calls: list[ToolCall] = []
        if hasattr(message, "tool_calls") and message.tool_calls:
            for tc in message.tool_calls:
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {"raw": tc.function.arguments}
                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=args,
                    )
                )

        return LLMResponse(text=text, tool_calls=tool_calls, raw=raw)

    # ── Convenience: build tool result message ─────────────────────────────────

    @staticmethod
    def tool_result_message(tool_call_id: str, name: str, content: str) -> dict:
        """Return the properly formatted tool-result message to append."""
        return {
            "role":         "tool",
            "tool_call_id": tool_call_id,
            "name":         name,
            "content":      content,
        }

    # ── Factory methods for task-based clients ────────────────────────────────

    @staticmethod
    def for_reasoning() -> "LiteLLMClient":
        """Create a client optimized for complex reasoning and analysis."""
        return LiteLLMClient(task="reasoning")

    @staticmethod
    def for_fast_tasks() -> "LiteLLMClient":
        """Create a client optimized for speed (fast model: qwen3.5-9b)."""
        return LiteLLMClient(task="fast")

    @staticmethod
    def for_medical() -> "LiteLLMClient":
        """Create a client optimized for medical domain tasks."""
        return LiteLLMClient(task="medical")

    @staticmethod
    def for_summarization() -> "LiteLLMClient":
        """Create a client optimized for text summarization."""
        return LiteLLMClient(task="summarization")

    @staticmethod
    def for_extraction() -> "LiteLLMClient":
        """Create a client optimized for information extraction."""
        return LiteLLMClient(task="extraction")

    @staticmethod
    def for_coding() -> "LiteLLMClient":
        """Create a client optimized for code analysis and generation (qwen3-coder-next)."""
        return LiteLLMClient(task="coding")

    @staticmethod
    def for_advanced_reasoning() -> "LiteLLMClient":
        """Create a client optimized for advanced reasoning (mistral-small-4-119b)."""
        return LiteLLMClient(task="advanced")

    @staticmethod
    def for_embeddings() -> "LiteLLMClient":
        """Create a client optimized for semantic embeddings (Qwen3-Embedding-8B)."""
        return LiteLLMClient(task="embedding")

    @staticmethod
    def for_task(task: str) -> "LiteLLMClient":
        """Create a client for a specific task type."""
        return LiteLLMClient(task=task)
