from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_inno_is_gated_by_runtime_and_service_reports():
    script = (ROOT / "packaging/windows/build_release.ps1").read_text()
    inno = script.index("$InnoCompiler =")
    assert script.index("Invoke-FrozenCheck '--check-runtime' '--runtime-check-output'") < inno
    assert script.index("Invoke-FrozenCheck '--smoke-test' '--smoke-test-output'") < inno
    assert "[guid]::NewGuid()" in script
    assert "ConvertFrom-Json" in script
    assert "$result.ok -ne $true" in script
    assert "WaitForExit(" in script
    assert "'xtb_gfnff'" in script


def test_per_user_inno_compiler_discovery():
    script = (ROOT / "packaging/windows/build_release.ps1").read_text()
    assert '$env:LOCALAPPDATA "Programs\\Inno Setup 6\\ISCC.exe"' in script


def test_installer_defaults_to_non_admin_user_install():
    installer = (ROOT / "packaging/windows/VinaLab_2.0.iss").read_text()
    assert "DefaultDirName={localappdata}\\Programs\\VinaLab 2.0" in installer
    assert "PrivilegesRequired=lowest" in installer
    assert "PrivilegesRequiredOverridesAllowed=dialog" in installer
