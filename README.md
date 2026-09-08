# VinaLab Light

VinaLab Light `v1.1.0` is the latest stable release of this project. It is a focused desktop GUI for AutoDock Vina 1.2.x, with the core docking workflow and practical result-validation tools.

## What is included

- Native AutoDock Vina scoring functions: `Vina` and `Vinardo`.
- PDB, MOL2, and SDF to PDBQT conversion for receptor and ligand preparation.
- Bundled AutoDock Vina CLI fallback for frozen Windows and Linux builds.
- Optional protein preparation before conversion, with direct Meeko PDBQT output.
- One ligand-selection field for multiple PDBQT files or a screening folder.
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

The `v1.1.0` GitHub release provides x64 packages for Windows and Ubuntu Linux:

- `VinaLab-Light-1.1.0-windows-x64-setup.exe` - Windows setup installer.
- `VinaLab-Light-1.1.0-windows-x64-portable.zip` - Windows portable package.
- `VinaLab-Light-1.1.0-ubuntu-x64.deb` - Ubuntu/Debian installer.
- `VinaLab-Light-1.1.0-linux-x64.tar.gz` - Linux portable archive.

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
sudo apt install ./VinaLab-Light-1.1.0-ubuntu-x64.deb
```

Then launch VinaLab from the application menu or run:

```bash
vinalab
```

The Debian package installs the application under `/opt/vinalab`, registers a desktop entry, and declares the required system libraries, including AutoDock Vina and Open Babel.

## Recommended workflow

1. Optionally prepare the protein (remove selected HETATM residues, choose a chain, extract a reference ligand). Save PDB or generate PDBQT directly with Meeko.
2. Convert remaining inputs to PDBQT. Meeko is the default; Open Babel is an explicit alternative. Receptor alternate conformation A is used when present; incomplete residues are not silently deleted.
3. Select the receptor and one or more ligand files (or a folder), then choose `Vina` or `Vinardo`.
4. Define the docking box manually, or select a reference ligand to center and size it. The first preview tab, **3D Box**, activates when coordinates change.
5. Review affinity, poses, contacts, clusters, and reference RMSD. Panels and selection lists support scrolling on notebook screens.
6. Export a report or open a selected pose in PyMOL when available.

## Interaction methodology

Light uses **MDAnalysis distance calculations with application-defined geometric heuristics**, not PLIP. The selected cutoff (4, 5, or 6 angstroms) identifies heavy-atom contacts. Carbon-carbon pairs within 4 angstroms are hydrophobic candidates; N/O/S pairs within 3.5 angstroms are polar contacts. These are not chemically validated hydrogen bonds: donor/acceptor roles and hydrogen-bond angles are not assigned. The table retains the shortest distance per residue and category. Contact frequency is calculated over the top ten available poses of the ligand.

References: [Michaud-Agrawal et al., 2011](https://doi.org/10.1002/jcc.21787) and [Gowers et al., 2016](https://doi.org/10.25080/majora-629e541a-00e). These describe MDAnalysis; the classification thresholds above are VinaLab heuristics, not a validated PLIP protocol.

The molecular view displays the receptor as cartoon and nearby residues as sticks. Cartoon rendering requires recognizable protein residue and backbone atom names; a PDBQT that has lost this information cannot reconstruct a protein backbone.

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
