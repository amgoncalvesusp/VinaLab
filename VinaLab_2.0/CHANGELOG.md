# Changelog

## 2.0.1 - 2026-09-07

- Corrected Windows frozen Qt startup by isolating build-time DLL discovery from
  unrelated Conda and workstation tool paths.
- Added mandatory frozen runtime and real-service checks before creating the setup.
- Added persistent run snapshots, logs, analysis history, mapped reference RMSD,
  offline search-box visualization, and safer project-relative artifact paths.
- Improved cross-platform installation diagnostics and portable test fixtures.
- Vina, Vinardo, PDBQT conversion, PyMOL integration, and GFN2/GFN-FF xTB analysis
  remain the supported execution workflows. GNINA, SMINA, PM6/SQM2.20, and UFF are
  not execution backends in this release.

## 2.0.0 - 2026-07-10

- New English desktop workflow for receptor, ligand, search-box, docking,
  rescoring, results, validation, and diagnostics.
- Reproducible search-box persistence and background Vina execution with user-set
  CPU thread limits.
- Element-aware validation that blocks unsupported Vina scoring for boron and
  other exotic elements.
- Native Windows xTB 6.7.1pre bundle for GFN2/ALPB rescoring, with LGPL notice.
- Windows standalone build configuration and Linux setup instructions.
