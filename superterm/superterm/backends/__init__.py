from __future__ import annotations

from ..config import Config, get_api_key
from .base import AIBackend


def build_backend(cfg: Config) -> AIBackend:
    if cfg.backend == "anthropic":
        from .anthropic_backend import AnthropicBackend

        key = get_api_key("anthropic")
        if not key:
            raise RuntimeError(
                "No Anthropic API key found. Set ANTHROPIC_API_KEY or run "
                "`superterm config set-key anthropic <key>`."
            )
        return AnthropicBackend(api_key=key, model=cfg.active_model)

    if cfg.backend == "openai":
        from .openai_backend import OpenAIBackend

        key = get_api_key("openai")
        if not key:
            raise RuntimeError(
                "No OpenAI API key found. Set OPENAI_API_KEY or run "
                "`superterm config set-key openai <key>`."
            )
        return OpenAIBackend(api_key=key, model=cfg.active_model)

    if cfg.backend == "ollama":
        from .ollama_backend import OllamaBackend

        return OllamaBackend(host=cfg.ollama_host, model=cfg.active_model)

    raise ValueError(f"Unknown backend: {cfg.backend!r}")
