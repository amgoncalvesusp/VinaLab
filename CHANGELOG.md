# Changelog

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
