# VinaLab v1.0.0

## English

### Fixes

- Prevents Windows system error dialogs from `gnina.exe` when required native DLLs are missing. VinaLab now checks direct DLL imports before launching GNINA and disables the GNINA option when the bundle is incomplete.
- Keeps Windows GNINA packaging scoped: compatible libtorch DLLs are bundled only when a complete CUDA libtorch runtime is present in the build environment.
- Improves PDBQT conversion reliability by removing stale output files before conversion, keeping the largest covalent ligand fragment when salts/counterions are present, and falling back to the Open Babel CLI if the Python Open Babel API fails.
- Hardens Linux startup by setting native runtime paths, QtWebEngine flags, and the app working directory in the installed and portable launchers.

### Notes

- The current Windows checkout does not include `torch_cuda.dll`; therefore the bundled Windows `gnina.exe` cannot be made functional from the local files alone. Use the Linux/WSL GNINA path or provide a complete Windows GNINA/libtorch bundle.

### Packages

- Windows setup: `VinaLab-1.0.0-windows-x64-setup.exe`
- Windows portable: `VinaLab-1.0.0-windows-x64-portable.zip`
- Ubuntu installer: `VinaLab-1.0.0-ubuntu-x64.deb`
- Linux portable: `VinaLab-1.0.0-linux-x64.tar.gz`

---

## Português

### Correções

- Evita as janelas de erro do sistema no Windows quando o `gnina.exe` está com DLLs nativas ausentes. O VinaLab agora verifica os imports diretos de DLL antes de iniciar o GNINA e desabilita a opção quando o bundle está incompleto.
- Mantém o empacotamento do GNINA Windows restrito: DLLs compatíveis do libtorch só são incluídas quando um runtime CUDA libtorch completo está presente no ambiente de build.
- Melhora a conversão para PDBQT removendo saídas antigas antes da conversão, mantendo o maior fragmento covalente do ligante quando há sais/contraíons, e usando fallback pelo CLI do Open Babel quando a API Python do Open Babel falha.
- Fortalece a inicialização no Linux configurando caminhos de runtime nativo, flags do QtWebEngine e diretório de trabalho nos launchers instalado e portátil.

### Observações

- O checkout Windows atual não inclui `torch_cuda.dll`; portanto o `gnina.exe` Windows incluído não pode ser tornado funcional apenas com os arquivos locais. Use o caminho GNINA em Linux/WSL ou forneça um bundle Windows completo de GNINA/libtorch.

### Pacotes

- Instalador Windows: `VinaLab-1.0.0-windows-x64-setup.exe`
- Pacote portátil Windows: `VinaLab-1.0.0-windows-x64-portable.zip`
- Instalador Ubuntu: `VinaLab-1.0.0-ubuntu-x64.deb`
- Pacote portátil Linux: `VinaLab-1.0.0-linux-x64.tar.gz`
