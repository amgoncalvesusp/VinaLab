from __future__ import annotations

import importlib
from pathlib import Path


def _validator_type():
    try:
        module = importlib.import_module("vinalab_core.tools.xtb_bundle")
    except ModuleNotFoundError:
        return None
    return getattr(module, "XtbBundleValidator", None)


def test_xtb_bundle_validator_is_available_for_standalone_runtime_checks() -> None:
    assert _validator_type() is not None


def test_xtb_bundle_validator_accepts_executable_and_license_bundle(tmp_path: Path) -> None:
    validator_type = _validator_type()
    assert validator_type is not None
    bundle = tmp_path / "tools" / "xtb"
    (bundle / "LICENSES").mkdir(parents=True)
    (bundle / "xtb.exe").write_text("placeholder", encoding="utf-8")
    (bundle / "LICENSES" / "COPYING").write_text("LGPL-3.0", encoding="utf-8")

    status = validator_type(tmp_path).validate()

    assert status.ready
    assert status.executable == bundle / "xtb.exe"


def test_xtb_bundle_validator_accepts_official_bin_layout(tmp_path: Path) -> None:
    validator_type = _validator_type()
    assert validator_type is not None
    bundle = tmp_path / "tools" / "xtb"
    (bundle / "bin").mkdir(parents=True)
    (bundle / "LICENSES").mkdir()
    (bundle / "bin" / "xtb.exe").write_text("placeholder", encoding="utf-8")
    (bundle / "LICENSES" / "COPYING").write_text("LGPL-3.0", encoding="utf-8")

    status = validator_type(tmp_path).validate()

    assert status.ready
    assert status.executable == bundle / "bin" / "xtb.exe"


def test_checked_in_standalone_xtb_bundle_is_ready() -> None:
    validator_type = _validator_type()
    assert validator_type is not None

    status = validator_type(Path(__file__).resolve().parents[1]).validate()

    assert status.ready, status.errors
    assert status.executable is not None
