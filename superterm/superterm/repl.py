"""Interactive shell. Plain commands run as normal shell passthrough (so this is a
drop-in terminal replacement, not a walled garden); anything else is treated as a
natural-language request for the AI agent, which can call the tools registered in
cli.py (filesystem, tags, organizer, legacy preview, data warehouse).
"""
from __future__ import annotations

import subprocess

from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from rich.console import Console

from .agent import AgentSession

HELP = """\
Super Terminal — commands:
  <shell command>       run it directly, e.g. `ls`, `cd ..`, `git status`
  ask <question>        explicit AI request (optional — plain English also works)
  :help                  this message
  :exit / :quit          leave
Anything that isn't a recognized shell command and isn't one of the above is sent
to the AI as a natural-language request.
"""


def run_repl(agent: AgentSession, workspace_root: str) -> None:
    console = Console()
    session = PromptSession(history=InMemoryHistory())
    console.print("[bold cyan]Super Terminal[/] — type :help for commands, or just ask in plain English.")

    while True:
        try:
            line = session.prompt("superterm> ")
        except (EOFError, KeyboardInterrupt):
            break
        stripped = line.strip()
        if not stripped:
            continue
        if stripped in (":exit", ":quit"):
            break
        if stripped == ":help":
            console.print(HELP)
            continue

        if stripped.startswith("ask "):
            question = stripped[len("ask "):]
            answer = agent.run_turn(question)
            console.print(answer)
            continue

        # `cd` can't affect this process from a subprocess, so handle it separately.
        if stripped == "cd" or stripped.startswith("cd "):
            console.print("[dim]note: this REPL doesn't track a changing cwd — ask the AI to "
                          "list/read a subdirectory, or pass full paths to shell commands[/dim]")
            continue

        result = subprocess.run(stripped, shell=True, cwd=workspace_root, capture_output=True, text=True)
        if result.returncode == 0 and not result.stderr:
            console.print(result.stdout, end="")
            continue
        if result.returncode == 0:
            console.print(result.stdout, end="")
            console.print(f"[dim]{result.stderr}[/dim]", end="")
            continue

        # Shell command failed (or doesn't exist) — treat the line as a natural-language ask.
        console.print("[dim]not a shell command, asking the AI...[/dim]")
        answer = agent.run_turn(stripped)
        console.print(answer)


def confirm_in_terminal(summary: str) -> bool:
    console = Console()
    console.print(f"[yellow]About to run:[/] {summary}")
    return console.input("Proceed? [y/N] ").strip().lower() == "y"
