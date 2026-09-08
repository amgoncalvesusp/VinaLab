# VinaLab Light 1.1.0

## GUI and preparation refresh (replacement packages)

- Optional Prepare Protein tab now precedes the optional converter and can save PDBQT directly using Meeko.
- Meeko is the default receptor preparation engine. Alternate conformation A is selected explicitly; incomplete residues are not silently dropped. Open Babel remains an explicit converter choice. MOL2/SDF receptors are read through Open Babel and parameterized with Meeko when residue metadata is suitable.
- Select multiple ligand files or a screening folder from a single field. Duplicate ligand filenames are rejected to prevent output collisions.
- Notebook-sized windows, scrollable result panels, and readable scrollable selection menus.
- 3D Box is the first preview tab and activates when coordinates change. High-contrast box edges replace the obscured surface/wireframe view.
- Receptor cartoon with only nearby residues highlighted as sticks; protein HETATM records are normalized for display without changing docking input files.
- Interaction methodology is identified and referenced as MDAnalysis-based geometric heuristics, not PLIP. Polar contacts are no longer mislabeled as confirmed hydrogen bonds.
- Corrected Brazilian Portuguese accents.
- Frozen Windows and Linux builds must pass dependency checks, Meeko conversion, and real Vina/Vinardo docking before publication.

This replaces the earlier v1.1.0 packages and remains the latest stable **Light** release. The separate VinaLab 2.x release is unchanged.

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


## Maintenance update

- Preserve exports from different scoring functions and existing files; preview output names before export.
- Export in a background worker, with cancellation after the current conversion (up to 120 seconds).
- Correct AutoDock atom-type normalization for reference PDB/PDBQT RMSD comparisons.
- Bundle 3Dmol.js 2.1.0 and its license for offline molecular and docking-box views.
- Send an extracted ligand directly to docking as the reference.
- Translate box and extraction controls; distinguish unavailable RMSD from failed validation.
