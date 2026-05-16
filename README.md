# VinaLab

## English

VinaLab is a desktop interface for AutoDock Vina 1.2.x. It helps prepare PDBQT inputs, run molecular docking jobs, inspect docking results, visualize poses, and generate reports.

### Downloads

Stable releases are published from Git tags such as `v0.0.2`. The release workflow builds native packages for:

- Windows: installer zip and portable executable zip
- macOS: native executable archive
- Linux: native executable archive

### Windows

Download `VinaLab-<version>-windows-x64-installer.zip`, extract it, and run:

```bat
Instalar_VinaLab.bat
```

The installer copies `VinaLab.exe` to `%LOCALAPPDATA%\VinaLab` and creates a desktop shortcut.

The portable package can also be extracted and run directly:

```bat
VinaLab.exe
```

### macOS

Download the macOS archive, extract it, allow execution if needed, and run the bundled `VinaLab` executable.

```bash
chmod +x VinaLab
./VinaLab
```

### Linux

Download the Linux archive, extract it, allow execution if needed, and run the bundled `VinaLab` executable.

```bash
chmod +x VinaLab
./VinaLab
```

### Running From Source

Install Python 3.10+ and run:

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

### Logs

Logs are written to:

- Installed Windows package: `%LOCALAPPDATA%\VinaLab\logs`
- Source checkout: `logs/`

### Optional Scoring Runtimes

Optional scoring methods that depend on large runtimes, such as Torch/DGL, may be disabled until their dependencies are installed in the active environment.

---

## Português

VinaLab é uma interface desktop para AutoDock Vina 1.2.x. Ele ajuda a preparar entradas PDBQT, executar docking molecular, inspecionar resultados, visualizar poses e gerar relatórios.

### Downloads

Releases estáveis são publicados a partir de tags Git como `v0.0.2`. O workflow de release gera pacotes nativos para:

- Windows: zip com instalador e zip portátil com executável
- macOS: arquivo compactado com executável nativo
- Linux: arquivo compactado com executável nativo

### Windows

Baixe `VinaLab-<versão>-windows-x64-installer.zip`, extraia o pacote e execute:

```bat
Instalar_VinaLab.bat
```

O instalador copia `VinaLab.exe` para `%LOCALAPPDATA%\VinaLab` e cria um atalho na Área de Trabalho.

O pacote portátil também pode ser extraído e executado diretamente:

```bat
VinaLab.exe
```

### macOS

Baixe o arquivo para macOS, extraia, permita execução se necessário e execute o binário `VinaLab`.

```bash
chmod +x VinaLab
./VinaLab
```

### Linux

Baixe o arquivo para Linux, extraia, permita execução se necessário e execute o binário `VinaLab`.

```bash
chmod +x VinaLab
./VinaLab
```

### Execução Pelo Código-Fonte

Instale Python 3.10+ e execute:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-build.txt
python launcher.py
```

No Windows, ative o ambiente com:

```bat
.venv\Scripts\activate
```

### Logs

Logs são gravados em:

- Pacote Windows instalado: `%LOCALAPPDATA%\VinaLab\logs`
- Código-fonte: `logs/`

### Runtimes Opcionais de Pontuação

Métodos opcionais de pontuação que dependem de runtimes grandes, como Torch/DGL, podem aparecer como desativados até que suas dependências sejam instaladas no ambiente ativo.
