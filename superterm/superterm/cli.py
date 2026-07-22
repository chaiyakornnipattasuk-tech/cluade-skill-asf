from __future__ import annotations

import sys
from pathlib import Path

import typer

from . import config as cfgmod
from .agent import AgentSession
from .backends import build_backend
from .repl import confirm_in_terminal, run_repl
from .tools.data_tools import register_data_tools
from .tools.fs_tools import register_fs_tools
from .tools.organizer import register_organizer_tools
from .tools.preview import register_preview_tool
from .tools.registry import ToolRegistry
from .tools.tag_store import TagStore

app = typer.Typer(help="Super Terminal: an AI-augmented shell with file, tagging, and data-source tools.")
config_app = typer.Typer(help="Manage backend/model/workspace settings.")
app.add_typer(config_app, name="config")


def _build_registry(cfg: cfgmod.Config) -> tuple[ToolRegistry, TagStore]:
    registry = ToolRegistry()
    tag_store = TagStore(cfg.workspace_root)
    register_fs_tools(registry, cfg.workspace_root, tag_store)
    register_organizer_tools(registry, cfg.workspace_root, tag_store)
    register_preview_tool(registry, cfg.workspace_root)
    connectors_path = str(cfgmod.HOME_DIR / "connectors.yaml")
    warehouse_path = str(cfgmod.HOME_DIR / "warehouse.duckdb")
    register_data_tools(registry, connectors_path, warehouse_path)
    return registry, tag_store


@app.command()
def start(workspace: str = typer.Option(None, help="Folder to treat as 'the drive' for this session.")) -> None:
    """Launch the interactive Super Terminal shell."""
    cfg = cfgmod.load_config()
    if workspace:
        cfg.workspace_root = str(Path(workspace).expanduser().resolve())
        cfgmod.save_config(cfg)

    try:
        backend = build_backend(cfg)
    except RuntimeError as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(1)

    registry, _tag_store = _build_registry(cfg)
    agent = AgentSession(backend=backend, tools=registry, confirm=confirm_in_terminal)
    run_repl(agent, cfg.workspace_root)


@app.command()
def ask(question: list[str]) -> None:
    """One-shot: ask a single question without entering the interactive shell."""
    cfg = cfgmod.load_config()
    try:
        backend = build_backend(cfg)
    except RuntimeError as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(1)
    registry, _tag_store = _build_registry(cfg)
    agent = AgentSession(backend=backend, tools=registry, confirm=confirm_in_terminal)
    typer.echo(agent.run_turn(" ".join(question)))


@config_app.command("show")
def config_show() -> None:
    cfg = cfgmod.load_config()
    typer.echo(f"backend: {cfg.backend}")
    typer.echo(f"model: {cfg.active_model}")
    typer.echo(f"workspace_root: {cfg.workspace_root}")
    typer.echo(f"ollama_host: {cfg.ollama_host}")


@config_app.command("set-backend")
def config_set_backend(backend: str = typer.Argument(..., help="anthropic | openai | ollama")) -> None:
    cfg = cfgmod.load_config()
    cfg.backend = backend
    cfgmod.save_config(cfg)
    typer.echo(f"backend set to {backend}")


@config_app.command("set-model")
def config_set_model(model: str) -> None:
    cfg = cfgmod.load_config()
    cfg.model[cfg.backend] = model
    cfgmod.save_config(cfg)
    typer.echo(f"{cfg.backend} model set to {model}")


@config_app.command("set-workspace")
def config_set_workspace(path: str) -> None:
    cfg = cfgmod.load_config()
    cfg.workspace_root = str(Path(path).expanduser().resolve())
    cfgmod.save_config(cfg)
    typer.echo(f"workspace_root set to {cfg.workspace_root}")


@config_app.command("set-key")
def config_set_key(backend: str, key: str) -> None:
    cfgmod.set_api_key(backend, key)
    typer.echo(f"key stored for {backend} (prefer exporting the env var instead if possible)")


@app.command()
def sync() -> None:
    """Sync all configured data sources into the local warehouse (no AI call)."""
    cfg = cfgmod.load_config()
    registry, _ = _build_registry(cfg)
    result = registry.call("sync_data_sources", {})
    typer.echo(result)


@app.command()
def query(sql: list[str]) -> None:
    """Run a SQL query against the local warehouse directly (no AI call)."""
    cfg = cfgmod.load_config()
    registry, _ = _build_registry(cfg)
    typer.echo(registry.call("query_data", {"sql": " ".join(sql)}))


@app.command()
def preview(path: str) -> None:
    """Syntax-highlighted preview of a file, with legacy PHP/Python-2 detection."""
    cfg = cfgmod.load_config()
    from rich.console import Console

    from .tools.preview import render_preview

    full_path = str(Path(cfg.workspace_root) / path) if not Path(path).is_absolute() else path
    render_preview(full_path, console=Console())


def main() -> None:
    app()


if __name__ == "__main__":
    sys.exit(main())
