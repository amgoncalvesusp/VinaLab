# VinaLab Light 1.1.1

Corrective stable release of the Light edition, focused on molecular preparation and complex export. This is the latest Light release; the separate VinaLab 2.x release remains available but is not marked latest.

## Fixed

- Detect PDB coordinates after long headers, not only within the first 40 lines.
- Normalize displaced PDB occupancy/element columns without moving atoms or modifying the source. Preserve two-letter elements such as chlorine and bromine.
- Read charged MOL2 variants through Open Babel when RDKit cannot parse them, then prepare PDBQT with Meeko.
- Generate 3D conformers for declared 2D ligands on the Meeko path. Reject non-3D SDF inputs on the explicit Open Babel path.
- Group receptor MOL2/SDF residues contiguously and rebuild imported hydrogens with Meeko templates.
- Validate PDBQT coordinates, charges, atom types and Meeko atom mappings before replacing an output. Preserve previous outputs on failure and reject source/output aliases and batch name collisions.
- Preserve Meeko macrocycle closure types for docking and omit nonphysical closure dummy atoms from PDB/MOL2 exports.
- Pass only successfully converted files to docking.
- Fix PDB/MOL2 exports on Unicode paths and detect empty or incomplete Open Babel results.
- Export complete receptor-pose MOL2 complexes, with separate component topology perception, preserved coordinates and atom counts. PDB complexes remain available for PDB/PDBQT pose exports.

## Included

Native Vina and Vinardo docking; optional protein preparation; PDB/MOL2/SDF conversion; 3D docking-box preview; reference-ligand box placement and RMSD validation; result tables, geometric contact analysis, clustering, reports and optional PyMOL integration. GNINA, neural scoring and SMINA are not part of Light.

## Validation and limits

Regression tests exercise real PDB, MOL2 and SDF conversions, charged/aromatic ligands, 2D inputs, Unicode paths, output preservation and all export formats. Release builds run the format matrix and real Vina/Vinardo docking plus PDB/MOL2 complex export inside each frozen Windows/Linux executable before publication.

The reported receptor/ligand pair was also tested locally: Meeko preparation, both docking functions and complex exports completed with 2,490 atoms preserved. User-provided input files are not distributed.

Receptors still need complete, recognizable residue chemistry. Multi-record receptor files are rejected. MOL2 topology is inferred from PDBQT and is not a force-field parameterization; missing nonpolar hydrogens are not restored. Interaction analysis uses documented geometric heuristics, not PLIP.

## Downloads

- Windows x64 setup installer and portable ZIP.
- Ubuntu/Debian x64 installer and Linux portable tarball.
- SHA-256 checksum manifests.
