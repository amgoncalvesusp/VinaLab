import importlib
import json
import sys


def test_smoke_dispatch_does_not_start_gui(monkeypatch):
    entry = importlib.import_module("vinalab_ui.main")
    smoke = importlib.import_module("vinalab_core.runtime_smoke")
    monkeypatch.setattr(smoke, "main", lambda argv: 7 if argv == ["--smoke-test-output", "qa.json"] else 8)
    assert entry.main(["vinalab", "--smoke-test", "--smoke-test-output", "qa.json"]) == 7


def test_windowless_smoke_writes_failure_json(monkeypatch, tmp_path):
    smoke = importlib.import_module("vinalab_core.runtime_smoke")
    monkeypatch.setattr(smoke, "run_services", lambda root: [{"name": "receptor", "ok": False, "error": "missing data"}])
    monkeypatch.setattr(sys, "stdout", None)
    output = tmp_path / "qa.json"
    assert smoke.main(["--smoke-test-output", str(output)]) == 1
    report = json.loads(output.read_text())
    assert report["ok"] is False
    assert report["steps"][0]["error"] == "missing data"


def test_smoke_writes_success_and_preserves_existing_report(monkeypatch, tmp_path):
    smoke = importlib.import_module("vinalab_core.runtime_smoke")
    monkeypatch.setattr(smoke, "run_services", lambda root: [{"name": "dock", "ok": True}])
    output = tmp_path / "qa.json"
    assert smoke.main(["--smoke-test-output", str(output)]) == 0
    original = output.read_text()
    assert smoke.main(["--smoke-test-output", str(output)]) == 2
    assert output.read_text() == original
def test_runtime_check_reports_errors_without_console(tmp_path, monkeypatch):
    import json

    from vinalab_core import runtime_check
    def fail():
        raise RuntimeError("missing runtime module")
    monkeypatch.setattr(runtime_check, "check_dependencies", fail)
    monkeypatch.setattr(runtime_check.sys, "stderr", None)
    report = tmp_path / "runtime.json"
    assert runtime_check.main(["--runtime-check-output", str(report)]) == 1
    assert json.loads(report.read_text())["error"] == "missing runtime module"
