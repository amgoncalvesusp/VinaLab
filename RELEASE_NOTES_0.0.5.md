# VinaLab 0.0.5

## English

### Highlights

- MOL2 and SDF ligands now convert to PDBQT (SDF format is detected and an Open
  Babel fallback handles MOL2/SDF that RDKit/Meeko cannot parse).
- Horizontal and vertical scrollbars on the option panels and the left workspace,
  so every option and the Run button are reachable in narrow windows.
- Maximum number of poses raised from 20 to 100.
- Pre-run checklist now appears above the Run button.
- "Fit box to ligand" now also centers the box on the ligand, removing the false
  "atoms outside the search box" warning.
- Affinity distribution and cluster charts are now interactive (Plotly): hover a
  point to see the molecule name; both charts get more space.
- "Open in PyMOL" now finds PyMOL across PATH and common Windows installs
  (Schrodinger PyMOL included) and opens the selected pose.
- MDAnalysis is bundled, so receptor-ligand interactions are computed again.
- Closing the window asks for confirmation (Yes/No).
- Scoring-function star ratings removed from the selector.
- GNINA (CNN) scoring is bundled for Windows.
- AutoDock4 (ad4) now reports a clear message: it requires AutoGrid4 affinity
  maps, which are not bundled — use Vina, Vinardo or GNINA.

### Release Assets

- `VinaLab-0.0.5-windows-x64-portable.zip`
- `VinaLab-0.0.5-windows-x64-installer.zip`
- `SHA256SUMS-windows.txt`

---

## Portugues

### Destaques

- Ligantes MOL2 e SDF agora convertem para PDBQT (o formato SDF e detectado e um
  fallback com Open Babel trata MOL2/SDF que o RDKit/Meeko nao conseguem ler).
- Barras de rolagem horizontal e vertical nos paineis de opcoes e na area lateral
  esquerda, para alcancar todas as opcoes e o botao Executar em janelas estreitas.
- Numero maximo de poses aumentado de 20 para 100.
- Checklist de pre-execucao agora aparece acima do botao Executar.
- "Ajustar caixa ao ligante" agora tambem centraliza a caixa no ligante, removendo
  o aviso falso de "atomos fora da caixa de busca".
- Graficos de distribuicao de afinidade e de clusters agora sao interativos
  (Plotly): passe o mouse em um ponto para ver o nome da molecula; ambos com mais
  espaco.
- "Abrir no PyMOL" agora encontra o PyMOL no PATH e em instalacoes comuns do
  Windows (incluindo Schrodinger PyMOL) e abre a pose selecionada.
- MDAnalysis incluido, entao as interacoes receptor-ligante voltam a ser
  calculadas.
- Fechar a janela pede confirmacao (Sim/Nao).
- Estrelas das funcoes de pontuacao removidas do seletor.
- Pontuacao GNINA (CNN) incluida para Windows.
- AutoDock4 (ad4) agora mostra mensagem clara: exige mapas de afinidade do
  AutoGrid4, que nao estao incluidos — use Vina, Vinardo ou GNINA.

### Artefatos do Release

- `VinaLab-0.0.5-windows-x64-portable.zip`
- `VinaLab-0.0.5-windows-x64-installer.zip`
- `SHA256SUMS-windows.txt`
