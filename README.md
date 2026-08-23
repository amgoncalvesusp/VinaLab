# VinaLab Light

VinaLab Light `v1.0.1` is the latest stable release of this project. It is a focused desktop GUI for AutoDock Vina 1.2.x, with the core docking workflow and practical result-validation tools.

## What is included

- Native AutoDock Vina scoring functions: `Vina` and `Vinardo`.
- PDB, MOL2, and SDF to PDBQT conversion for receptor and ligand preparation.
- Bundled AutoDock Vina CLI fallback for frozen Windows and Linux builds.
- Docking setup for a rigid receptor, a ligand, or a ligand folder.
- Docking-box editor with a 3D preview of the receptor and search volume.
- Reference/base ligand selection to center the box and fit its size with padding.
- Reference-ligand RMSD comparison for new poses, with configurable pass/fail cutoff.
- Pose tables, affinity and RMSD plots, interaction analysis, RMSD clustering, and consensus views.
- Exportable docking reports and representative cluster poses.
- Optional PyMOL handoff when a PyMOL executable is available on the system `PATH`.
- English and Brazilian Portuguese interface strings, including in-app quick-start tips.

## Scope of the Light edition

This release intentionally focuses on AutoDock Vina native scoring. GNINA, CNN/neural scoring, and SMINA are not included in the Light installers. No external Conda installation is required for the Windows package; the required application runtime and Vina CLI fallback are bundled.

## Downloads

The `v1.0.1` GitHub release provides x64 packages for Windows and Ubuntu Linux:

- `VinaLab-1.0.1-windows-x64-setup.exe` - Windows setup installer.
- `VinaLab-1.0.1-windows-x64-portable.zip` - Windows portable package.
- `VinaLab-1.0.1-ubuntu-x64.deb` - Ubuntu/Debian installer.
- `VinaLab-1.0.1-linux-x64.tar.gz` - Linux portable archive.

SHA-256 checksum files are included with the release assets.

## Windows

Run the setup installer, or extract the portable archive and launch:

```bat
VinaLab.exe
```

The Windows build does not display or package GNINA. Use Linux/WSL only if you need a separate CNN-scoring workflow outside this release.

## Ubuntu Linux

Install the Debian package with:

```bash
sudo apt install ./VinaLab-1.0.1-ubuntu-x64.deb
```

Then launch VinaLab from the application menu or run:

```bash
vinalab
```

The Debian package installs the application under `/opt/vinalab`, registers a desktop entry, and declares the required system libraries, including AutoDock Vina and Open Babel.

## Recommended workflow

1. Convert the receptor and ligand to PDBQT in the conversion tab.
2. Select the receptor and ligand, then choose `Vina` or `Vinardo`.
3. Define the docking box manually, or select a reference ligand to center and size it.
4. Confirm the box in the 3D preview before running docking.
5. Review affinity, poses, interactions, clusters, and reference RMSD in the results tab.
6. Export a report or open a selected pose in PyMOL when available.

## Running from source

Use Python 3.10 or newer:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-build.txt
python launcher.py
```

On Windows, activate the environment with:

```bat
.venv\Scripts\activate
```

## Logs

Logs are written to:

- Installed Windows package: `%LOCALAPPDATA%\VinaLab\logs`
- Source checkout: `logs/`

## License and citation

VinaLab is distributed under the license in [`LICENSE`](LICENSE). For AutoDock Vina attribution, use the citation information provided by the AutoDock Vina project.
