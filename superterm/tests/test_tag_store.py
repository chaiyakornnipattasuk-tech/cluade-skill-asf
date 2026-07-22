from pathlib import Path

from superterm.tools.tag_store import TagStore


def test_tag_add_find_remove(tmp_path: Path):
    f = tmp_path / "report.pdf"
    f.write_text("x")
    store = TagStore(tmp_path)

    store.add_tags(str(f), ["finance", "q3"])
    assert store.tags_for(str(f)) == ["finance", "q3"]
    assert store.find_by_tag("finance") == [str(f.resolve())]

    store.remove_tags(str(f), ["q3"])
    assert store.tags_for(str(f)) == ["finance"]


def test_retag_path_follows_move(tmp_path: Path):
    old = tmp_path / "old.txt"
    old.write_text("x")
    new = tmp_path / "new.txt"
    store = TagStore(tmp_path)
    store.add_tags(str(old), ["keep"])

    store.retag_path(str(old), str(new))
    assert store.tags_for(str(new)) == ["keep"]
    assert store.tags_for(str(old)) == []


def test_tags_persist_across_instances(tmp_path: Path):
    f = tmp_path / "a.txt"
    f.write_text("x")
    TagStore(tmp_path).add_tags(str(f), ["persisted"])
    assert TagStore(tmp_path).tags_for(str(f)) == ["persisted"]
