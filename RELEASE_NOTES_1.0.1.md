# VinaLab Light 1.0.1

VinaLab Light 1.0.1 is the latest stable release and focuses on a compact, reliable AutoDock Vina workflow for Windows and Ubuntu Linux.

## Included

- Native AutoDock Vina scoring functions: Vina and Vinardo.
- Bundled AutoDock Vina CLI fallback for frozen Windows and Linux builds.
- PDB, MOL2, and SDF conversion to PDBQT for receptors and ligands.
- Runtime validation for RDKit, Meeko, Open Babel, Open Babel data, and plugins during release checks.
- Docking-box editor and 3D preview showing the receptor and search volume.
- Reference/base ligand selection to center the docking box and fit its size with configurable padding.
- Reference-ligand RMSD comparison for generated poses, including a configurable pass/fail cutoff.
- Pose result tables, affinity and RMSD plots, interaction analysis, RMSD clustering, consensus views, and report export.
- Optional PyMOL handoff when PyMOL is available on the system PATH.
- In-app quick-start guidance for conversion, box setup, docking, and result review.

## Light edition scope

GNINA, CNN/neural scoring, and SMINA are not part of this release or its installers. The Light edition exposes only the native AutoDock Vina scoring functions.

## Packages

- Windows x64 setup installer and portable package.
- Ubuntu x64 Debian installer.
- Linux x64 portable archive.
- SHA-256 checksum files for the release artifacts.

## Validation

The release was checked with the conversion, Vina CLI docking, runtime dependency, packaging, and release consistency test suites on Windows and Linux.
