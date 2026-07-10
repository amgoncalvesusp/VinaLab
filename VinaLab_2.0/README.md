# VinaLab 2.0

VinaLab 2.0 is a desktop molecular docking workbench with an English Qt interface,
reproducible docking projects, AutoDock Vina execution, and an element-aware xTB
rescoring route for complexes that cannot be scored safely by Vina (including boron).

## Included engines

- **Windows:** AutoDock Vina 1.2.7 and xTB 6.7.1pre are bundled in `tools/`.
- **xTB license:** LGPL-3.0-or-later; its full text is at `tools/xtb/LICENSES/COPYING`.
- **GPU:** the bundled Vina and xTB engines are CPU-only. The Pose Generation panel
  lets the user set the CPU thread count. GPU docking requires a future compatible
  engine plugin and is not claimed by this release.

## Windows installation

### End users

1. Download `VinaLab_2.0_Windows_x64.zip` from the GitHub release.
2. Extract the archive to a writable local folder, for example `C:\VinaLab_2.0`.
3. Run `VinaLab_2.0.exe`.

The application stores projects, runs, and its SQLite database in
`%LOCALAPPDATA%\VinaLab 2.0`, not inside the installation directory.

### Creating an installer

Install Python 3.11+ and run:

```powershell
py -m pip install -e ".[ui,build]"
pwsh -ExecutionPolicy Bypass -File packaging/windows/build_release.ps1
```

If Inno Setup 6 is installed, the same script also creates a standard Windows setup
executable under `release/windows/`.

## Linux installation

This repository provides the application source and a setup helper. Linux engine
binaries are platform-specific and must be installed separately before production
calculations.

```bash
git clone https://github.com/amgoncalvesusp/VinaLab.git
cd VinaLab/VinaLab_2.0
bash packaging/linux/install.sh
source .venv/bin/activate
vinalab
```

Install AutoDock Vina and xTB from their official Linux releases, then place them
at `tools/vina/vina` and `tools/xtb/bin/xtb`, respectively, or make both commands
available on `PATH`. Run the Diagnostics tab before starting a calculation.

## Development and verification

```bash
python -m pytest -q
```

The application is intentionally conservative: it blocks Vina docking when the
ligand contains unsupported exotic elements and redirects the user to the
appropriate rescoring route.
