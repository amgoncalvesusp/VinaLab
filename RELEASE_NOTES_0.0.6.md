# VinaLab v0.0.6

## Interface and Usability

- Modernized professional light theme with consistent color tokens, typography, and spacing.
- Visible draggable horizontal and vertical scrollbars in side panels.
- Mouse-wheel protection for spin boxes and combo boxes, so scrolling no longer changes docking parameters by accident.
- Splitter handles redesigned so they are not confused with scrollbars.

## Runtime and Conversion Fixes

- Bundles PySide6/Qt6 DLLs and the Microsoft Visual C++ runtime so the app opens on clean Windows machines.
- Fixes the dependency-status crash caused by an incorrect package key in the docking tab.
- Converts receptor PDBQT in-process in the frozen app using Meeko/Open Babel instead of requiring external command-line tools.
- Bundles Open Babel support for receptor conversion and MOL2 conversion.

## Packaging Fixes

- Adds a real Windows setup installer: `VinaLab-0.0.6-windows-x64-setup.exe`.
- Keeps the portable Windows zip for users who do not want installation.
- Aligns release metadata so `VERSION`, installer metadata, UI labels, and release notes all identify 0.0.6.
- Bundles scoring archives from `pontuacao/` in the active Windows release spec.
- Verifies Meeko, Open Babel, RDKit, ProDy/Bio, and runtime dependencies before release builds.
- Bundles `obabel.exe` explicitly when available from `openbabel-wheel`.
- Enables GNINA only when its executable can start with all required local DLLs.
