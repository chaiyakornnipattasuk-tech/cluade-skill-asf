from pathlib import Path

import pytest

from superterm.tools.fs_tools import WorkspaceError, _resolve_in_workspace, classify
from superterm.tools.registry import ToolRegistry
from superterm.tools.tag_store import TagStore
from superterm.tools.fs_tools import register_fs_tools


def test_classify_types(tmp_path: Path):
    php = tmp_path / "old.php"
    php.write_text("<?php echo 'hi'; ?>")
    py = tmp_path / "script.py"
    py.write_text("print('hi')")
    assert classify(php) == "php"
    assert classify(py) == "python"
    assert classify(tmp_path) == "directory"


def test_resolve_blocks_escape(tmp_path: Path):
    with pytest.raises(WorkspaceError):
        _resolve_in_workspace(tmp_path, "../../etc/passwd")


def test_search_and_tag_via_registry(tmp_path: Path):
    (tmp_path / "notes.txt").write_text("hello")
    (tmp_path / "data.csv").write_text("a,b\n1,2\n")

    registry = ToolRegistry()
    tag_store = TagStore(tmp_path)
    register_fs_tools(registry, str(tmp_path), tag_store)

    listing = registry.call("list_dir", {"path": "."})
    assert "notes.txt" in listing
    assert "data.csv" in listing

    registry.call("tag_file", {"path": "notes.txt", "tags": "important"})
    results = registry.call("search_files", {"tag": "important"})
    assert "notes.txt" in results

    csvs = registry.call("search_files", {"file_type": "data"})
    assert "data.csv" in csvs
