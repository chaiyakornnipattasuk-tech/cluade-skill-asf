from pathlib import Path

from superterm.tools.organizer import apply_moves, plan_organize
from superterm.tools.tag_store import TagStore


def test_plan_and_apply_by_type(tmp_path: Path):
    (tmp_path / "a.py").write_text("print('hi')")
    (tmp_path / "b.php").write_text("<?php ?>")
    (tmp_path / "c.txt").write_text("hello")

    tag_store = TagStore(tmp_path)
    moves = plan_organize(tmp_path, tmp_path, "type", tag_store)
    assert len(moves) == 3

    apply_moves(moves, tag_store)
    assert (tmp_path / "python" / "a.py").exists()
    assert (tmp_path / "php" / "b.php").exists()
    assert (tmp_path / "text" / "c.txt").exists()


def test_plan_by_tag(tmp_path: Path):
    f = tmp_path / "report.pdf"
    f.write_text("x")
    tag_store = TagStore(tmp_path)
    tag_store.add_tags(str(f), ["finance"])

    moves = plan_organize(tmp_path, tmp_path, "tag", tag_store)
    dest_names = [m.destination.parent.name for m in moves if m.source.name == "report.pdf"]
    assert dest_names == ["finance"]


def test_moved_file_keeps_tags(tmp_path: Path):
    f = tmp_path / "report.pdf"
    f.write_text("x")
    tag_store = TagStore(tmp_path)
    tag_store.add_tags(str(f), ["finance"])

    moves = plan_organize(tmp_path, tmp_path, "tag", tag_store)
    apply_moves(moves, tag_store)

    moved = tmp_path / "finance" / "report.pdf"
    assert moved.exists()
    assert tag_store.tags_for(str(moved)) == ["finance"]
