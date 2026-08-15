"""Config: which AI backend to use, and which local folder ("the drive") is in scope.

Everything lives under ~/.superterm/ so the tool never touches project source trees.
API keys are read from environment variables first; a local keyfile is only a fallback
so the CLI is usable without exporting env vars every session.
"""
from __future__ import annotations

import os
import stat
from dataclasses import dataclass, field
from pathlib import Path

import yaml

HOME_DIR = Path(os.environ.get("SUPERTERM_HOME", Path.home() / ".superterm"))
CONFIG_PATH = HOME_DIR / "config.yaml"
KEYFILE_PATH = HOME_DIR / "keys.yaml"

DEFAULT_CONFIG = {
    "backend": "anthropic",  # anthropic | openai | ollama
    "model": {
        "anthropic": "claude-sonnet-5",
        "openai": "gpt-4o-mini",
        "ollama": "llama3.1",
    },
    "ollama_host": "http://localhost:11434",
    "workspace_root": str(Path.home()),
    "require_confirmation": True,
}


@dataclass
class Config:
    backend: str = "anthropic"
    model: dict = field(default_factory=lambda: dict(DEFAULT_CONFIG["model"]))
    ollama_host: str = "http://localhost:11434"
    workspace_root: str = str(Path.home())
    require_confirmation: bool = True

    @property
    def active_model(self) -> str:
        return self.model.get(self.backend, "")


def ensure_home() -> None:
    HOME_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> Config:
    ensure_home()
    if not CONFIG_PATH.exists():
        save_config(Config())
    data = yaml.safe_load(CONFIG_PATH.read_text()) or {}
    merged = {**DEFAULT_CONFIG, **data}
    return Config(
        backend=merged["backend"],
        model={**DEFAULT_CONFIG["model"], **merged.get("model", {})},
        ollama_host=merged.get("ollama_host", DEFAULT_CONFIG["ollama_host"]),
        workspace_root=merged.get("workspace_root", DEFAULT_CONFIG["workspace_root"]),
        require_confirmation=merged.get("require_confirmation", True),
    )


def save_config(cfg: Config) -> None:
    ensure_home()
    CONFIG_PATH.write_text(
        yaml.safe_dump(
            {
                "backend": cfg.backend,
                "model": cfg.model,
                "ollama_host": cfg.ollama_host,
                "workspace_root": cfg.workspace_root,
                "require_confirmation": cfg.require_confirmation,
            },
            sort_keys=False,
        )
    )


def set_api_key(backend: str, key: str) -> None:
    """Store a key locally, chmod 600. Prefer env vars (ANTHROPIC_API_KEY / OPENAI_API_KEY) when set."""
    ensure_home()
    keys = {}
    if KEYFILE_PATH.exists():
        keys = yaml.safe_load(KEYFILE_PATH.read_text()) or {}
    keys[backend] = key
    KEYFILE_PATH.write_text(yaml.safe_dump(keys))
    KEYFILE_PATH.chmod(stat.S_IRUSR | stat.S_IWUSR)


def get_api_key(backend: str) -> str | None:
    env_map = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY"}
    env_var = env_map.get(backend)
    if env_var and os.environ.get(env_var):
        return os.environ[env_var]
    if KEYFILE_PATH.exists():
        keys = yaml.safe_load(KEYFILE_PATH.read_text()) or {}
        return keys.get(backend)
    return None
