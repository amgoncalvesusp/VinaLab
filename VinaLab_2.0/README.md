# VinaLab 2.0

Desktop docking workbench with an English Qt interface. The corrective release is
VinaLab 2.0.1. VinaLab Light 1.1.0 remains the GitHub `Latest` release; VinaLab 2.0.1
is published as an additional release for users who need the full analysis workflow.

## Implemented workflows

- Create and reopen folder-based SQLite projects; browse docking and analysis history.
- Prepare ligand PDB/MOL2/SDF/MOL files using RDKit and Meeko. Existing 3D heavy-atom
  coordinates are preserved; 2D ligands receive deterministic ETKDG coordinates.
- Prepare rigid receptor PDB/MOL2/SDF/MOL files. Meeko handles supported PDB residues;
  Open Babel bindings provide a fallback. Conversion rejects changed heavy-atom
  geometry, invalid charges, multiple receptors, and existing output files.
- Run **Vina or Vinardo** with CPU, exhaustiveness, seed and pose-count controls.
  Unsupported Vina atom types are rejected at the service boundary.
- Inspect the receptor, reference ligand and canonical docking box in an **offline
  Three.js viewer**. Rotate, zoom, reset and fit the box to reference coordinates
  with an explicit margin. The displayed box is the box supplied to Vina.
- Browse and export pose scores (CSV) and coordinates (PDBQT).
- Validate heavy-atom reference RMSD without independently superimposing ligands.
  Atom correspondence uses molecular topology, including graph-valid symmetry.
- Calculate **GFN2-xTB or GFN-FF / ALPB water frozen interaction energies** from
  prepared receptor/pocket and ligand XYZ files, with explicit charges and spins.
- Open saved receptor, poses, optional reference and box in **PyMOL when on PATH**.

Each docking run owns a unique directory containing input snapshots, output,
parameters and logs. The database records hashes, settings, lifecycle status and
errors. Relative artifact paths allow project folders to be moved. Analyses retain
input snapshots, provenance and JSON results; matching validation records are linked
to their docking run. Imported XYZ rescoring is recorded as external input, not
silently attributed to an unrelated pose.

## Scientific boundaries

**Preparation is not a substitute for chemical review.** Choose protonation,
tautomer, stereochemistry, cofactors and receptor state before docking. The converter
does not infer physiological protonation or repair an arbitrary incomplete protein.
The Open Babel receptor fallback is identified in the conversion log.

**Reference RMSD requires a common receptor coordinate frame.** Supply a reference
SDF/MOL with bond topology and either SDF poses or Meeko PDBQT with SMILES/IDX mapping
remarks. Bare PDBQT without a trustworthy atom mapping is reported as not comparable,
not zero. Receptor alignment is not performed automatically. Vina's RMSD lower/upper
bounds in the Results table are distances from its best pose, not reference RMSD.

**xTB interaction energy is not binding affinity or binding free energy.** The
reported quantity is `E(complex) - E(receptor) - E(ligand)` at frozen coordinates,
using one method/solvent for all three calculations. Complete hydrogens, charge/spin
consistency and a common coordinate frame must be confirmed. Complex coordinates are
constructed from the two fragments. Keep the same prepared/capped pocket when
comparing poses. Covalent binding, entropy, relaxation and standard-state corrections
are outside this protocol. GFN-FF does not model electronic spin.

GNINA, SMINA, PM6/SQM2.20 and UFF interaction scoring are **not implemented execution
backends**. Missing implementations are never advertised as available. xTB support
for an element does not make Vina capable of generating its poses.

## Install this checkout

Use 64-bit Python **3.11 or newer**. From `VinaLab_2.0`:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -e ".[dev,build]"
.venv\Scripts\vinalab --check-runtime
.venv\Scripts\vinalab
```

Linux, from the same directory:

```bash
bash packaging/linux/install.sh
source .venv/bin/activate
vinalab --check-runtime
vinalab
```

PySide6, RDKit, Meeko, Gemmi, Open Babel, NumPy and SciPy are declared installation
dependencies. Native engines are CPU-only. Windows includes Vina 1.2.7 and xTB
6.7.1pre. On Linux, install native `vina` and `xtb` executables and expose them on
PATH, or place them in `tools/vina/vina` and `tools/xtb/bin/xtb` with execute permission.
Windows `.exe` files are never selected on Linux. See Diagnostics for availability.

Project data defaults to `%LOCALAPPDATA%\VinaLab 2.0` on Windows and
`$XDG_DATA_HOME/VinaLab 2.0` (or `~/.local/share/VinaLab 2.0`) on Linux, not the
installation directory. Use Project to choose another location.

## Build and verification

```powershell
pwsh -File packaging/windows/build_release.ps1 -Python .venv\Scripts\python.exe
```

PyInstaller creates `dist/VinaLab_2.0`. Inno Setup, when available, additionally
creates the Windows setup executable. The v2 GitHub workflow builds artifacts only
when manually dispatched; it does not publish a release. See
[packaging contracts](packaging/README.md).
See the [local corrective-build QA report](packaging/QA-2026-09-07.md) for verified
platforms, test results and remaining release gates.

Windows builds isolate DLL discovery from unrelated Conda/tool installations.
Setup defaults to a per-user installation and is generated only after the frozen
dependency and real conversion/docking/xTB checks pass. To repeat artifact checks:

```powershell
.\dist\VinaLab_2.0\VinaLab_2.0.exe --check-runtime
.\dist\VinaLab_2.0\VinaLab_2.0.exe --smoke-test --smoke-test-output smoke.json
$env:QT_QPA_FONTDIR = "$env:WINDIR\Fonts"
.\dist\VinaLab_2.0\VinaLab_2.0.exe --smoke-test-ui --ui-smoke-output ui-evidence
```

The UI check runs offscreen in a temporary project, captures the complete window,
writes a PNG/JSON evidence folder and exits automatically. It does not open user
projects. WebGL readiness is reported separately; offscreen window construction
does not replace the real Qt renderer check below.

```bash
python -m pytest -q --cov=vinalab_core --cov=vinalab_ui --cov-branch
```

Set `VINALAB_TEST_VINA` to a native executable to require the dedicated CLI smoke
tests. GUI integration tests also exercise the installed Vina/xTB engines when
available. Browser checks in `tests/box_viewer_browser_check.js` verify offline
rendering, camera interaction and nonblank canvas pixels; `tests/box_viewer_qt_check.py`
checks the actual Qt viewer. Native Linux and clean-machine installer validation
remain separate gates, not conclusions drawn from Windows tests.

xTB is LGPL-3.0-or-later; notices are in `tools/xtb/LICENSES/COPYING`.
Offline Three.js provenance and license are bundled beside the viewer assets.
