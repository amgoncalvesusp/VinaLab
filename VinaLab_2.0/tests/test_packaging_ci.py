import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


def helper():
    spec = importlib.util.spec_from_file_location("verify_frozen", ROOT / "packaging/verify_frozen.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ci_pins_native_engines_and_checks_frozen_services():
    workflow = (ROOT.parent / ".github/workflows/v2-build.yml").read_text()
    assert "vina=1.2.7 xtb=6.7.1" in workflow
    assert "apt-get install -y autodock-vina" not in workflow
    assert "packaging/verify_frozen.py" in workflow


@pytest.mark.parametrize("valid", [True, False])
def test_frozen_gate_requires_complete_success_reports(tmp_path, valid):
    module = helper()

    def runner(command, **kwargs):
        steps = [{"name": name, "ok": True} for name in module.REQUIRED_STEPS]
        if not valid:
            steps = steps[:-1]
        Path(command[-1]).write_text(json.dumps({"ok": True, "steps": steps}))
        return SimpleNamespace(returncode=0)

    if valid:
        assert len(module.verify(tmp_path / "app", tmp_path, runner=runner)) == 2
    else:
        with pytest.raises(RuntimeError, match="incomplete"):
            module.verify(tmp_path / "app", tmp_path, runner=runner)
