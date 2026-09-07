# VinaLab 2.0 installation contracts

- Install the actual `VinaLab_2.0` project with Python 3.11 or newer.
  `pip install .` includes the UI and molecular-conversion dependencies;
  `pip install '.[build,dev]'` additionally prepares tests and frozen builds.
- The source/editable resource root is the project directory. Wheels stage engine
  resources into `vinalab_core/_bundled/tools`; frozen builds stage them into
  `_MEIPASS/tools`. Always resolve engines through `resource_root()`.
- Offline viewer assets retain their package-relative paths under
  `vinalab_ui/assets` or `vinalab_ui/widgets/assets` in wheels and frozen builds.
- `default_project_root()` uses LOCALAPPDATA on Windows, Application Support on
  macOS, and absolute XDG_DATA_HOME (or `~/.local/share`) on Linux. Callers create
  writable directories when needed; installed code is never a project workspace.
- Windows wheels are tagged `py3-none-win_amd64` because their engines are x64
  Windows binaries. Linux wheel/frozen resources exclude EXE/DLL files and need
  native Vina/xTB on PATH. Build each platform natively.
- Frozen builds fail before Analysis when required imports are missing. The
  resulting executable supports `--check-runtime`, exiting without creating
  the UI. Run it after freezing to detect missing collected dependencies.
- The manual v2 workflow tests/builds this subdirectory and uploads artifacts
  only. Legacy release automation excludes `v2*` tags. No publication is added.

Verification: `python -m pytest tests/test_packaging_contract.py tests/test_installation_contract.py -q`.
The installation test uses temporary environments, installs without resolving
runtime dependencies, and checks wheel, editable, and sdist-to-wheel paths from
an unrelated working directory. Dependency imports are checked separately.
