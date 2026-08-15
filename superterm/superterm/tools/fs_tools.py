"""Filesystem tools exposed to the AI. Every path is resolved and checked against
the workspace root before touching disk — the model cannot read or move files
outside the folder the user configured as "the drive" for this session.
"""
from __future__ import annotations

import mimetypes
import shutil
from pathlib import Path

from .registry import Tool, ToolRegistry
from .tag_store import TagStore

MAX_READ_BYTES = 200_000


class WorkspaceError(Exception):
    pass


def _resolve_in_workspace(root: Path, path: str) -> Path:
    resolved = (root / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        raise WorkspaceError(f"{path!r} is outside the workspace root {root}") from None
    return resolved


def classify(path: Path) -> str:
    if path.is_dir():
        return "directory"
    ext = path.suffix.lower()
    kind, _ = mimetypes.guess_type(path.name)
    if ext in {".php"}:
        return "php"
    if ext in {".py"}:
        return "python"
    if ext in {".md", ".txt", ".rst"}:
        return "text"
    if ext in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
        return "image"
    if ext in {".csv", ".tsv", ".xlsx", ".json", ".yaml", ".yml"}:
        return "data"
    return kind or (ext.lstrip(".") or "unknown")


def register_fs_tools(registry: ToolRegistry, workspace_root: str, tag_store: TagStore) -> None:
    root = Path(workspace_root).expanduser().resolve()

    def list_dir(path: str = ".") -> str:
        target = _resolve_in_workspace(root, path)
        if not target.is_dir():
            return f"error: {path} is not a directory"
        entries = []
        for child in sorted(target.iterdir()):
            kind = classify(child)
            tags = tag_store.tags_for(str(child))
            tag_str = f" [{','.join(tags)}]" if tags else ""
            size = child.stat().st_size if child.is_file() else "-"
            entries.append(f"{kind:10} {size!s:>10}  {child.name}{tag_str}")
        return "\n".join(entries) or "(empty)"

    def read_file(path: str, max_bytes: int = MAX_READ_BYTES) -> str:
        target = _resolve_in_workspace(root, path)
        if not target.is_file():
            return f"error: {path} is not a file"
        data = target.read_bytes()[:max_bytes]
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return f"(binary file, {target.stat().st_size} bytes, cannot preview as text)"

    def search_files(query: str = "", file_type: str = "", tag: str = "") -> str:
        """Search by filename substring, classified type (e.g. python/php/image/data), and/or tag."""
        matches = []
        if tag:
            matches = [Path(p) for p in tag_store.find_by_tag(tag)]
        else:
            for child in root.rglob("*"):
                if ".superterm" in child.parts:
                    continue
                if query and query.lower() not in child.name.lower():
                    continue
                if file_type and classify(child) != file_type:
                    continue
                matches.append(child)
        return "\n".join(str(m) for m in matches[:500]) or "(no matches)"

    def tag_file(path: str, tags: str) -> str:
        target = _resolve_in_workspace(root, path)
        tag_store.add_tags(str(target), tags.split(","))
        return f"tagged {target.name} with: {tags}"

    def move_file(source: str, destination: str) -> str:
        src = _resolve_in_workspace(root, source)
        dst = _resolve_in_workspace(root, destination)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        tag_store.retag_path(str(src), str(dst))
        return f"moved {source} -> {destination}"

    registry.register(
        Tool(
            name="list_dir",
            description="List a directory's contents (type, size, tags) relative to the workspace root.",
            parameters={"path": {"type": "string", "description": "Directory path, default '.'"}},
            required=[],
            handler=list_dir,
        )
    )
    registry.register(
        Tool(
            name="read_file",
            description="Read a text file's contents (truncated for very large files).",
            parameters={"path": {"type": "string"}, "max_bytes": {"type": "integer"}},
            required=["path"],
            handler=read_file,
        )
    )
    registry.register(
        Tool(
            name="search_files",
            description=(
                "Search files under the workspace by name substring, classified type "
                "(python/php/image/data/text/...), and/or tag."
            ),
            parameters={
                "query": {"type": "string"},
                "file_type": {"type": "string"},
                "tag": {"type": "string"},
            },
            required=[],
            handler=search_files,
        )
    )
    registry.register(
        Tool(
            name="tag_file",
            description="Attach one or more comma-separated tags to a file (stored in a sidecar DB, file untouched).",
            parameters={"path": {"type": "string"}, "tags": {"type": "string"}},
            required=["path", "tags"],
            handler=tag_file,
        )
    )
    registry.register(
        Tool(
            name="move_file",
            description="Move or rename a file within the workspace. Destructive: requires user confirmation.",
            parameters={"source": {"type": "string"}, "destination": {"type": "string"}},
            required=["source", "destination"],
            handler=move_file,
            destructive=True,
        )
    )
