# VinaLab 0.0.1

Primeiro release público do VinaLab.

## Correção do pacote Windows

- `VinaLab.exe` agora é empacotado a partir de `main.py` e deve abrir o aplicativo diretamente.
- O executável Windows não deve criar `VinaLab_runtime`, `.venv` ou baixar dependências no primeiro uso.
- O inicializador `launcher.py` fica reservado para execução pelo código-fonte.
- Dependências opcionais de pontuação pesada não são instaladas automaticamente no primeiro uso.

## Artefatos

- `VinaLab-0.0.1-windows-x64-portable.zip`: pacote portátil para Windows contendo `VinaLab.exe`.
- `VinaLab-0.0.1-windows-installer.zip`: instalador Windows com `Instalar_VinaLab.bat`, `install_windows.ps1` e `VinaLab.exe`.
- `VinaLab-0.0.1-source.zip`: código-fonte e arquivos necessários para execução em Linux/macOS via Python.

## Windows

Extraia o pacote e execute:

```bat
Instalar_VinaLab.bat
```

ou:

```powershell
powershell -ExecutionPolicy Bypass -File install_windows.ps1
```

## Linux/macOS

Nesta versão, Linux e macOS usam o pacote de código-fonte. Builds compilados para esses sistemas precisam ser gerados em cada sistema operacional ou por GitHub Actions.
