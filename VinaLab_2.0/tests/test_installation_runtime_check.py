import importlib
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_runtime_flag_exits_without_creating_application(monkeypatch):
    entry = importlib.import_module("vinalab_ui.main")
    checker = importlib.import_module("vinalab_core.runtime_check")
    monkeypatch.setattr(checker, "check_dependencies", lambda: None)

    def no_gui(*args):
        pytest.fail("Runtime check created a GUI")

    monkeypatch.setattr(entry, "create_application", no_gui)
    assert entry.main(["vinalab", "--check-runtime"]) == 0


def test_runtime_failure_without_console_returns_one(monkeypatch):
    checker = importlib.import_module("vinalab_core.runtime_check")

    def missing():
        raise RuntimeError("missing meeko")

    monkeypatch.setattr(checker, "check_dependencies", missing)
    monkeypatch.setattr(sys, "stderr", None)
    assert checker.main() == 1


def test_runtime_flag_checks_before_ui_imports():
    code = """
import sys
from importlib.abc import MetaPathFinder
class NoUi(MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'vinalab_ui.mainwindow':
            raise RuntimeError('UI imported before runtime dispatch')
sys.meta_path.insert(0, NoUi())
from vinalab_ui.main import main
raise SystemExit(main(['vinalab', '--check-runtime']))
"""
    result = subprocess.run([sys.executable, "-c", code], cwd=ROOT,
                            capture_output=True, text=True, timeout=60, check=False)
    assert result.returncode == 0, result.stdout + result.stderr


def test_frozen_launcher_forwards_runtime_flag(tmp_path):
    result = subprocess.run(
        [sys.executable, str(ROOT / "packaging/frozen_entry.py"), "--check-runtime"],
        cwd=tmp_path, capture_output=True, text=True, timeout=60, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
