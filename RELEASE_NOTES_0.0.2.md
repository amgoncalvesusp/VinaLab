# VinaLab 0.0.2

## English

This release prepares VinaLab for public GitHub releases built from tags.

### Changes

- Added GitHub Actions release workflow for Windows, macOS, and Linux native builds.
- Added automated packaging and checksum generation for release assets.
- Added bilingual README with English first and Portuguese second.
- Added `requirements-build.txt` for lean release builds without optional heavy scoring runtimes.
- Kept optional Torch/DGL-based scoring dependencies out of first-run setup.

### Release Assets

The GitHub Release created from tag `v0.0.2` should include:

- `VinaLab-0.0.2-windows-x64-installer.zip`
- `VinaLab-0.0.2-windows-x64-portable.zip`
- `VinaLab-0.0.2-macos-x64.tar.gz`
- `VinaLab-0.0.2-linux-x64.tar.gz`
- `SHA256SUMS-*.txt`

---

## Português

Este release prepara o VinaLab para releases públicos no GitHub gerados a partir de tags.

### Mudanças

- Adicionado workflow GitHub Actions para builds nativos de Windows, macOS e Linux.
- Adicionado empacotamento automático e geração de checksums dos artefatos.
- Adicionado README bilíngue com inglês primeiro e português em seguida.
- Adicionado `requirements-build.txt` para builds de release sem runtimes opcionais pesados de pontuação.
- Dependências opcionais baseadas em Torch/DGL continuam fora do setup automático inicial.

### Artefatos do Release

O GitHub Release criado a partir da tag `v0.0.2` deve incluir:

- `VinaLab-0.0.2-windows-x64-installer.zip`
- `VinaLab-0.0.2-windows-x64-portable.zip`
- `VinaLab-0.0.2-macos-x64.tar.gz`
- `VinaLab-0.0.2-linux-x64.tar.gz`
- `SHA256SUMS-*.txt`
