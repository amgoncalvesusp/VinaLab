# VinaLab v0.0.7

## Correcoes de bugs

### Conversao de receptor para PDBQT

- A preparacao de receptor com Meeko (`mk_prepare_receptor`) agora usa `--default_altloc` e `--allow_bad_res`, evitando falhas em estruturas cristalograficas reais com residuos em localizacao alternativa.
- A conversao remove um `.pdbqt` antigo antes de executar e so reporta sucesso quando uma nova saida valida e gerada.

### GNINA CNN

- O instalador Ubuntu agora inclui o executavel Linux oficial do GNINA para habilitar a funcao de pontuacao GNINA/CNN diretamente no pacote.
- O empacotamento Windows continua incluindo o bundle GNINA quando `tools/gnina/gnina.exe` esta presente no repositorio.
- A disponibilidade do GNINA e validada em tempo de execucao na maquina do usuario, evitando que ausencia de GPU/driver na maquina de build bloqueie o release.

## Pacotes

- Windows setup: `VinaLab-0.0.7-windows-x64-setup.exe`
- Windows portable: `VinaLab-0.0.7-windows-x64-portable.zip`
- Ubuntu installer: `VinaLab-0.0.7-ubuntu-x64.deb`
- Linux portable: `VinaLab-0.0.7-linux-x64.tar.gz`
