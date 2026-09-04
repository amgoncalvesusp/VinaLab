# VinaLab Light 1.1.0

VinaLab Light 1.1.0 is a maintenance release driven by user feedback from a peptide-docking study against KPC-2. It fixes the file-preparation, layout, and export problems reported there, and adds co-crystal ligand extraction so a docking box can be centred without leaving the application.

## Fixed

- **Peptide MOL2 conversion.** The Open Babel ligand path now protonates at physiological pH (`-p 7.4`) instead of adding bare hydrogens (`-h`). MOL2 files written by Discovery Studio and similar tools — charged termini (`N.4`, `O.co2`), no explicit hydrogens — convert the same way as the equivalent command line.
- **Silent truncation of multi-molecule files.** A MOL2 or SDF holding several molecules was converted down to its first entry with no warning. The conversion log now reports how many molecules the file contains and that only the first was converted; split the file and use screening mode to dock all of them.
- **Clipped result table and filters.** Result columns were stretched to equal widths, which cut off the header text. Columns are now sized to their content and stay resizable, and the affinity/RMSD filters and the scoring-function button show their full labels.
- **Complex export exported only the pose.** The dialog is called "Export Complex" but wrote the ligand alone. It now also writes `<pose>_complex.pdb` — receptor plus docked pose in one file, with continuous atom serials, the pose as HETATM in chain Z (so `chain Z` / `hetatm` selects the ligand), and CONECT records for the ligand. The checkbox is on by default and the pose file is still exported in the chosen format.
- **Frozen export dialog.** A failure during complex export left the dialog open with a stalled progress bar and no message. Errors now surface in a dialog that states how many files were written before the failure, and Open Babel is capped at 120 s per pose so a stuck conversion cannot hang the window.

## Added

- **Co-crystal ligand extraction (Prepare Protein tab).** A new "Co-crystallized ligand" section lists the HETATM residues of the loaded PDB — waters excluded, atom counts shown so the inhibitor is distinguishable from cryoprotectants — and writes the selected residue to its own PDB file. This covers structures such as 6D15, whose two TWB copies and glycerol previously had to be separated in an external tool.
- **PDB reference ligands.** The reference/base ligand picker in the Docking tab accepts `.pdb` in addition to `.pdbqt`, so an extracted ligand can centre and size the search box directly.

## Light edition scope

Unchanged: only the native AutoDock Vina scoring functions (Vina and Vinardo) are exposed. GNINA, CNN/neural scoring, and SMINA are not part of this release or its installers.

## Packages

Release artifacts are now named for the edition (`VinaLab-Light-1.1.0-...`), the Windows installer identifies itself as "VinaLab Light", and the Linux desktop entry shows the same name.

- `VinaLab-Light-1.1.0-windows-x64-setup.exe` and `VinaLab-Light-1.1.0-windows-x64-portable.zip`
- `VinaLab-Light-1.1.0-ubuntu-x64.deb`
- `VinaLab-Light-1.1.0-linux-x64.tar.gz`
- SHA-256 checksum files for the release artifacts.

## Validation

The full suite (65 tests) passes in a single pytest process. The PySide6 stub in the docking-helper tests is now installed only when PySide6 is genuinely absent; as a leaked stub it is not a package, which broke collection of every later test module. New regression tests cover the pH-aware ligand protonation flag, the multi-molecule warning, HETATM residue discovery and extraction, and receptor-pose complex assembly.
