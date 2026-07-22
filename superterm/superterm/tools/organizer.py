"""Auto-organize a folder into subfolders by classified type, by tag, or by
year-month of last modification. Always produces a plan first; applying it is a
separate, confirmation-gated step so the AI (or a human) can review moves before
anything happens on disk.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass
from pathlib import Path

from .fs_tools import classify
from .tag_store import TagStore

Strategy = str  # "type" | "tag" | "date"


@dataclass
class PlannedMove:
    source: Path
    destination: Path


def plan_organize(root: Path, target_dir: Path, strategy: Strategy, tag_store: TagStore) -> list[PlannedMove]:
    moves: list[PlannedMove] = []
    for child in sorted(target_dir.iterdir()):
        if child.is_dir() or ".superterm" in child.parts:
            continue

        if strategy == "type":
            bucket = classify(child)
        elif strategy == "tag":
            tags = tag_store.tags_for(str(child))
            bucket = tags[0] if tags else "untagged"
        elif strategy == "date":
            mtime = datetime.datetime.fromtimestamp(child.stat().st_mtime)
            bucket = mtime.strftime("%Y-%m")
        else:
            raise ValueError(f"unknown strategy: {strategy}")

        dest = target_dir / bucket / child.name
        if dest != child:
            moves.append(PlannedMove(source=child, destination=dest))
    return moves


def apply_moves(moves: list[PlannedMove], tag_store: TagStore) -> list[str]:
    results = []
    for move in moves:
        move.destination.parent.mkdir(parents=True, exist_ok=True)
        move.source.rename(move.destination)
        tag_store.retag_path(str(move.source), str(move.destination))
        results.append(f"{move.source.name} -> {move.destination.relative_to(move.destination.parents[1])}")
    return results


def format_plan(moves: list[PlannedMove], target_dir: Path) -> str:
    if not moves:
        return "(nothing to move — already organized)"
    lines = [f"{m.source.relative_to(target_dir)} -> {m.destination.relative_to(target_dir)}" for m in moves]
    return "\n".join(lines)


def register_organizer_tools(registry, workspace_root: str, tag_store: TagStore) -> None:
    from .registry import Tool
    from .fs_tools import _resolve_in_workspace

    root = Path(workspace_root).expanduser().resolve()
    _last_plan: dict[str, list[PlannedMove]] = {}

    def organize_plan(path: str = ".", strategy: str = "type") -> str:
        target = _resolve_in_workspace(root, path)
        moves = plan_organize(root, target, strategy, tag_store)
        _last_plan["moves"] = moves
        _last_plan["target"] = target
        return format_plan(moves, target)

    def organize_apply(path: str = ".", strategy: str = "type") -> str:
        target = _resolve_in_workspace(root, path)
        moves = plan_organize(root, target, strategy, tag_store)
        results = apply_moves(moves, tag_store)
        return "\n".join(results) or "(nothing to move)"

    registry.register(
        Tool(
            name="organize_plan",
            description=(
                "Preview how a folder would be reorganized into subfolders by 'type', 'tag', or "
                "'date' (year-month) — makes no changes, just returns the move list."
            ),
            parameters={"path": {"type": "string"}, "strategy": {"type": "string", "enum": ["type", "tag", "date"]}},
            required=[],
            handler=organize_plan,
        )
    )
    registry.register(
        Tool(
            name="organize_apply",
            description="Actually perform the reorganization previewed by organize_plan. Destructive: requires confirmation.",
            parameters={"path": {"type": "string"}, "strategy": {"type": "string", "enum": ["type", "tag", "date"]}},
            required=[],
            handler=organize_apply,
            destructive=True,
        )
    )
