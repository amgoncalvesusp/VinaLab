# VinaLab

## English

VinaLab is a desktop interface for AutoDock Vina 1.2.x. It helps prepare PDBQT inputs, run molecular docking jobs, inspect docking results, visualize poses, and generate reports.

### Downloads

Stable releases are published from Git tags such as `v1.0.0`. The current release workflow builds Windows and Ubuntu x64 packages:

- Windows setup installer: `VinaLab-<version>-windows-x64-setup.exe`
- Windows portable archive: `VinaLab-<version>-windows-x64-portable.zip`
- Ubuntu installer: `VinaLab-<version>-ubuntu-x64.deb`
- Linux portable archive: `VinaLab-<version>-linux-x64.tar.gz`

### Windows

Download and run the setup installer:

```bat
VinaLab-<version>-windows-x64-setup.exe
```

The setup installer installs `VinaLab.exe`, registers an uninstaller, and creates shortcuts.

The portable package can also be extracted and run directly:

```bat
VinaLab.exe
```

### Ubuntu Linux

Download and install the Ubuntu package with apt so system dependencies are resolved:

```bash
sudo apt install ./VinaLab-<version>-ubuntu-x64.deb
```

Launch it from the application menu or run:

```bash
vinalab
```

The Ubuntu package installs the app under `/opt/vinalab`, registers a desktop entry, installs the application icon, includes an AutoDock Vina CLI fallback in the frozen app, and ships the GNINA Linux executable for CNN scoring.

macOS is supported from source only in this release.

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

## Portugues

VinaLab e uma interface desktop para AutoDock Vina 1.2.x. Ele ajuda a preparar entradas PDBQT, executar docking molecular, inspecionar resultados, visualizar poses e gerar relatorios.

### Downloads

Releases estáveis são publicados a partir de tags Git como `v1.0.0`. O workflow de release atual gera pacotes Windows e Ubuntu x64:

- Instalador Windows: `VinaLab-<versao>-windows-x64-setup.exe`
- Pacote portatil Windows: `VinaLab-<versao>-windows-x64-portable.zip`
- Instalador Ubuntu: `VinaLab-<versao>-ubuntu-x64.deb`
- Pacote portatil Linux: `VinaLab-<versao>-linux-x64.tar.gz`

### Windows

Baixe e execute o instalador:

```bat
VinaLab-<versao>-windows-x64-setup.exe
```

O instalador instala `VinaLab.exe`, registra um desinstalador e cria atalhos.

O pacote portatil tambem pode ser extraido e executado diretamente:

```bat
VinaLab.exe
```

### Ubuntu Linux

Baixe e instale o pacote Ubuntu com apt para resolver as dependencias de sistema:

```bash
sudo apt install ./VinaLab-<versao>-ubuntu-x64.deb
```

Abra pelo menu de aplicativos ou execute:

```bash
vinalab
```

O pacote Ubuntu instala o app em `/opt/vinalab`, registra a entrada desktop, instala o icone da aplicacao, inclui um fallback CLI do AutoDock Vina no app congelado e distribui o executavel Linux do GNINA para pontuacao CNN.

macOS e suportado pelo codigo-fonte nesta release.

### Execucao Pelo Codigo-Fonte

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

Os logs sao gravados em:

- Pacote Windows instalado: `%LOCALAPPDATA%\VinaLab\logs`
- Checkout pelo codigo-fonte: `logs/`

### Runtimes Opcionais de Pontuacao

Metodos opcionais de pontuacao que dependem de runtimes grandes, como Torch/DGL, podem ficar desativados ate que suas dependencias sejam instaladas no ambiente ativo.
