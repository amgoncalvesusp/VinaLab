# VinaLab 0.0.3

## English

### New Features

- **Prepare Protein tab**: load PDB, strip HETATM ligands (with keep-residues list), select chain, add hydrogens via Open Babel at neutral pH.
- **Consensus plot sub-tab** in Results: scatter/3D plot of multi-scoring results with mplcursors tooltips; X/Y/Z axis selectors for any scoring column.
- **Blind docking box** button: computes box from radius of gyration of receptor heavy atoms (2·Rg + 2 Å cube).
- **MOL2 receptor support**: Converter tab now accepts `.mol2` receptor files (OBabel MOL2→PDB→PDBQT pipeline).
- **Expanded ligand file filter**: Converter input accepts `.pdbqt`, `.mol2`, `.sdf`, `.mol`, `.pdb`.
- **PDBQT charge validation and repair**: pre-flight check before Vina run; three-tier repair chain (RDKit Gasteiger → OBabel --partialcharge → 0.000 fallback).
- **Fully-rigid receptor checkbox**: hides flex sidechains field when checked.
- **Load box preset via file dialog**: replaces dropdown with a Browse button.
- **Interactive architecture HTML**: `architecture.html` — single-file interactive architecture and usage guide with Mermaid pipeline diagrams.

### Improvements

- Scrollbars set to `AsNeeded` on all panels.
- Workflow step groups numbered 1–7 in setup panel.
- Tab order: Converter → Prepare Protein → Docking → Report.
- "Modo Lote" renamed to "Modo Triagem" throughout.
- Box auto-size uses max extent of all ligands + 1 Å (cube).
- Atom tree table: min height 240 px, vertical scrollbar always visible.
- Max poses raised to 20.
- Tooltips added for blind docking, flex sidechains, triagem mode.
- Added `mplcursors>=0.5` to requirements.

### Release Assets

- `VinaLab-0.0.3-windows-x64-portable.zip`
- `SHA256SUMS-*.txt`

---

## Português

### Novas funcionalidades

- **Aba Preparar Proteína**: carrega PDB, remove HETATM (com lista de resíduos a manter), seleciona cadeia, adiciona hidrogênios via Open Babel em pH neutro.
- **Sub-aba Gráfico de Consenso** em Resultados: dispersão/3D de pontuações múltiplas com tooltips via mplcursors; seletores de eixo X/Y/Z.
- **Botão Docking Cego**: calcula caixa a partir do raio de giração dos átomos pesados do receptor (2·Rg + 2 Å cúbico).
- **Suporte a receptor MOL2**: Aba Converter aceita `.mol2` para receptor.
- **Filtro de arquivo de ligante ampliado**: entrada aceita `.pdbqt`, `.mol2`, `.sdf`, `.mol`, `.pdb`.
- **Validação e reparo de cargas PDBQT**: verificação pré-docking; cadeia de reparo em três níveis.
- **Checkbox receptor totalmente rígido**: oculta campo de cadeias laterais flexíveis quando marcado.
- **Carregar predefinição via diálogo de arquivo**: substitui dropdown por botão Procurar.
- **HTML de arquitetura interativo**: guia de arquitetura e uso com diagramas Mermaid.

### Melhorias

- Barras de rolagem configuradas como `AsNeeded` em todos os painéis.
- Grupos de etapas numerados de 1 a 7.
- Ordem das abas: Converter → Preparar Proteína → Docking → Relatório.
- "Modo Lote" renomeado para "Modo Triagem".
- Auto-tamanho da caixa usa extensão máxima de todos os ligantes + 1 Å.
- Tabela de átomos: altura mínima 240 px, barra de rolagem vertical sempre visível.
- Máximo de poses elevado para 20.
- Tooltips para docking cego, cadeias laterais flexíveis e modo triagem.
- Adicionado `mplcursors>=0.5` aos requisitos.

### Artefatos do Release

- `VinaLab-0.0.3-windows-x64-portable.zip`
- `SHA256SUMS-*.txt`
