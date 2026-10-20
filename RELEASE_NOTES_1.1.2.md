# VinaLab Light 1.1.2

Corrective release for ligand preparation, repeated docking runs, molecular exports and execution diagnostics.

## Fixed

- Automatic ligand preparation tries Meeko first, then Open Babel. The log retains the Meeko failure and identifies the fallback engine. Explicit engine selection remains available; failed conversions preserve source files and previous outputs.
- Loaded configurations clear obsolete reference-ligand and fixed-seed settings. Each run snapshots current parameters, and rigid docking no longer reuses a previously selected rigid fragment from flexible docking.
- Reject ligand names that would generate the same normalized output name before preparation starts.
- Preserve source PDBQT files while repairing charge columns in staged run inputs.
- Export individual poses through temporary files without overwriting or deleting a neighboring PDBQT. Preserve receptor and selected-pose coordinates, chain/residue identity and validated PDB/MOL2 atom counts.
- Preserve flexible-receptor torsion/residue markers for Vina. Complexes use the docked sidechains, grouped with their residues; standalone poses contain only the ligand.
- Disambiguate repeated PDB atom names without changing elements, coordinates or connectivity, preventing strict PDB readers from dropping atoms.
- Keep prior run notes and pinned results separate when switching output folders; sort exact zero RMSD correctly.
- Show active calculation status and elapsed time, completed-job progress, and separate successful/failed counts. Execution errors remain visible and are written to a per-run log.

## Validation

Regression tests cover automatic fallback with real Open Babel, repeat-run configuration, failure reporting, output collisions and source preservation. Release builds run real Vina and Vinardo docking inside the frozen executable, test PDB/MOL2/SDF preparation and fallback, and validate atom identities/counts and coordinates in every offered export format.

Generated flexible-receptor validation uses Meeko preparation of an AKA peptide with flexible LYS A:2 and real Vina docking. Exported complexes retain all 26 receptor atoms plus 4 ligand atoms; standalone poses retain only the 4 ligand atoms. Open Babel roundtrips and strict Bio.PDB parsing verify counts and docked coordinates (tolerance 0.00051 angstrom).

## Scientific and platform limits

Open Babel and Meeko can produce different protonation, charges and atom types; Open Babel ligand preparation uses pH 7.4. Automatic receptor preparation remains strict Meeko preparation. Failed chemistry validation is not bypassed.

PDB/MOL2 exports preserve physical atoms present in PDBQT. They do not restore missing nonpolar hydrogens or original force-field topology. MOL2 bonds are perceived separately for receptor and ligand, with no invented receptor-ligand covalent bonds.

## Downloads

- Windows x64 setup installer and portable ZIP.
- Ubuntu/Debian x64 installer and Linux portable tarball.
- SHA-256 checksum manifests.

The macOS unsigned test previews remain attached to v1.1.1 and do not contain these fixes. Physical clean-machine installation is not part of the automated validation.
