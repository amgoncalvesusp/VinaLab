# VinaLab v0.0.9

## Correcoes de bugs

### Inicializacao no Linux (continuacao)

- A correcao 0.0.8 (desativar o sandbox do QtWebEngine) nao bastava: no pacote congelado Linux os processos separados de GPU e auxiliar do Chromium tambem falham ao iniciar a partir do diretorio temporario do PyInstaller, derrubando o aplicativo na primeira `QWebEngineView`. Agora o QtWebEngine roda em processo unico com GPU e sandbox desativados (`QTWEBENGINE_CHROMIUM_FLAGS=--single-process --no-sandbox --disable-gpu`) e o `AA_ShareOpenGLContexts` e definido antes da `QApplication`.
- O pacote congelado nao tenta mais executar o `launcher.py` (que nao e incluido no bundle) quando a verificacao de ambiente acusa algo ausente; a janela abre e reporta o estado pela barra de status em vez de fechar silenciosamente.
- Windows e macOS nao sao afetados pelas mudancas.

## Pacotes

- Windows setup: `VinaLab-0.0.9-windows-x64-setup.exe`
- Windows portable: `VinaLab-0.0.9-windows-x64-portable.zip`
- Ubuntu installer: `VinaLab-0.0.9-ubuntu-x64.deb`
- Linux portable: `VinaLab-0.0.9-linux-x64.tar.gz`
