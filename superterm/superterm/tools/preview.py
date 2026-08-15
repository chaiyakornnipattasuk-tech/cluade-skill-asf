"""Preview old/legacy source files with syntax highlighting, right in the terminal.

Also flags likely Python 2 code (vs. Python 3) using cheap syntax heuristics, since
a lot of "old python that doesn't run anymore" breaks specifically because of the
2-to-3 split, and knowing that up front is more useful than a traceback.
"""
from __future__ import annotations

import re
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

PY2_MARKERS = [
    (re.compile(r"^\s*print +[^(]", re.MULTILINE), "print statement (no parentheses)"),
    (re.compile(r"except\s+\w+\s*,\s*\w+"), "old-style `except Exc, e:`"),
    (re.compile(r"\bxrange\s*\("), "xrange()"),
    (re.compile(r"\bunicode\s*\("), "unicode()"),
    (re.compile(r"\bbasestring\b"), "basestring"),
    (re.compile(r"^\s*exec\s+[^(]", re.MULTILINE), "exec statement (no parentheses)"),
    (re.compile(r"\.has_key\s*\("), ".has_key()"),
]

LEXER_BY_EXT = {
    ".php": "php",
    ".py": "python",
    ".py2": "python",
}


def detect_python_version(source: str) -> str:
    for pattern, _label in PY2_MARKERS:
        if pattern.search(source):
            return "python2"
    return "python3"


def detect_python_markers(source: str) -> list[str]:
    return [label for pattern, label in PY2_MARKERS if pattern.search(source)]


def render_preview(path: str, console: Console | None = None) -> str:
    owns_console = console is None
    console = console or Console(record=True)
    p = Path(path)
    source = p.read_text(errors="replace")
    ext = p.suffix.lower()
    lexer = LEXER_BY_EXT.get(ext, "text")

    banner = None
    if ext == ".py":
        version = detect_python_version(source)
        if version == "python2":
            markers = detect_python_markers(source)
            banner = f"[yellow]Detected legacy Python 2 syntax[/] ({', '.join(markers)})"
    elif ext == ".php":
        version_match = re.search(r"<\?php\s*//\s*(?:v|version)?\s*(\d\.\d)", source)
        banner = "[yellow]PHP file[/]" + (f" — hints at version {version_match.group(1)}" if version_match else "")

    if banner:
        console.print(Panel(banner, expand=False))
    console.print(Syntax(source, lexer, line_numbers=True, word_wrap=False))
    return console.export_text() if owns_console else ""


def register_preview_tool(registry, workspace_root: str) -> None:
    from pathlib import Path as _Path

    from .fs_tools import _resolve_in_workspace
    from .registry import Tool

    root = _Path(workspace_root).expanduser().resolve()

    def preview_legacy_file(path: str) -> str:
        target = _resolve_in_workspace(root, path)
        if not target.is_file():
            return f"error: {path} is not a file"
        source = target.read_text(errors="replace")
        ext = target.suffix.lower()
        if ext == ".py":
            version = detect_python_version(source)
            if version == "python2":
                markers = detect_python_markers(source)
                header = f"Detected legacy Python 2 syntax: {', '.join(markers)}\n\n"
            else:
                header = "Detected Python 3 (or version-neutral) syntax.\n\n"
        elif ext == ".php":
            header = "PHP file.\n\n"
        else:
            header = ""
        return header + source[:20_000]

    registry.register(
        Tool(
            name="preview_legacy_file",
            description=(
                "Read an old PHP or Python file and report whether it looks like legacy "
                "Python 2 syntax, along with its contents, so it can be understood without running it."
            ),
            parameters={"path": {"type": "string"}},
            required=["path"],
            handler=preview_legacy_file,
        )
    )
