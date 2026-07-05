# VinaLab v0.0.8

## Correcoes de bugs

### Inicializacao no Linux

- Corrige o fechamento imediato do aplicativo no Linux logo apos abrir. O visualizador molecular usa QtWebEngine, cujo sandbox do Chromium nao funciona a partir do diretorio temporario extraido pelo PyInstaller (o `chrome-sandbox` nao e SUID root ali), o que derrubava o processo na primeira `QWebEngineView`. O sandbox agora e desativado no pacote congelado Linux antes do Qt carregar (`QTWEBENGINE_DISABLE_SANDBOX`).
- Windows e macOS nao sao afetados pela mudanca.

## Pacotes

- Windows setup: `VinaLab-0.0.8-windows-x64-setup.exe`
- Windows portable: `VinaLab-0.0.8-windows-x64-portable.zip`
- Ubuntu installer: `VinaLab-0.0.8-ubuntu-x64.deb`
- Linux portable: `VinaLab-0.0.8-linux-x64.tar.gz`
