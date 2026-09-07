import json
import os
import subprocess
import sys
from pathlib import Path


def test_ui_smoke_flag_dispatches_without_normal_application(monkeypatch):
    from vinalab_ui import main, runtime_ui_smoke
    received = []
    monkeypatch.setattr(runtime_ui_smoke, "main", lambda args: received.append(args) or 7)
    monkeypatch.setattr(main, "create_application", lambda *_: (_ for _ in ()).throw(AssertionError()))
    assert main.main(["vinalab", "--smoke-test-ui", "--ui-smoke-output", "output"]) == 7
    assert received == [["--ui-smoke-output", "output"]]


def test_ui_smoke_watchdog_terminates_a_hung_gui(tmp_path):
    code = (
        "import time; from vinalab_ui import runtime_ui_smoke as s; "
        "s._run = lambda *args: time.sleep(60); "
        "raise SystemExit(s.main(['--ui-smoke-output', " + repr(str(tmp_path)) +
        ", '--ui-smoke-timeout', '0.1']))"
    )
    result = subprocess.run([sys.executable, "-c", code], timeout=12, capture_output=True, check=False)
    assert result.returncode == 1
    report = json.loads(next(tmp_path.glob("ui-smoke-*/result.json")).read_text())
    assert not report["ok"]
    assert "timeout" in report["error"].lower()


def test_ui_smoke_real_offscreen_run_reports_health_and_is_isolated(tmp_path):
    env = {**os.environ, "LOCALAPPDATA": str(tmp_path / "user-data")}
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "vinalab_ui.main", "--smoke-test-ui",
         "--ui-smoke-output", str(tmp_path / "evidence"), "--ui-smoke-timeout", "8"],
        env=env, cwd=root, timeout=35, capture_output=True, text=True, check=False,
    )
    report = json.loads(next((tmp_path / "evidence").glob("ui-smoke-*/result.json")).read_text())
    assert result.returncode == 0 and report["ok"], (report, result.stderr)
    assert report["ui_constructed"] and report["window_sampled_colors"] > 10
    if report["webgl_ready"]:
        assert report["sampled_colors"] > 30
    else:
        assert report["limitation"] and report["renderer_gate"] == "separate_real_qt_required"
    assert report["tab"] == "Search Box"
    assert report["platform"] == "offscreen"
    assert report["png_saved"]
    assert Path(report["screenshot"]).is_file()
    assert not Path(report["project_root"]).exists()
    assert not (tmp_path / "user-data" / "VinaLab 2.0").exists()
