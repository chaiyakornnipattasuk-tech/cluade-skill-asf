from pathlib import Path

from typer.testing import CliRunner

from superterm import config as cfgmod
from superterm.cli import app

runner = CliRunner()


def _configure(tmp_path: Path, monkeypatch, workspace: Path):
    monkeypatch.setenv("SUPERTERM_HOME", str(tmp_path / ".superterm_home"))
    monkeypatch.setattr(cfgmod, "HOME_DIR", tmp_path / ".superterm_home")
    monkeypatch.setattr(cfgmod, "CONFIG_PATH", tmp_path / ".superterm_home" / "config.yaml")
    monkeypatch.setattr(cfgmod, "KEYFILE_PATH", tmp_path / ".superterm_home" / "keys.yaml")
    result = runner.invoke(app, ["config", "set-workspace", str(workspace)])
    assert result.exit_code == 0, result.output


def test_ls_tag_find_without_ai(tmp_path, monkeypatch):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "notes.txt").write_text("hi")
    _configure(tmp_path, monkeypatch, workspace)

    result = runner.invoke(app, ["ls", "."])
    assert result.exit_code == 0, result.output
    assert "notes.txt" in result.output

    result = runner.invoke(app, ["tag", "notes.txt", "important"])
    assert result.exit_code == 0, result.output

    result = runner.invoke(app, ["find", "--tag", "important"])
    assert result.exit_code == 0, result.output
    assert "notes.txt" in result.output


def test_organize_dry_run_then_apply(tmp_path, monkeypatch):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "a.py").write_text("print('hi')")
    _configure(tmp_path, monkeypatch, workspace)

    plan = runner.invoke(app, ["organize", "."])
    assert plan.exit_code == 0, plan.output
    assert "a.py -> python" in plan.output.replace("\\", "/")
    assert not (workspace / "python" / "a.py").exists()

    applied = runner.invoke(app, ["organize", ".", "--apply"])
    assert applied.exit_code == 0, applied.output
    assert (workspace / "python" / "a.py").exists()
