# Changelog

## 1.0.1 - 2026-07-07

- Remove GNINA dos builds Windows; a UI Windows exibe apenas Vina/Vinardo/AD4 e pontuadores opcionais disponiveis.
- Mantem GNINA apenas para Linux/WSL ou builds futuros com bundle nativo comprovadamente completo.
- Garante que o fallback AutoDock Vina CLI rode com `native_tool_env`, igual aos outros binarios nativos.
- Reforca a checagem de runtime empacotado para RDKit, Meeko, `meeko.cli.mk_prepare_receptor`, Open Babel, `obabel`, plugins `.obf`, `openbabel_wheel.libs` e Vina CLI.
- Adiciona SMINA como backend opcional detectado em `tools/smina`, PATH ou Conda, sem bloquear builds Windows/Linux.
- Adiciona testes de regressao para ausencia de GNINA/libtorch no spec Windows, ambiente do Vina CLI, runtime Open Babel e smoke tests opcionais de conversao/docking.

## 1.0.0 - 2026-07-06

- Evita janelas de erro do Windows ao detectar DLLs nativas ausentes do `gnina.exe` antes de iniciar o processo.
- Prepara o empacotamento para incluir DLLs libtorch do GNINA Windows somente quando um runtime CUDA completo estiver disponível.
- Reforça a conversão para PDBQT com remoção de saídas antigas, seleção do maior fragmento covalente do ligante e fallback pelo CLI do Open Babel.
- Fortalece os launchers Linux instalado e portátil com caminhos nativos, flags QtWebEngine e diretório de trabalho explícitos.

## 0.0.9 - 2026-07-05

- Corrige de fato o fechamento imediato no Linux: QtWebEngine agora roda em processo unico com GPU/sandbox desativados (`--single-process --no-sandbox --disable-gpu`) e `AA_ShareOpenGLContexts` e definido antes da `QApplication`.
- O pacote congelado nao tenta mais rodar o `launcher.py` ausente quando a verificacao de ambiente falha, evitando um fechamento silencioso.

## 0.0.8 - 2026-07-04

- Corrige o fechamento imediato do aplicativo no Linux: desativa o sandbox do QtWebEngine no pacote congelado (`QTWEBENGINE_DISABLE_SANDBOX`), que impedia a `QWebEngineView` de iniciar a partir do diretorio temporario do PyInstaller.

## 0.0.7 - 2026-07-04

- Corrige a preparacao de receptores PDBQT com localizacao alternativa usando `--default_altloc`.
- Evita falso sucesso quando um `.pdbqt` antigo ja existia na pasta de saida.
- Adiciona o instalador Ubuntu e o pacote Linux portatil ao release 0.0.7.
- Inclui o executavel Linux oficial do GNINA no pacote Ubuntu/Linux para habilitar pontuacao GNINA/CNN.

## 0.0.6 - 2026-06-09

- Design profissional modernizado: tema claro com tokens de cor consistentes, tipografia e espacamento calibrados.
- Barras de rolagem draggaveis (H+V) em todos os paineis laterais com espessura aumentada para melhor usabilidade.
- Protecao contra alteracao acidental de parametros via scroll do mouse: roda do mouse em spinbox/combobox rola o painel sem mudar o valor.
- Handles do splitter redesenhados para nao confundir com barras de rolagem.

## 0.0.5 - 2026-06-09

- Ligantes MOL2 e SDF convertem para PDBQT via Open Babel como fallback.
- Barras de rolagem horizontal e vertical nos paineis de opcoes e workspace lateral.
- Numero maximo de poses aumentado de 20 para 100.
- Checklist de pre-execucao acima do botao Executar.
- "Ajustar caixa ao ligante" centraliza a caixa, remove aviso falso de atomos fora da caixa.
- Graficos de afinidade e clusters interativos com Plotly.
- "Abrir no PyMOL" detecta PyMOL no PATH e em instalacoes Windows (Schrodinger incluido).
- MDAnalysis incluido — interacoes receptor-ligante calculadas novamente.
- Confirmacao ao fechar a janela.
- Estrelas das funcoes de pontuacao removidas do seletor.
- GNINA (CNN) incluido para Windows.
- AutoDock4 exibe mensagem clara sobre necessidade de mapas AutoGrid4.

## 0.0.4 - 2026-06-02

- Prepara release da nova versao com melhorias acumuladas de interface, docking, conversao, resultados e pontuacao.
- Adiciona pacotes Windows portatil e instalador para publicacao no GitHub.
- Atualiza o workflow de release para usar as notas da versao 0.0.4.

## 0.0.2 - 2026-05-16

- Adiciona GitHub Actions para gerar builds nativos de Windows, macOS e Linux a partir de tags `v*`.
- Adiciona empacotamento automatizado dos artefatos e criação de GitHub Release.
- Atualiza README bilíngue com inglês primeiro e português em seguida.
- Mantém dependências opcionais de pontuação fora do bootstrap automático.
- Corrige dependências de build para usar `PySide6`/`PySide6-Addons` em vez de um pacote inexistente `PySide6-WebEngine`.
- Remove a API Python `vina` dos requirements de build, usando o fallback CLI incluído para evitar compilação com Boost nos runners.
- Usa `macos-15-intel` para o build macOS x64 no GitHub Actions.

## 0.0.1 - 2026-05-16

- Primeira versão pública como VinaLab.
- Corrige o pacote Windows para abrir o aplicativo compilado diretamente, sem bootstrap de `.venv` no primeiro uso.
- O instalador Windows agora inclui `Instalar_VinaLab.bat` e remove runtimes legados da pasta instalada.
- Interface desktop para AutoDock Vina com fluxo de conversão, configuração, docking, resultados, visualização 3D e relatórios.
- Conversão de ligantes PDB/MOL2 para PDBQT com validação de geometria via RDKit e fallback Meeko.
- Visualização 3D de receptor e pose de ligante em Py3Dmol/3Dmol.js.
- Tabelas de resultados, interações, clusters e consenso com tooltips em pt-BR.
- Layout responsivo validado para 1280x720, 1920x1080 e 2560x1440.
- Auditoria inicial de strings visíveis em pt-BR.
