# VinaLab 2.0 — Plano de Implementação Completo

> Documento de especificação para outra IA (ou equipe) implementar o VinaLab 2.0 do zero,
> reaproveitando a base gráfica e as funções já existentes do VinaLab 1.x.
>
> **Data:** 2026-07-09
> **Origem:** `vinagui/` (VinaLab 1.x, PySide6) — repositório de referência.
> **Destino:** `VinaLab_2.0/` (novo projeto).
> **Objetivos inegociáveis:**
> 1. Rodar de forma confiável em **Windows 10/11** e **Ubuntu Linux** (20.04+); **macOS como alvo secundário**.
> 2. **Funções de pontuação que funcionem nos dois SOs**, com paridade de resultado.
> 3. **Suporte a átomos exóticos — Boro (B) em primeiro lugar**, mas também Se, Si, As, e metais — que o AutoDock Vina não tipa.
>
> **Decisões confirmadas pelo usuário (2026-07-09):**
> - ✅ **conda-forge** é a base de toolchain (resolve o problema de portabilidade do Linux).
> - ✅ **QM semiempírica (xtb) priorizada como via primária de Boro** — validada por literatura como
>   função de pontuação legítima e de ponta *quando computada com solvatação + correções* (não em
>   fase gasosa). Ver §4.4 para a evidência (SQM2.20, Nature Commun. 2024) e o desenho correto.
> - ✅ **macOS mantido como alvo secundário** (best-effort; CI e empacotamento incluídos, sem bloquear releases).

---

## 0. Como ler este documento

| Seção | Para quê |
|---|---|
| 1 | Diagnóstico do 1.x: o que quebrou e o que reaproveitar. |
| 2 | Princípios e decisões de arquitetura do 2.0. |
| 3 | Arquitetura de software em camadas + diagrama. |
| 4 | **Subsistema de pontuação (o coração do pedido)** — arquitetura de plugins e a via Boro. |
| 5 | Pipeline de preparação com suporte a elementos exóticos. |
| 6 | Estratégia cross-platform (Windows + Ubuntu). |
| 7 | Modelo de dados e persistência. |
| 8 | Camada de UI (reaproveitamento da base gráfica). |
| 9 | Migração 1.x → 2.0. |
| 10 | Testes e validação científica. |
| 11 | Roadmap por fases com critérios de aceite. |
| 12 | Riscos e decisões em aberto. |
| 13 | Estrutura de diretórios proposta. |
| 14 | Apêndices: contratos de código, parâmetros de Boro, referências. |

---

## 1. Diagnóstico do VinaLab 1.x

### 1.1. O que REAPROVEITAR (a base gráfica e as funções que já funcionam)

O VinaLab 1.x é uma aplicação **PySide6 (Qt6)** madura. A camada gráfica e vários módulos de
domínio são sólidos e devem ser portados quase intactos:

| Componente 1.x | Arquivo | Papel | Reaproveitamento |
|---|---|---|---|
| Janela principal + abas | `mainwindow.py` | `QMainWindow` com `QTabWidget` (Converter, Prepare Protein, Docking, Report) + `QSplitter` horizontal com Results à direita | **Portar** — layout e fluxo de sinais são bons. |
| Entry point | `main.py` | Bootstrap Qt, `resource_path()`, workaround QtWebEngine no Linux congelado | **Portar** com ajustes (ver §6). |
| Engine de docking | `core/docking_engine.py` | `DockingWorker(QThread)`: Vina/Vinardo/AD4/GNINA/SMINA + rescoring externo | **Refatorar** para arquitetura de plugins (§4). Lógica de parsing de PDBQT, validação de grid, sanitização — reaproveitar. |
| Conversor | `core/converter.py` | `FileConverter`: RDKit+Meeko → PDBQT, fallback Open Babel | **Estender** para elementos exóticos (§5). |
| Utilidades de arquivo | `core/file_utils.py` | Sanitização PDBQT, normalização de tipos AutoDock, reparo de cargas | **Estender** — é aqui que o Boro é bloqueado hoje (`VALID_AUTODOCK_TYPES`). |
| Descoberta de binários | `core/native_tools.py` | Acha vina/gnina/smina/obabel no PATH e em `tools/`; monta env com DLLs | **Portar e generalizar** (§6) — adicionar xtb, autogrid4. |
| Gerenciador de ambiente | `core/environment_manager.py` | venv, checagem/instalação de deps, status report | **Portar** — trocar por gestão baseada em conda opcional (§6). |
| i18n | `core/i18n.py` | PT/EN, `I18n.get(key, lang)` | **Portar a infraestrutura**, mas entregar somente catálogo `en_US` no 2.0. |
| Responsividade / scrolling | `core/responsive.py`, `core/scrolling.py` | Perfis de tela, `WheelGuard` | **Portar** direto. |
| RMSD / clustering | `core/rmsd.py`, `tabs/results_clustering.py` | Clustering de poses por RMSD | **Portar** direto. |
| Resultados | `tabs/results_tab.py` (2009 linhas), `results_view.py`, `results_plotly.py`, `results_dialogs.py` | Tabela, filtros, Plotly, viewer 3D (py3Dmol), export CSV/Excel, consenso | **Portar** — é o maior ativo de UI. Adaptar o schema de colunas ao novo modelo de dados (§7). |
| Relatório | `tabs/report_tab.py` | PDF via reportlab | **Portar**. |
| Preparo de proteína | `tabs/prepare_protein_tab.py` | ProDy/gemmi limpeza de receptor | **Portar**. |
| Setup / caixa de busca | `tabs/setup_tab.py` | Seleção receptor/ligante, definição de grid | **Portar**. |
| Estilo | `ui/style.qss`, `ui/splash.py`, `ui/about_dialog.py`, `ui/help_panel.py`, `ui/welcome_dialog.py` | Tema e diálogos | **Portar** direto. |

### 1.2. O que está QUEBRADO ou frágil (o que o 2.0 precisa corrigir)

1. **Fork bagunçado.** O repositório 1.x tem arquivos duplicados `-Notebook_AMG` (ex.:
   `docking_tab-Notebook_AMG.py`, `converter-Notebook_AMG-2.py`, `i18n-Notebook_AMG.py`).
   São variantes de uma mesclagem mal resolvida entre duas máquinas. → **O 2.0 começa limpo,
   sem esses duplicados.**

2. **Cross-platform Linux frágil.** Os 5 commits mais recentes são todos sobre caminhos do
   **Open Babel no Linux** (`fix: locate installed Open Babel package roots`, `fix: override
   stale Open Babel runtime paths`, etc.). A descoberta de plugins/DLL/SO do Open Babel entre
   Windows e Linux é o ponto de dor recorrente. → **O 2.0 padroniza toolchain via conda-forge
   (§6) para eliminar essa classe de bug.**

3. **AD4 bloqueado.** A interface oferece AutoDock4 (`--scoring ad4`) mas o código levanta erro:
   não gera mapas AutoGrid4. → **O 2.0 implementa geração de GPF + `autogrid4`, ou remove AD4
   da UI até implementá-lo.**

4. **GNINA só no Linux.** Não há binário GNINA para Windows; a UI avisa e desabilita.
   → **Aceitável, mas o 2.0 não pode depender de GNINA para a via principal de Boro.**

5. **Rescoring pesado e frágil.** RTMScore e DeltaVinaXGB dependem de `torch`/`dgl`/`torch-scatter`,
   instalados como zips em `pontuacao/` extraídos em runtime e chamados por subprocess com
   `PYTHONPATH` remendado. DeltaVinaRF20 está bloqueado (Python 2/R). → **O 2.0 troca "zip +
   subprocess" por plugins isolados com ambiente próprio e cache (§4).**

6. **Boro (e afins) impossível.** `core/file_utils.py::VALID_AUTODOCK_TYPES` **não inclui `B`**.
   O AutoDock Vina/Vinardo/AD4 não tem parâmetros para boro; a sanitização normaliza ou remove o
   átomo, e o Meeko não sabe tipá-lo. Resultado: ligantes com boro (ex.: bortezomibe, tavaborol,
   ácidos borônicos) **não podem ser preparados nem pontuados** hoje. → **É o requisito central
   do 2.0; ver §4.4 e §5.**

### 1.3. Limitação científica do núcleo AutoDock (a razão do requisito de Boro)

O AutoDock Vina, Vinardo e AD4 usam a tipagem atômica AutoDock, que cobre apenas:
`C, A(C aromático), N, NA, NS, OA, OS, S, SA, P, F, Cl, Br, I, H, HD, HS` e um conjunto pequeno
de metais (`Mg, Mn, Zn, Ca, Fe, Cu`). **Não existe parâmetro de van der Waals/desolvatação para
Boro, Silício, Selênio, Arsênio** e a maioria dos metais de transição. Qualquer software que
dependa só do force field AutoDock **nunca** pontuará boro corretamente. A solução exige uma via
de pontuação **independente da tipagem AutoDock** — física (semiempírica/MM) ou ML com
featurização agnóstica ao elemento. Isso guia toda a §4.

---

## 2. Princípios e decisões de arquitetura do 2.0

| # | Princípio | Consequência prática |
|---|---|---|
| P1 | **Núcleo desacoplado da UI.** | Toda a lógica de docking/scoring/preparo vive numa biblioteca `vinalab_core` sem importar PySide6. A UI (`vinalab_ui`) consome o núcleo via interfaces. Permite testes headless e uso por CLI/notebook. |
| P2 | **Pontuação como sistema de plugins.** | Cada função de pontuação implementa um contrato único `ScoringPlugin` (§4.1). Adicionar Lin_F9, OnionNet, xtb etc. é registrar um plugin, sem tocar no engine. |
| P3 | **Paridade cross-platform por design.** | Toolchain unificada via **conda-forge** (vina, openbabel, xtb, gnina, smina, autodock-vina, autogrid). Descoberta de binário abstrai SO. Nada de caminhos hard-coded de DLL. |
| P4 | **Via de elementos exóticos (Boro) de primeira classe.** | Um caminho de preparo+pontuação que **não passa pela tipagem AutoDock**: RDKit para química + xtb/OpenMM/UFF para energia. Detectado automaticamente quando o ligante contém B/Si/Se/As. |
| P5 | **Reprodutibilidade.** | Todo run persiste em SQLite: parâmetros, versões de ferramentas, hashes de arquivo, comandos. Relatório técnico auditável. |
| P6 | **Degradação graciosa.** | Se um scorer/binário falta, o run continua com os disponíveis e registra `scoring_error` por pose (comportamento já presente no 1.x — manter). |
| P7 | **Reuso agressivo da UI 1.x.** | Não reescrever `results_tab`, `report_tab`, `converter_widget`. Adaptá-los ao novo modelo de dados. |
| P8 | **Uma única fonte de verdade para a caixa de busca.** | `SearchBox` é imutável e contém centro, tamanho, frame de coordenadas, margem e origem. Preview, validação, cache e comando do motor consomem exatamente a mesma instância. |
| P9 | **Busca de pose ≠ rescoring.** | O plano de execução declara separadamente o motor que gera poses e os scorers que as avaliam. Um scorer capaz de Boro não é presumido como motor de docking. |
| P10 | **Recursos computacionais explícitos.** | Um `ResourceManager` aplica orçamento global de CPU, GPUs e concorrência a todos os plugins; nenhum subprocess pode monopolizar a máquina. |
| P11 | **Produto em inglês, pronto para localização futura.** | UI, CLI, relatórios, logs e documentação distribuída são `en_US`. Manter chaves i18n, mas não manter PT/EN em paralelo no 2.0. |

### 2.1. Stack tecnológica alvo

- **Linguagem:** Python 3.11 (piso 3.10, teto 3.12 enquanto torch/dgl não suportarem 3.13).
- **UI:** PySide6 6.7.x (Qt6). Reuso direto; toda interface, CLI, relatório e mensagem distribuída em inglês (`en_US`).
- **Química:** RDKit, Meeko (ligantes padrão), ProDy + gemmi (receptor), Open Babel (fallback).
- **Docking:** AutoDock Vina 1.2.7 (Python API + CLI fallback), Smina, GNINA (Linux), AutoGrid4/AutoDock4. GPU é opcional por plugin: Vina-GPU e AutoDock-GPU passam por validação própria antes de serem distribuídos.
- **Pontuação exótica/Boro (via física-QM, agnóstica ao force field AutoDock):**
  - Primária: **xtb (GFN2-xTB / GFN-FF) com solvatação implícita ALPB/GBSA** — Z≤86, inclui Boro.
  - Alta acurácia: **SQM2.20-style — PM6-D3H4X/COSMO2 via MOPAC (open source) + Cuby** — 83 elementos incl. Boro.
  - Complementar (orgânicos padrão): **OpenMM + OpenFF/GAFF2** (MM-GBSA).
  - Fallback barato: **RDKit UFF**, apenas quando sua parametrização validar o complexo; nunca prometer cobertura para todo caso químico.
- **Dados:** SQLite (via `sqlite3`/`sqlalchemy` leve) + export Parquet (pandas/pyarrow).
- **Empacotamento:** conda-forge como fonte de binários; PyInstaller para bundle final;
   Inno Setup (Windows), AppImage/.desktop (Linux) e `.app`/`.dmg` (macOS, secundário).
- **Reprodutibilidade de dependências:** `environment.yml` + lockfiles por plataforma gerados com `conda-lock`, contendo versões e hashes resolvidos.

---

## 3. Arquitetura de software

```
┌──────────────────────────────────────────────────────────────────────┐
│                          vinalab_ui  (PySide6)                         │
│  MainWindow · Converter · PrepareProtein · Setup · Docking · Results   │
│  · Report · ScoringSelector · ValidationPanel                          │
│  (só chama vinalab_core através de serviços; nenhuma regra de negócio) │
└───────────────┬────────────────────────────────────────────┬─────────┘
                │ Qt Signals / Workers (QThread)              │
┌───────────────▼────────────────────────────────────────────▼─────────┐
│                        vinalab_core  (sem Qt)                          │
│                                                                        │
│  prepare/          docking/            scoring/         analysis/      │
│  ├ ligand_prep     ├ engine_registry   ├ registry       ├ rmsd/cluster │
│  ├ receptor_prep   ├ vina_engine       ├ base (contrato)├ consensus    │
│  ├ element_router  ├ smina_engine      ├ vina_scorer    ├ enrichment   │
│  │  (Boro!)        ├ gnina_engine      ├ vinardo_scorer ├ ifp          │
│  └ pdbqt_utils     ├ ad4_engine        ├ ad4_scorer     └ casf_validate│
│                    └ pose_model        ├ xtb_scorer   ◄── Boro         │
│  io/               tools/              ├ openmm_scorer ◄── Boro        │
│  ├ project_db      ├ tool_locator      ├ uff_scorer    ◄── Boro        │
│  ├ parquet_export  ├ conda_env         ├ linf9_scorer                  │
│  └ report_data     ├ resource_manager  ├ onionnet_scorer               │
│                    └ platform          ├ pose_search_plan              │
│                                        ├ rtmscore_scorer               │
│                                        └ deltaxgb_scorer               │
└────────────────────────────────────────────────────────────────────────┘
                │
┌───────────────▼────────────────────────────────────────────────────────┐
│  vinalab_cli  (headless): mesmo núcleo via linha de comando / batch      │
└──────────────────────────────────────────────────────────────────────────┘
```

**Regra de ouro:** `vinalab_core` **nunca importa PySide6**. A UI passa callbacks de progresso
(`Callable[[Progress], None]`) e o núcleo os chama. Os `QThread` workers ficam em `vinalab_ui`,
finos, delegando ao núcleo.

### 3.1. Contratos obrigatórios de geometria, busca e recursos

#### `SearchBox`: coordenadas impossíveis de divergir

```python
@dataclass(frozen=True)
class SearchBox:
    center: tuple[float, float, float]       # Angstrom, frame do receptor preparado
    size: tuple[float, float, float]         # Angstrom; cada componente > 0
    coordinate_frame: str                    # hash/id do receptor preparado
    margin: float                            # usado apenas no auto-fit; persistido
    source: Literal["user", "reference_ligand", "binding_site", "imported"]

    @property
    def minimum(self) -> tuple[float, float, float]: ...  # center - size / 2
    @property
    def maximum(self) -> tuple[float, float, float]: ...  # center + size / 2
    def contains_all(self, coordinates, tolerance=0.01) -> ValidationResult: ...
```

- A UI altera a caixa somente chamando `SearchBoxService.replace_center()` ou `fit_to_atoms()`; é proibido editar campos Qt e montar um comando separado depois.
- `fit_to_atoms(reference_ligand, margin=4.0)` usa o ponto médio da **bounding box** do ligante e `size = span + 2*margin`. Não usar o centróide, pois um ligante alongado pode ficar parcialmente fora.
- Quando o usuário informar `center_x/y/z`, o novo centro é aplicado exatamente como informado e a preview 3D, `SearchBox`, configuração do motor e chave de cache são atualizados na mesma transação. A mudança invalida mapas/grid existentes.
- O frame é sempre o do receptor **preparado**. Transformações de viewer, câmera e Py3Dmol nunca entram no cálculo. Se o preparo alterar coordenadas, guardar a matriz de transformação e reaplicar/invalidar a caixa de forma explícita.
- Antes de executar, validar tamanho positivo, limites do motor, frame compatível e o ligante de referência dentro de `minimum..maximum`. A mensagem mostra átomo, coordenada e limite que falhou.

#### Plano de execução separado

```python
@dataclass(frozen=True)
class PoseSearchPlan:
    engine_key: str                 # ex.: vina, ad4_gpu, vina_gpu, covalent_ad4
    search_box: SearchBox
    chemical_state_id: str          # tautômero, protonação, carga e multiplicidade
    covalent_mode: CovalentSpec | None
    resource_request: ResourceRequest
    experimental: bool = False

@dataclass(frozen=True)
class ResourceRequest:
    cpu_threads: int
    gpu_device_ids: tuple[int, ...] = ()
    max_parallel_jobs: int = 1
```

Um `PoseSearchPlan` sempre existe antes de `ScoringPlan`. Para Boro, o router deve indicar que
xtb/PM6/UFF são **rescoring** e exigir um motor de busca compatível; não pode simplesmente ocultar
Vina e prosseguir sem poses. Casos borônicos covalentes exigem `CovalentSpec` (resíduo nucleofílico,
estado pré/pós-reação e restrições de ligação/ângulo) confirmado pelo usuário.

#### ResourceManager

- Preferência do projeto: `cpu_budget`, `leave_one_core_free=True`, `max_parallel_jobs`, GPUs habilitadas e IDs das GPUs.
- Atribuir `--cpu` ao Vina, `OMP_NUM_THREADS`/`OPENBLAS_NUM_THREADS`/`MKL_NUM_THREADS` ao subprocess e `OPENMM_CPU_THREADS`/propriedades de plataforma ao OpenMM.
- Garantir `sum(cpu_threads de jobs ativos) <= cpu_budget`; uma GPU só recebe uma tarefa pesada por vez, salvo suporte explícito do plugin.
- Exibir na UI o motor, CPU, GPU e estimativa de fila antes de iniciar. Cancelamento deve matar a árvore de processos e liberar o recurso.

---

## 4. Subsistema de pontuação (o coração do pedido)

Esta é a parte mais importante. Duas exigências combinadas:
**(a) funcionar igual em Windows e Ubuntu** e **(b) suportar Boro e outros átomos exóticos.**

### 4.1. Contrato único `ScoringPlugin`

Todo scorer implementa esta interface. O engine nunca conhece detalhes de um scorer específico.

```python
# vinalab_core/scoring/base.py
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Protocol, Sequence

@dataclass(frozen=True)
class PoseInput:
    """Uma pose a pontuar (independente de quem a gerou)."""
    pose_id: str                 # id estável: hash(receptor)+ligand+mode
    receptor_pdbqt: Path
    receptor_pdb: Path           # versão PDB (para scorers que não usam PDBQT)
    ligand_pdbqt: Path           # pose isolada (1 MODEL)
    ligand_sdf: Path             # mesma pose em SDF (RDKit-safe; preserva ordem de ligação)
    mode: int
    elements: frozenset[str]     # {"C","N","O","B",...} — usado para roteamento
    box_center: tuple[float, float, float]
    box_size: tuple[float, float, float]
    meta: dict = field(default_factory=dict)

@dataclass(frozen=True)
class ScoreResult:
    pose_id: str
    score: float | None          # menor = melhor (convenção; documentar unidade)
    unit: str                    # "kcal/mol", "pK", "arb", "Eh", ...
    scorer_key: str
    scorer_version: str
    ok: bool
    error: str = ""
    extra: dict = field(default_factory=dict)   # ex.: CNNaffinity, componentes de energia

@dataclass(frozen=True)
class ScorerCapabilities:
    supports_elements: frozenset[str] | None   # None = todos os elementos
    is_element_agnostic: bool                  # True p/ xtb, UFF, OpenMM
    requires_binary: str | None                # "xtb", "gnina", "smina", "autogrid4", None
    requires_python_env: str | None            # nome do env conda isolado, se houver
    platforms: frozenset[str]                  # {"win32","linux"}
    kind: Literal["rescore"]                  # busca pertence a DockingEngine, não a scorer
    cost: str                                  # "low" | "medium" | "high"

class ScoringPlugin(Protocol):
    key: str          # "vina", "vinardo", "xtb_gfn2", "openmm_mmgbsa", ...
    label: str        # "Vina", "xtb GFN2 (Boro-capaz)", ...

    def capabilities(self) -> ScorerCapabilities: ...
    def is_available(self) -> tuple[bool, str]:
        """(disponível, motivo_se_indisponível). Checa binário/env no SO atual."""
    def can_score(self, pose: PoseInput) -> tuple[bool, str]:
        """Rejeita, ex., poses com Boro em scorers AutoDock; explica o porquê."""
    def score(self, poses: Sequence[PoseInput],
              progress: "ProgressCb | None" = None) -> list[ScoreResult]:
        """Pontua um lote de poses do MESMO complexo. Deve ser determinístico
        (mesma seed → mesmo score) e cache-friendly."""
```

O **registry** (`scoring/registry.py`) descobre plugins, filtra por SO/disponibilidade/elemento e
entrega ao engine. A UI (`ScoringSelector`, portada do 1.x) lista apenas o que `is_available()` e
`can_score()` permitem, com tooltip explicando indisponibilidades — **exatamente o padrão que o
`ScoringFunctionSelector` do 1.x já faz** (`tabs/docking_tab.py`), agora generalizado.

### 4.2. Roteamento automático por elemento (o "cérebro" do Boro)

```python
# vinalab_core/scoring/router.py
EXOTIC_ELEMENTS = {"B", "Si", "Se", "As", "Te", "Ge"}
# metais também caem aqui p/ scoring quantitativo confiável

def choose_scorers(pose: PoseInput, requested: list[str],
                   registry: ScoringRegistry) -> ScoringPlan:
    exotic = pose.elements & (EXOTIC_ELEMENTS | METALS)
    if not exotic:
        return registry.resolve(requested)           # caminho normal
    # Ligante exótico: filtra SOMENTE scorers incompatíveis e injeta rescoring agnóstico.
    # A escolha do motor que GEROU a pose já ocorreu no PoseSearchPlan (§3.1).
    plan = registry.resolve(requested, drop_incompatible=True)
    if not plan.has_element_agnostic():
        plan.add_default_exotic_scorers()             # xtb → pm6 → OpenMM (se parametrizar) → UFF
    plan.add_warning(
        f"Ligante contém {sorted(exotic)}. O rescoring será físico-QM "
        f"(xtb GFN2 com solvatação; SQM2.20 quando disponível). Verifique o "
        f"motor de busca experimental/covalente indicado no plano de execução."
    )
    return plan
```

**Comportamento visível ao usuário:** ao carregar um ligante com Boro, a UI mostra um aviso,
seleciona os scorers Boro-capazes e abre a seção **Pose generation**. Ela nunca inicia um run se
não houver motor de busca compatível selecionado; explica se o motor é experimental e oferece o
modo covalente quando o usuário declarar um ligante reativo.

#### 4.2.1. Geração de poses para elementos exóticos

1. **Ligante padrão:** Vina/Vinardo/Smina/GNINA podem gerar poses, respeitando `SearchBox`.
2. **Ligante exótico não covalente:** executar uma prova de compatibilidade com AutoDock4/AutoDock-GPU
   usando mapas e parâmetros explicitamente validados para o elemento. Este motor deve ser marcado
   `experimental` até passar os benchmarks de §10; nunca converter silenciosamente B para C.
3. **Ligante borônico potencialmente covalente:** exigir um `CovalentSpec` confirmado (resíduo,
   átomo alvo, estado pré/pós-reação e restrições) e usar plugin de docking covalente. Se não houver
   plugin disponível, bloquear a execução e orientar que só o rescoring de uma pose fornecida é possível.
4. **Fallback proibido:** xTB, PM6, OpenMM e UFF recebem poses; eles não são substitutos de busca
   conformacional. O sistema não pode declarar um resultado de docking apenas porque obteve um score.

### 4.3. Catálogo de funções de pontuação do 2.0

Ordenado por prioridade. Colunas: elementos, SOs, tipo, custo, o que reaproveitar do 1.x.

Colunas SO: ✅ suportado · ⚠️ com ressalva. macOS (secundário) segue a coluna Linux, **exceto
GNINA** (mais maduro no Linux). O que roda por conda-forge (vina, vinardo, smina, xtb, openbabel,
mopac, openmm) tem build para os três SOs.

| Key | Label | Elementos | Win | Linux | Tipo | Boro? | Origem |
|---|---|---|---|---|---|---|---|
| `vina` | AutoDock Vina | AutoDock set | ✅ | ✅ | search+rescore | ❌ | 1.x, portar |
| `vinardo` | Vinardo | AutoDock set | ✅ | ✅ | search+rescore | ❌ | 1.x, portar |
| `ad4` | AutoDock4 | AutoDock + metais | ✅ | ✅ | search+rescore | ⚠️ via param custom | 1.x, **destravar** (§4.6) |
| `smina` | Smina | AutoDock set | ✅ | ✅ | search+rescore | ❌ | 1.x, portar |
| `gnina` | GNINA CNN | AutoDock set | ❌ | ✅ | search+rescore | ❌ | 1.x, portar |
| `vina_gpu` | Vina-GPU | AutoDock set | ⚠️ | ✅ | search | ❌ | opcional; benchmark CPU/GPU próprio |
| `ad4_gpu` | AutoDock-GPU | AD4 + mapas | ⚠️ | ✅ | search | ⚠️ via parâmetros validados | opcional; POC para Boro |
| **`xtb_gfn2`** | **xtb GFN2-xTB + ALPB(água)** | **todos (Z≤86)** | ✅ | ✅ | **rescore** | **✅** | **NOVO — via Boro primária** |
| **`xtb_gfnff`** | **xtb GFN-FF + ALPB** | **todos** | ✅ | ✅ | rescore | **✅** | **NOVO — via Boro rápida** |
| **`pm6_sqm`** | **SQM2.20 (PM6-D3H4X/COSMO2, MOPAC)** | **83 elem. incl. B** | ✅ | ✅ | rescore | **✅** | **NOVO — Boro alta acurácia** |
| **`openmm_mmgbsa`** | **OpenMM MM-GBSA** | GAFF2/OpenFF | ✅ | ✅ | rescore | ⚠️ parcial | NOVO |
| **`uff_ie`** | **RDKit UFF (energia de interação)** | casos parametrizáveis por UFF | ✅ | ✅ | rescore | ⚠️ | NOVO — fallback barato, com validação |
| `linf9` | Lin_F9 (Smina fork) | AutoDock + termo metal | ✅ | ✅ | rescore | ❌ | NOVO |
| `onionnet_sfct` | OnionNet-SFCT | agnóstico (contatos) | ✅ | ✅ | rescore | ⚠️ OOD | NOVO |
| `rtmscore` | RTMScore | agnóstico (grafo) | ⚠️ | ✅ | rescore | ⚠️ OOD | 1.x, isolar env |
| `deltaxgb` | DeltaVinaXGB-Light | AutoDock + features | ✅ | ✅ | rescore | ❌ | 1.x, isolar env |

Legenda Boro: ✅ suportado · ⚠️ possível com ressalva (parâmetros parciais ou extrapolação
fora do domínio de treino, "OOD") · ❌ impossível pelo force field.

**Posicionamento (importante para não usar a ferramenta errada):**
- **Triagem de alto volume, orgânicos padrão** → empíricos/ML: `vinardo`, `gnina`, `linf9`,
  `rtmscore`. Rápidos e competitivos em benchmark (CASF).
- **Qualquer átomo exótico (Boro etc.)** → motor de pose explicitamente validado + via física-QM:
  `xtb_gfn2`/`xtb_gfnff` como rescoring inicial, `pm6_sqm` como protocolo acurado e `uff_ie`
  somente se parametrizar com êxito.
- **Rescoring acurado dos top-N hits** (qualquer elemento) → `pm6_sqm` ou `xtb_gfn2` — a
  literatura mostra que um protocolo QM semiempírico completo pode superar FF e ML em afinidade (§4.4).

### 4.4. A via Boro em detalhe (elementos exóticos)

**Por que QM semiempírica é a via certa — e é uma boa função de pontuação (não um remendo).**
A família física-QM foi validada na literatura como estado da arte em afinidade: o **SQM2.20**
([Pecina et al., *Nature Communications* 2024](https://www.nature.com/articles/s41467-024-45431-8),
[PMC10847445](https://pmc.ncbi.nlm.nih.gov/articles/PMC10847445/)) é uma função de pontuação
semiempírica (PM6-D3H4X/COSMO2) que alcança **qualidade de DFT em minutos**, com **R² médio ≈ 0,69**
contra dados experimentais, **superando funções de force field e de ML** em múltiplos alvos (BACE1
etc.). A mesma classe cobre a tabela periódica quase inteira — **inclui Boro** (xtb: Z≤86; PM6: 83
elementos H–Ba, Lu–Bi). Portanto a via QM resolve os dois requisitos de uma vez: **suporta Boro** e
**pode ser cientificamente competitiva quando o protocolo completo for validado**. `xtb_gfn2` não
deve ser anunciado como SQM2.20: é um rescoring inicial diferente, que requer benchmark próprio.

> ⚠️ **O detalhe que decide se é "boa" ou "ruim":** o score físico **não** é a energia de
> interação em fase gasosa. É preciso o esquema com termos físicos:
> `Score ≈ ΔE_int + ΔΔG_solv + ΔG_conf(L) + ΔG_H+ + (−TΔS)` — energia de interação **+ solvatação
> implícita** (ALPB/GBSA no xtb; COSMO2 no PM6) + conformação/entropia. ΔE em vácuo superliga
> interações polares/carregadas e é um mau preditor. **Todo scorer QM do 2.0 usa solvatação.**

Quatro níveis, por custo/acurácia. O router (§4.2) usa **xtb GFN2 (com solvatação) como padrão**,
sobe para **PM6/SQM2.20** para rescoring acurado, e usa UFF apenas após teste de parametrização.

#### Nível 1 — `xtb_gfn2` / `xtb_gfnff` com solvatação (PRIMÁRIA)

- **Ferramenta:** [`xtb`](https://github.com/grimme-lab/xtb) (Grimme). GFN2-xTB (tight-binding
  autoconsistente) e GFN-FF (força-campo). **Cobre Z=1–86, incluindo Boro nativamente.**
- **Cross-platform:** `conda install -c conda-forge xtb` — binário para Windows, Linux **e macOS**.
  Sem compilar. É a principal razão de padronizar conda (§6).
- **O que computa (com solvatação, obrigatório):**
  `ΔG_int = [E(complexo) + G_solv(complexo)] − [E(receptor) + G_solv(receptor)] − [E(lig) + G_solv(lig)]`,
  usando `--alpb water` (ou `--gbsa`). O padrão é single-point com geometria congelada; otimização
  só é permitida com restrições locais e é registrada como um protocolo distinto.
- **Estado químico obrigatório:** complexo, receptor e ligante usam carga/multiplicidade coerentes;
  antes do score enumerar tautômeros e estados de protonação no pH definido pelo projeto. Para Boro
  covalente, pontuar o estado químico que o usuário declarou, não um complexo não covalente implícito.
- **Truncamento do bolsão:** recorta resíduos num raio (ex.: 6 Å) ao redor do ligante, satura
  ligações cortadas com H (capping), mantém o bolsão fixo. ProDy/RDKit (já disponíveis).
- **Determinismo:** GFN é determinístico → cache por `hash(complexo_truncado)+método+solvente`.
- **Saída:** Hartree → kcal/mol (`×627.509`).
- **Custo:** GFN-FF ~segundos/pose; GFN2 ~dezenas de segundos/pose num bolsão pequeno.
  `cost="high"`; rodar em fila com cache.

Esqueleto:

```python
# vinalab_core/scoring/xtb_scorer.py
class XtbScorer:
    key = "xtb_gfn2"
    label = "xtb GFN2-xTB + ALPB água (suporta Boro)"

    def capabilities(self):
        return ScorerCapabilities(
            supports_elements=None, is_element_agnostic=True,
            requires_binary="xtb", requires_python_env=None,
            platforms=frozenset({"win32", "linux", "darwin"}),
            kind="rescore", cost="high")

    def score(self, poses, progress=None):
        results = []
        for p in poses:
            assert p.meta["chemical_state_id"] and p.meta["charge_model"]
            pocket = truncate_pocket(p.receptor_pdb, p.ligand_sdf, radius=6.0)  # ProDy
            # Cada single-point em solvente implícito (ALPB água) — NUNCA em vácuo:
            g_complex  = run_xtb(merge(pocket, p.ligand_sdf), method="gfn2",
                                 solvent="water", charge=total_charge)
            g_receptor = run_xtb(pocket, method="gfn2", solvent="water")
            g_ligand   = run_xtb(p.ligand_sdf, method="gfn2", solvent="water",
                                 charge=lig_charge)
            dE_solv = (g_complex - g_receptor - g_ligand) * 627.509 # energia relativa, não Kd
            results.append(ScoreResult(p.pose_id, dE_solv, "kcal/mol", self.key,
                                       xtb_version(), ok=True))
        return results
```

#### Nível 2 — `pm6_sqm` = SQM2.20 (ALTA ACURÁCIA, física de ponta)

- **Método:** PM6-D3H4X (dispersão D3 + correções de ligação de H/halogênio) com solvatação
  **COSMO2** e os termos de entropia/conformação/protonação do protocolo SQM2.20.
- **Ferramenta:** **MOPAC** (open source desde 2022, [openmopac.net](https://openmopac.net),
  conda-forge, Win/Linux/macOS) para o PM6; orquestração via **Cuby** (framework de Řezáč) ou um
  driver próprio replicando os termos. Estruturas de referência do benchmark em
  [github.com/Honza-R/PL-REX](https://github.com/Honza-R/PL-REX).
- **Boro:** PM6 parametriza 83 elementos (H–Ba, Lu–Bi) → **Boro incluído**.
- **Quando usar:** rescoring acurado dos top-N hits (qualquer elemento) e complexos exóticos onde
  se quer o melhor da física. `cost="high"` (minutos/complexo, ainda muito abaixo de DFT).
- **Evolução opcional:** **PM6-ML** ([Nováček & Řezáč, *JCTC* 2025](https://pubs.acs.org/doi/full/10.1021/acs.jctc.4c01330),
  [mopac-ml](https://github.com/Honza-R/mopac-ml)) adiciona correção ML ao PM6 e melhora ainda mais
  a acurácia — plugável no mesmo nível quando desejado.

#### Nível 3 — `openmm_mmgbsa` (física clássica, complementar a orgânicos padrão)

- **Ferramenta:** OpenMM + `openmmforcefields` (GAFF2 / OpenFF). conda-forge (Win/Linux/macOS);
  GPU opcional, roda em CPU.
- **Boro:** GAFF2 tem cobertura **parcial** (ácidos borônicos comuns podem faltar parâmetros → o
  parametrizador falha explicitamente). Por isso é **complementar**, não a via de Boro: ótimo para
  orgânicos padrão e MM-GBSA; para Boro, cai para xtb se a parametrização falhar.
- **O que computa:** ΔE de interação MM ou MM-GBSA de ponto único (sem MD, ou minimização curta).

#### Nível 4 — `uff_ie` (fallback barato, condicionado à parametrização)

- **Ferramenta:** RDKit UFF (Universal Force Field) — **puro Python/C++ já nas dependências**.
- **Boro:** UFF possui parâmetros para muitos elementos, incluindo Boro, mas a implementação deve
  testar `UFFHasAllMoleculeParams`/equivalente e rejeitar explícita e seguramente qualquer caso
  não parametrizável.
- **O que computa:** energia de interação intermolecular aproximada. Não requer binário externo,
  mas só é oferecida após o teste de parametrização; se falhar, registrar o motivo em vez de
  inventar um score.

**Cadeia de fallback do router para Boro:** `xtb_gfn2` → (se xtb ausente) `pm6_sqm` → (se MOPAC
ausente) `openmm_mmgbsa` → (se parametrizar) `uff_ie`. Se todos falharem, retornar erro explicável,
preservar poses e orientar a configurar xTB/PM6; nunca fabricar uma opção "universal".

> **Nota científica obrigatória (UI + relatório):** os scores QM/MM com solvatação são estimativas
> de energia livre de interação relativa; a acurácia de afinidade absoluta depende do alvo. No nível
> SQM2.20, o protocolo completo pode competir com/superar FF e ML nos benchmarks publicados; xTB
> deve ser interpretado como ranking físico calibrável até ser validado para o alvo/quimiotipo, não
> como Kd exato nem como garantia de superioridade.

### 4.5. Scorers ML agnósticos (opcionais, com ressalva de domínio)

`rtmscore`, `onionnet_sfct`: featurização por distância/grafo é agnóstica ao elemento, então
tecnicamente aceitam Boro, **mas os modelos foram treinados em PDBbind (quase sem boro)** — a
predição é extrapolação. Disponibilizar como "análise avançada" com etiqueta `OOD` (out of
domain) e **nunca** como via primária de Boro. Isolar suas dependências pesadas (`torch`/`dgl`)
num **env conda dedicado** invocado por subprocess (substitui o esquema zip+PYTHONPATH do 1.x).

### 4.6. AD4 destravado com parâmetro de Boro (opcional, avançado)

Para quem quer docking (não só rescoring) de boro dentro do ecossistema AutoDock:

1. Implementar geração de GPF + execução de `autogrid4` (resolve a pendência do 1.x).
2. Fornecer um **arquivo de parâmetros AD4 estendido** (`data/AD4_boron_parameters.dat`) com uma
   linha `atom_par B` (Rii, epsii, vol, solpar, Rij_hb, epsij_hb, hbond, ...). Ver valores
   sugeridos no Apêndice 14.3. Isso permite `autogrid4` gerar mapa para o tipo `B` e `vina
   --scoring ad4` posicionar o boro.
3. Meeko/preparo precisa emitir o tipo `B` no PDBQT (§5).

> Marcar como **experimental**: os parâmetros de boro AD4 são uma aproximação; o ranking físico
> confiável continua sendo a via xtb (§4.4). Priorizar xtb; AD4-boro é um extra para usuários
> que exigem docking flexível de boro.

### 4.7. Consenso e normalização (portar do 1.x, estender)

- **Consenso entre scorers** (`analysis/consensus.py`): já existe no 1.x (coluna de consenso na
  results_tab). Estender para rank-based consensus (média de ranks Z-normalizados) porque as
  unidades diferem (kcal/mol Vina vs. score RTMScore vs. Eh xtb). **Nunca somar unidades
  diferentes** — comparar por rank ou por Z-score dentro de cada scorer.
- **Ligand efficiency**: `LE = −score / heavy_atoms` (contar heavy atoms via RDKit). Adicionar
  coluna. Evita favorecer moléculas grandes.

---

## 5. Pipeline de preparação com suporte a elementos exóticos

O 1.x prepara ligante com **RDKit + Meeko** (`converter.py::_convert_ligand_rdkit_meeko`) e cai
para Open Babel. O problema do Boro está aqui: Meeko emite tipagem AutoDock, que não tem Boro, e
`file_utils.sanitize_pdbqt_for_vina` normaliza/remove o átomo.

### 5.1. Detecção precoce de elementos

No carregamento do ligante, RDKit lê a molécula e extrai `elements = {atom.GetSymbol()}`. Isso
alimenta `PoseInput.elements` e o router (§4.2). Detecção acontece **antes** da conversão a PDBQT.

### 5.2. Dois caminhos de preparo

```python
# vinalab_core/prepare/element_router.py
def prepare_ligand(mol, out_dir) -> LigandArtifacts:
    elements = {a.GetSymbol() for a in mol.GetAtoms()}
    if elements & (EXOTIC_ELEMENTS | METALS):
        return prepare_exotic_ligand(mol, out_dir)   # preserva química; não presume docking
    return prepare_autodock_ligand(mol, out_dir)     # RDKit+Meeko (1.x)
```

- **`prepare_autodock_ligand`** (padrão): reaproveita `_convert_ligand_rdkit_meeko` do 1.x →
  gera PDBQT tipado para Vina/Vinardo/GNINA/Smina.
- **`prepare_exotic_ligand`** (Boro & cia): **não** produz tipagem AutoDock. Gera:
  - `ligand.sdf` (RDKit, 3D embedado com ETKDG, Hs adicionados, cargas MMFF/Gasteiger onde
    aplicável; para Boro usar cargas Gasteiger ou EEM via Open Babel).
  - `ligand.pdbqt` **só se** o usuário escolher AD4-boro (§4.6), usando o mapeamento de tipo `B`.
  - `ligand.mol2` para OpenMM/xtb pipelines que preferem mol2.
  Estes artefatos alimentam os scorers agnósticos (xtb/OpenMM/UFF), que **não passam pela
  sanitização AutoDock** — o átomo de boro é preservado.

### 5.3. Estados químicos e modo covalente

Antes de preparar qualquer artefato, executar `ChemicalStateService`:

1. Ler estrutura, estereoquímica, carga formal, elementos e ligações; falhar de forma explicável em
   valência/química inválida, sem "consertar" ou remover átomo silenciosamente.
2. Gerar/permitir selecionar tautômeros e protonações no pH configurado; cada alternativa recebe
   `chemical_state_id`, carga, multiplicidade, método de carga e hash.
3. Para Boro/metal ou grupo reativo, apresentar **Covalent mode** com estado `noncovalent`,
   `pre_reaction` ou `post_reaction`. Se o usuário selecionar covalente, exigir resíduo, átomo
   nucleofílico e restrições de distância/ângulo antes de criar o `PoseSearchPlan`.
4. Nunca tipar B como C, eliminar B durante sanitização ou inferir automaticamente que uma molécula
   é covalente. O relatório deve registrar estado escolhido e avisos.

### 5.4. Preparo do receptor

Reaproveitar `prepare_protein_tab` + ProDy/gemmi. Para a via xtb, adicionar `truncate_pocket()`
(recorte do bolsão em raio configurável, capping de ligações cortadas com H). Guardar o bolsão
truncado em cache por receptor+centro+raio.

### 5.5. Guarda de qualidade

Portar/estender os "alertas de qualidade de pose" do roadmap 1.x: clashes, ligante fora da caixa
(já existe `_validate_ligand_inside_grid`), ausência de H, geometria de boro suspeita (boro é
tipicamente sp2 trigonal ou sp3 tetraédrico — checar hibridização/valência via RDKit), frame de
coordenadas compatível e `SearchBox` válido depois do preparo do receptor e antes de gerar mapas.

---

## 6. Estratégia cross-platform (Windows + Ubuntu; macOS secundário)

Esta seção resolve a classe de bug nº 2 (§1.2): descoberta frágil de binários. **Decisão do
usuário: conda-forge é a base de toolchain.** macOS é alvo secundário (best-effort).

### 6.1. Toolchain unificada via conda-forge

**Decisão (confirmada):** distribuir/instalar as ferramentas nativas via **conda-forge**, que tem
builds oficiais para Windows, Linux e macOS de: `vina`, `openbabel`, `xtb`, `mopac`, `smina`,
`autodock-vina`, `autogrid`, `openmm`, `openmmforcefields` (e `gnina` no Linux). Isso elimina a
caça manual de DLL/SO/plugins do Open Babel que domina os commits recentes do 1.x — a via de
pontuação de Boro (`xtb`, `mopac`) vem pronta e idêntica nos três SOs.

- **Modo desenvolvedor / power user:** `environment.yml` define as dependências e gera lockfiles
  versionados por plataforma (`conda-lock.win-64.yml`, `conda-lock.linux-64.yml`, `conda-lock.osx-*.yml`).
  CI e releases instalam pelo lockfile, não por resolução solta.
- **Modo usuário final:** bundle PyInstaller que **embute** os binários necessários em `tools/`
  (como o 1.x já faz para vina/gnina), agora incluindo `xtb` e `mopac` + libs. O `tool_locator`
  procura primeiro em `tools/`, depois no env conda, depois no PATH.

### 6.2. `tool_locator` (portar e generalizar `native_tools.py`)

```python
# vinalab_core/tools/tool_locator.py
def find_tool(name: str) -> ToolInfo | None:
    """Ordem: tools/<name>[.exe] → $CONDA_PREFIX/{bin,Scripts,Library/bin}
       → PATH. Retorna caminho + versão + env necessário (LD_LIBRARY_PATH/PATH
       com libs adjacentes)."""
```

Reaproveitar do 1.x: `native_tool_env()`, `native_tool_starts()`, a lógica de DLL do Windows e
de plugins do Open Babel. Generalizar a tabela de nomes por SO (`xtb`/`xtb.exe`,
`gnina`/(sem win), `autogrid4`/`autogrid4.exe`).

### 6.3. Diferenças de SO a tratar explicitamente

| Aspecto | Windows | Linux (Ubuntu) | macOS (secundário) |
|---|---|---|---|
| `CREATE_NO_WINDOW` | usar (já no 1.x) | 0 | 0 |
| Executáveis | `.exe` | sem sufixo, `chmod +x` | sem sufixo; assinar/notarizar p/ distribuir |
| Libs runtime | DLLs adjacentes; `PATH`/`add_dll_directory` | `.so`; `LD_LIBRARY_PATH`, `$ORIGIN` rpath | `.dylib`; `@rpath`, `DYLD_LIBRARY_PATH` |
| QtWebEngine congelado | ok | `--single-process --no-sandbox --disable-gpu` (já no 1.x) | ok |
| Open Babel plugins/data | `BABEL_LIBDIR`, `BABEL_DATADIR` | idem, caminhos diferentes | idem |
| GNINA | indisponível → desabilitar na UI | disponível | via conda (best-effort) |
| Diretório de dados do usuário | `%LOCALAPPDATA%\VinaLab` | `~/.local/share/VinaLab` | `~/Library/Application Support/VinaLab` |
| Empacotamento | PyInstaller + Inno Setup (`.iss`) | PyInstaller + AppImage + `.desktop` | PyInstaller + `.app`/`.dmg` |

Reaproveitar `packaging/windows/VinaLab.iss`, `packaging/linux/run_vinalab.sh`,
`packaging/linux/vinalab.desktop` e `packaging/macos/run_vinalab.command` do 1.x como ponto de partida.

### 6.4. CPU, GPU e política de paridade

- **Vina CPU:** expor `--cpu N`; o padrão é `min(detectados - 1, cpu_budget)`, nunca todos os
  cores sem confirmação.
- **Vina-GPU / AutoDock-GPU:** plugins opcionais, instalados/desabilitados independentemente. O
  primeiro é um motor Vina-derivado; o segundo usa mapas AD4 e pode ser o POC para parâmetros de
  Boro. Detectar CUDA/OpenCL, GPU, driver e VRAM em tela de diagnóstico; falhar para CPU sem
  interromper o projeto.
- **OpenMM:** oferecer plataformas CPU/CUDA/OpenCL/HIP, `DeviceIndex`, precisão e threads. xTB é
  tratado como CPU e recebe limite de threads via ambiente.
- **GPU não é botão global:** cada motor declara `supports_gpu`, fornecedores/API aceitos, GPUs,
  precisão, versão e limites. O usuário escolhe dispositivo somente se o motor suportar.
- **Paridade:** CPU e GPU não precisam ser bit-a-bit iguais. Exigir que cada motor atinja os
  critérios de pose/ranking do benchmark próprio, dentro de tolerância definida. Resultados de
  motores diferentes nunca são misturados como se fossem a mesma função de scoring.

### 6.5. Teste de paridade cross-platform (CI)

GitHub Actions com matriz `{windows-latest, ubuntu-latest, macos-latest}` (macOS pode ser
`continue-on-error: true` enquanto secundário): instala o lockfile da plataforma, roda a suíte de
regressão (§10) e compara o **mesmo motor/método** entre SOs dentro de tolerância documentada.
Vina pode exigir `|Δ| < 0.05 kcal/mol`; para xTB/PM6 validar ranking e intervalo numérico definido
por versão. GPU roda em runner/self-hosted dedicado e não bloqueia release até ser suportada.

### 6.6. Confiabilidade operacional multi-SO

- Chamar ferramentas com listas de argumentos (`shell=False`), UTF-8 e paths absolutos; testar
  diretórios com espaços, acentos e caracteres não ASCII em Windows e Linux.
- Criar diretórios temporários por run, curtos e controlados; evitar limite de path do Windows.
- Executar plugins pesados em subprocesso isolado com protocolo JSON, timeout, cancelamento que
  mata toda árvore de processos, limite de recursos e captura de stdout/stderr.
- Validar binário, versão e smoke test na tela **Diagnostics** antes de habilitar um plugin. Não
  baixar/instalar dependências silenciosamente durante docking.
- Gerar manifesto por run com hashes, comando, variáveis de ambiente relevantes, versões, CPU/GPU,
  seed, logs e arquivos de entrada/saída. Persistir de modo atômico e permitir retomar run interrompido.
- Manter migrations versionadas do SQLite, backup antes de migração, crash-report local opt-in sem
  enviar estruturas químicas, SBOM e revisão de licenças antes do empacotamento.

---

## 7. Modelo de dados e persistência

Trocar o fluxo "linhas soltas em memória + CSV" por um **projeto persistente em SQLite** (o
roadmap 1.x já pede isso). Schema mínimo:

```sql
runs(run_id PK, created_at, status, receptor_hash, coordinate_frame_id,
     box_center_x/y/z, box_size_x/y/z, box_margin, box_source,
     exhaustiveness, seed, num_modes, cpu_threads, gpu_devices_json,
     vinalab_version, tool_versions_json, manifest_path, resumed_from_run_id)
ligands(ligand_id PK, run_id FK, name, source_path, smiles, inchikey,
        heavy_atoms, mw, elements_json, has_exotic BOOL)
chemical_states(state_id PK, ligand_id FK, tautomer_id, protonation, ph, charge,
                multiplicity, charge_model, covalent_mode, warnings_json)
search_plans(plan_id PK, run_id FK, engine_key, experimental BOOL, covalent_spec_json,
             resource_request_json, search_box_json)
poses(pose_id PK, ligand_id FK, state_id FK, plan_id FK, mode, rmsd_lb, rmsd_ub,
      output_pdbqt_path, output_sdf_path, pose_hash)
scores(score_id PK, pose_id FK, scorer_key, scorer_version, score, unit,
       ok BOOL, error, extra_json, computed_at)     -- 1 pose : N scorers
interactions(pose_id FK, residue, itype, distance)  -- IFP
clusters(pose_id FK, cluster_id, is_representative)
```

- **Cache de rescoring:** chave `hash(receptor_truncado)+ligand_pose_hash+scorer_key+scorer_version`.
  Se existir, não recomputar (crítico para xtb/RTMScore que são caros).
- **Cache de grid:** chave `receptor_preparado_hash + SearchBox(center,size,frame) + spacing +
  tipos_atômicos + engine_version`. Qualquer alteração do centro/tamanho invalida o cache.
- **Export "analysis-ready":** `to_parquet()` das tabelas `runs/ligands/poses/scores/interactions`
  para uso em R/Python/Jupyter.
- A `results_tab` do 1.x passa a ler deste modelo (adaptar o mapeamento de colunas).

---

## 8. Camada de UI (sólida, amigável e em inglês)

Manter a familiaridade do `mainwindow.py`, mas organizar o fluxo em passos claros:

```text
Project → Receptor → Ligand & chemical state → Search box → Pose generation
        → Rescoring → Run → Results → Validation → Report
```

### 8.1. Princípios obrigatórios de UX

- Interface, CLI, relatórios, tooltips, mensagens de erro e documentação distribuída em inglês
  (`en_US`). Preservar `i18n.py` como infraestrutura, com um único catálogo inicial.
- Todo campo tem unidade, faixa válida, valor padrão, dica curta e validação inline. Botões de run
  ficam desabilitados com uma lista concreta do que falta, nunca com erro genérico após clicar.
- O usuário vê o que será executado: motor, scorer(s), caixa, estados químicos, CPU, GPU, seed,
  estimativa de custo e avisos científicos. Nunca alterar opções silenciosamente.
- Operações longas mostram etapa, itens concluídos/total, tempo decorrido, estimativa quando
  possível, log expansível, `Cancel` e `Run in background`. Cancelar conserva resultados já válidos.
- Layout responsivo, navegação por teclado, ordem de tabulação, contraste e ícones com texto;
  não depender apenas de cor para erro/experimental/disponível.

### 8.2. Telas e fluxos

1. **Project home:** criar/abrir projeto, últimos runs, estado de banco, versões e botão
   **Diagnostics**. Abrir projeto corrompido em modo de recuperação, sem sobrescrever arquivos.
2. **Receptor:** importação, limpeza, cadeia/altloc, protonação, preview e resumo das alterações.
   Mostrar o `coordinate_frame_id` do receptor preparado.
3. **Ligand & chemical state:** mostrar estrutura 2D/3D, elementos, carga e avisos de valência.
   Oferecer tautômero/protonação e, para Boro/metal/grupo reativo, o cartão **Covalent mode**.
   A confirmação do usuário é necessária antes de criar uma busca covalente.
4. **Search box:** campos `Center X/Y/Z (Å)` e `Size X/Y/Z (Å)`, presets e botões **Fit to
   reference ligand** e **Fit to selected residues**. Alterar qualquer campo atualiza imediatamente
   o cubo 3D e a tabela `Min/Max`; a tela mostra se o ligante de referência está inteiramente dentro.
   Exibir margem, frame e aviso de cache que será recriado.
5. **Pose generation:** escolher motor com badges `Stable`, `Experimental`, `CPU`, `GPU`,
   `Boron-compatible` e `Covalent`. Para Boro, explicar que rescoring não gera poses e bloquear
   Continue até selecionar um motor compatível ou importar poses externas.
6. **Rescoring:** lista separada do motor de busca. Exibir suporte por elemento, disponibilidade,
   custo e motivo de indisponibilidade. Seleção automática pode sugerir xTB, mas requer confirmação
   e nunca oculta a decisão.
7. **Compute:** seletor simples `Use up to N CPU cores`, `Keep one core free`, número de jobs e
   seletor de GPU apenas quando aplicável. Link **Test hardware** executa diagnóstico rápido sem
   docking. Mostrar fila e impedir oversubscription.
8. **Run monitor:** tabela por ligante/pose com status preparado → buscando → pontuando → salvo,
   erros copiáveis e ação **Retry failed step**. Não perder o log ao trocar de aba.
9. **Results:** tabela com motor, estado químico, `scorer`, unidade, `LE`, `has_exotic`,
   `experimental`, `scoring_error`; viewer sincronizado, filtros e export. Separar visualmente
   resultados de motores/scorers diferentes; consenso só por rank normalizado entre conjuntos válidos.
10. **Validation:** wizard de redocking que pede receptor preparado e ligante de referência,
    preenche caixa por bounding box + margem, permite editar e só então executa. Mostrar RMSD
    heavy-atom/symmetry-aware top-1/3/10, taxa <2 Å, pose sobreposta e configuração exata.
11. **Report:** relatório em inglês com figuras, resultados, limitações, manifest, hashes, versões,
    caixas, recursos, warnings de Boro/OOD/covalência e arquivos de reprodução.

### 8.3. Estados de erro e mensagens

Cada falha deve informar: **what failed**, **why**, **what the user can do**, **technical details**
copiáveis. Exemplos: `Reference ligand atom B12 is outside Search box maximum X`, `AutoDock-GPU is
experimental for boron and has not passed the selected validation profile`, `xTB unavailable: binary
not found; choose a configured environment or use a parametrizable fallback`. Reuso direto de
`style.qss`, splash, about e help, adaptados ao novo vocabulário em inglês.

---

## 9. Migração 1.x → 2.0

1. **Fork limpo:** copiar do 1.x apenas os arquivos canônicos; **descartar todos os
   `-Notebook_AMG*`**. Lista canônica em §1.1.
2. **Extrair o núcleo:** mover lógica não-Qt de `docking_engine.py`, `converter.py`,
   `file_utils.py`, `native_tools.py` para `vinalab_core/`. Deixar os `QThread` como cascas finas
   em `vinalab_ui/`.
3. **Refatorar scoring:** transformar os ramos `if scoring_key == ...` de
   `DockingWorker._run_ligand_with_scoring` em plugins `ScoringPlugin` (§4.1).
4. **Trocar zip+PYTHONPATH** dos scorers pesados por envs conda isolados + cache.
5. **Adicionar** `xtb_scorer`, `openmm_scorer`, `uff_scorer`, `element_router`, `tool_locator`
   generalizado, `SearchBoxService`, `ChemicalStateService`, `ResourceManager`, camada SQLite e
   manifest de run.
6. **Portar UI** adaptando ao novo modelo de dados e ao fluxo de §8; migrar strings visíveis para
   `en_US`, sem recriar a lógica de negócio em widgets Qt.
7. **Ler `pontuacao/`**: os zips RTMScore/DeltaVinaXGB podem ser reusados como implementação dos
   plugins correspondentes (empacotados em env isolado).

---

## 10. Testes e validação científica

### 10.1. Testes de software (portar/estender `tests/` do 1.x)

- Unit: parsing PDBQT, sanitização, roteamento por elemento, cadeia de fallback Boro, cache,
  `SearchBox.minimum/maximum/contains_all`, auto-fit por bounding box e invalidação de grid.
- Contrato: para cada plugin, `is_available`/`can_score`/`score` respeitam o protocolo.
- Smoke headless: rodar um docking pequeno sem UI (o 1.x já tem `test_smoke_workflows.py`).
- Contrato de motor: `DockingEngine` declara elementos, CPU/GPU, requisitos de mapa e se é
  experimental; não aceitar `PoseSearchPlan` incompatível.
- Integração: mover o centro três vezes e verificar que preview serializada, comando do motor,
  `SearchBox` persistido e chave de grid são idênticos; mudar tamanho/frame também invalida cache.
- UI: testes Qt de campos inválidos, botão Run bloqueado, atualização imediata da caixa, cancelamento,
  recuperação e mensagens de erro em inglês. Testes de acessibilidade por teclado.
- Robustez: paths com espaço/acentos, permissão negada, binário ausente, timeout, processo filho
  travado, banco interrompido durante escrita e migração de schema com backup.

### 10.2. Suíte de regressão de scoring (nova, essencial)

3–5 complexos públicos por perfil químico, com pose conhecida. Para cada motor/scorer: verificar
saída, ranking estável, metadados completos e ausência de erro. Separar perfis: orgânicos padrão,
Boro não covalente, Boro covalente e metal. **Incluir ≥1 complexo borônico** (ex.:
bortezomibe/proteassoma PDB **2F16**, após confirmar estado covalente e preparo correto) para
validar preparação → geração de pose → rescoring. Nunca validar Boro apenas pelo fato de xTB
retornar uma energia.

### 10.3. Validação científica (painel na UI)

- **Redocking / docking power:** RMSD top-1/3/10, taxa <2 Å.
- **Ranking power:** Spearman vs. afinidades experimentais quando fornecidas.
- **Screening power / enriquecimento:** ROC-AUC, EF1%, EF5%, BEDROC.
- **Paridade cross-platform:** §6.5.
- **Validação da caixa:** todo caso de redocking registra o auto-fit e executa ao menos um caso de
  centro alterado manualmente; a referência deve estar contida e o comando deve reproduzir a caixa.
- **Comparação justa:** comparar somente o mesmo motor/estado químico; CPU/GPU e motores distintos
  usam benchmark/tolerância próprios e não igualdade bit-a-bit.

### 10.4. Validação específica de Boro

Como não há benchmark CASF com boro, validar por **consistência física e química**: séries
congêneres de ácidos borônicos com Ki conhecido, separando casos não covalentes e covalentes →
checar ranking (Spearman, intervalo de confiança e split por scaffold), taxa de redocking e
geometria de reação quando aplicável. Documentar que xTB é energia relativa calibrável, não Kd
absoluto; só promover um motor experimental a estável após atingir critérios pré-definidos.

---

## 11. Roadmap por fases (com critérios de aceite)

### Fase 0 — Fundação limpa (1–2 semanas)
- Novo repo `vinalab_core` + `vinalab_ui` + `vinalab_cli`; descartar duplicados `-Notebook_AMG`.
- `environment.yml` + `conda-lock` por plataforma; `tool_locator` generalizado; CI matriz Win/Linux (+macOS best-effort).
- `SearchBox`, `ResourceManager`, migrações SQLite, manifest e esqueleto de Diagnostics antes da UI de docking.
- **Aceite:** app abre em Win e Ubuntu; `pytest` verde nos dois; toolchain resolvida por lockfile;
  diagnóstico explica ferramenta ausente; alterar centro de caixa atualiza modelo e invalida cache.

### Fase 1 — Núcleo desacoplado + scoring como plugin (2–3 semanas)
- Extrair núcleo sem Qt; contrato `ScoringPlugin`; registry; portar Vina/Vinardo/Smina/GNINA como
  plugins; `DockingEngine`/`PoseSearchPlan` separados de scoring; modelo SQLite + cache.
- **Aceite:** docking Vina/Vinardo idêntico ao 1.x, agora via plugins; resultados persistidos;
  scores Vina batem entre Win e Linux (tolerância §6.5); redocking wizard reproduz caixa e mostra
  RMSD symmetry-aware; UI de setup em inglês bloqueia configurações inválidas antes do run.

### Fase 2 — Via Boro / física-QM (3–4 semanas) ⟵ **entrega central**
- `element_router`; `prepare_exotic_ligand`; `truncate_pocket`; plugins `uff_ie`, `xtb_gfn2`,
  `xtb_gfnff` **com solvatação ALPB/GBSA** (nunca vácuo); `ChemicalStateService`; modo covalente;
  cadeia de fallback validada; UI banner + seleção explícita.
- **Aceite:** carregar ligante com Boro → via física-QM ativada automaticamente; xtb (com
  solvatação) retorna score válido em Win **e** Ubuntu para poses e estados químicos declarados;
  UFF só aparece se parametrizar; não há mapeamento silencioso B→C; validação de ordenação numa
  série congênere de ácidos borônicos com Ki conhecido. A etapa não declara docking de Boro pronto
  enquanto o POC de geração de poses/covalência não passar os critérios de §10.

### Fase 3 — Alta acurácia (SQM2.20/PM6) + física complementar + AD4 (2–3 semanas)
- Plugin `pm6_sqm` (MOPAC + termos SQM2.20: PM6-D3H4X/COSMO2 + solv + entropia); `openmm_mmgbsa`;
  destravar `ad4` (GPF + autogrid4); POC `ad4_gpu`/`vina_gpu`; `AD4_boron_parameters.dat` experimental.
- **Aceite:** `pm6_sqm` reproduz a ordenação de um subconjunto do benchmark PL-REX; MM-GBSA roda
  em orgânicos padrão; AD4 gera mapas e docka nos dois SOs; qualquer motor GPU passa diagnóstico,
  seleção de dispositivo, controle de recursos e benchmark próprio antes de aparecer como `Stable`.

### Fase 4 — Análise avançada (2–3 semanas)
- ValidationPanel (redocking/RMSD/enriquecimento); consenso por rank; LE; IFP; heatmaps;
  isolar RTMScore/DeltaVinaXGB/OnionNet em env conda; relatório reprodutível; recuperação de jobs.
- **Aceite:** painel CASF-like funcional; scorers ML pesados rodam isolados sem quebrar o core.

### Fase 5 — Empacotamento e distribuição (1–2 semanas)
- PyInstaller + Inno Setup (Win) + AppImage/.desktop (Linux) + `.app`/`.dmg` (macOS, best-effort),
  com `xtb` e `mopac` embutidos; instaladores testados em máquina limpa.
- **Aceite:** instalar do zero em Win e Ubuntu limpos e docar+pontuar boro sem internet/conda.

---

## 12. Riscos e decisões em aberto

**Decisões estratégicas — resolvidas (2026-07-09):**
- ✅ **conda-forge** como base de toolchain.
- ✅ **xtb (QM semiempírica) como rescoring inicial de Boro**, com solvatação. SQM2.20 permanece
  protocolo separado de alta acurácia; ambos precisam de benchmark no domínio químico alvo.
- ✅ **macOS mantido como alvo secundário** (best-effort).
- ✅ **Interface em inglês (`en_US`)** para o release 2.0; infraestrutura de i18n preservada.

**Riscos técnicos remanescentes e mitigação:**

| Risco | Recomendação | Alternativa |
|---|---|---|
| Custo do xtb GFN2 em lotes grandes | GFN-FF como triagem + GFN2/PM6 nos top-N; cache agressivo; fila | Só GFN-FF |
| Fase gasosa dá score ruim | **Sempre** usar solvatação (ALPB/GBSA no xtb, COSMO2 no PM6) — já no desenho (§4.4) | — |
| Empacotar `xtb`+`mopac` (~dezenas de MB) | Embutir no bundle; é o preço do suporte a Boro real e da alta acurácia | Baixar sob demanda na 1ª execução |
| SQM2.20 exige montar MOPAC+Cuby+termos | Fase 3 (não bloqueia a entrega de Boro na Fase 2, que usa xtb) | Começar só com PM6+COSMO2 e adicionar termos incrementalmente |
| OpenMM aumenta o bundle | Opcional (instalável), não embutido; xtb é a via primária | Embutir se houver espaço |
| GNINA ausente no Windows | Documentar; não é via de Boro; oferecer WSL | Compilar GNINA Win (custoso) |
| Parâmetros AD4 de Boro aproximados | Marcar experimental; o número confiável vem de xtb/PM6 | Não expor AD4-boro |
| ML scorers (RTMScore) OOD para Boro | Etiqueta OOD; nunca primária | Ocultar para exóticos |
| Conda como dependência de build | Reprodutível; usuário final recebe bundle sem conda | pip-only (retoma o inferno de DLL) |
| Rescoring sem pose compatível | Separar `PoseSearchPlan` de `ScoringPlan`; bloquear run sem motor/pose | Importar pose externa e permitir somente rescoring |
| Borônico covalente modelado como não covalente | Exigir `CovalentSpec` e benchmark separado pré/pós-reação | Mostrar limitação e não prometer docking covalente |
| Caixa visual divergir da caixa executada | `SearchBox` imutável, serviço único, chave de cache com caixa e teste de integração | Bloquear execução quando frame/configuração divergirem |
| GPU/driver instável ou sem suporte | Plugin opcional, Diagnostics, fallback CPU e benchmark por hardware | Não empacotar GPU no primeiro release estável |
| UFF/OpenMM sem parâmetros | Checar parametrização antes de executar; registrar motivo | xTB/PM6 ou erro explícito, jamais score inventado |
| Processos externos travados | Isolamento, timeout, kill de árvore, checkpoints e retry | Encerrar somente o plugin e preservar o projeto |

---

## 13. Estrutura de diretórios proposta

```
VinaLab_2.0/
├─ pyproject.toml                # build, deps, entry points (vinalab, vinalab-cli)
├─ environment.yml               # conda cross-platform (vina, openbabel, xtb, mopac, openmm, ...)
├─ conda-lock.*.yml              # ambientes resolvidos e hasheados por plataforma
├─ requirements.txt              # pip core (espelha o 1.x)
├─ requirements-scoring.txt      # torch/dgl para RTMScore/DeltaXGB (env isolado)
├─ README.md · CHANGELOG.md
├─ vinalab_core/
│  ├─ prepare/  (ligand_prep, receptor_prep, element_router, chemical_states, pocket_truncate, pdbqt_utils)
│  ├─ docking/  (engine_registry, pose_search_plan, search_box, covalent, vina/smina/gnina/ad4/vina_gpu/ad4_gpu engines, pose_model)
│  ├─ scoring/  (base, registry, router, vina/vinardo/ad4/smina/gnina,
│  │            xtb, pm6_sqm, openmm, uff, linf9, onionnet, rtmscore, deltaxgb)
│  ├─ analysis/ (rmsd, cluster, consensus, enrichment, ifp, casf_validate)
│  ├─ io/       (project_db[SQLite], migrations, manifest, checkpoints, parquet_export, report_data)
│  ├─ tools/    (tool_locator, conda_env, platform, resource_manager, diagnostics, subprocess_runner)
│  └─ i18n.py
├─ vinalab_ui/
│  ├─ main.py · mainwindow.py
│  ├─ tabs/ (project, receptor, ligand, search_box, pose_generation, rescoring, compute, results, report, validation, diagnostics)
│  ├─ widgets/ (scoring_selector, engine_selector, search_box_editor, chemical_state_card, exotic_banner, run_monitor, ...)
│  ├─ workers/ (docking_worker, scoring_worker — QThread finos)
│  └─ resources/ (style.qss, icons, splash)
├─ vinalab_cli/  (headless batch)
├─ data/         (AD4_boron_parameters.dat, exemplos de teste incl. complexo borônico)
├─ packaging/    (windows/*.iss, linux/AppImage+.desktop, macos/ opcional)
└─ tests/        (unit, integração de caixa/cache, contrato de engine/plugin, UI, recuperação, regressão incl. Boro, paridade SO/GPU)
```

---

## 14. Apêndices

### 14.1. Contrato de progresso e worker (UI ↔ núcleo)

```python
# vinalab_core/common.py
@dataclass
class Progress:
    stage: str          # "prepare" | "dock" | "score" | "analyze"
    current: int
    total: int
    message: str
ProgressCb = Callable[[Progress], None]

# vinalab_ui/workers/docking_worker.py  (Qt fica só aqui)
class DockingWorker(QThread):
    progress = Signal(object)   # Progress
    row_ready = Signal(list)    # list[dict] p/ results_tab
    error = Signal(str)
    def run(self):
        service = DockingService(self.request)          # do núcleo, sem Qt
        service.run(progress=lambda p: self.progress.emit(p),
                    on_rows=lambda rows: self.row_ready.emit(rows))
```

### 14.2. Elementos que disparam a via agnóstica

```python
EXOTIC_ELEMENTS = {"B", "Si", "Se", "As", "Te", "Ge", "Sb"}
METALS = {"Mg","Mn","Zn","Ca","Fe","Cu","Ni","Co","Cd","Hg","Pt","Pd","Ru","Au","Ag","Mo","V","W"}
# Vina cobre parcialmente {Mg,Mn,Zn,Ca,Fe,Cu} como esferas LJ; para score quantitativo
# confiável de qualquer metal, preferir a via agnóstica (xtb) também.
```

### 14.3. Parâmetro AD4 experimental para Boro (Apêndice para §4.6)

Linha `atom_par` a acrescentar em `data/AD4_boron_parameters.dat` (valores iniciais a calibrar;
derivar Rii/vol de raios de vdW do boro ~2.0 Å e epsii por analogia ao C; **exige validação**):

```
# atom_par  Rii   epsii   vol      solpar   Rij_hb epsij_hb hbond bond_index
atom_par B  4.00  0.095   19.5     -0.00110 0.0    0.0      0     0
```

> Estes números são um ponto de partida por analogia (boro ~ carbono em raio, sem H-bond). São
> **aproximados** e servem só para permitir posicionamento geométrico via AutoGrid4. O ranking de
> energia confiável para boro vem da via xtb (§4.4), não daqui.

### 14.4. Fórmulas de conversão de unidade

- xtb: Hartree → kcal/mol: `E[kcal/mol] = E[Eh] × 627.5094740631`.
- Consenso: nunca somar unidades distintas; usar Z-score por scorer
  `z = (x − μ_scorer) / σ_scorer` ou rank médio.

### 14.5. Referências científicas

- **CASF-2016:** Su et al., *J. Chem. Inf. Model.* 2019. https://doi.org/10.1021/acs.jcim.8b00545
- **AutoDock Vina 1.2:** Eberhardt et al., *JCIM* 2021. https://doi.org/10.1021/acs.jcim.1c00203
- **Vinardo:** Quiroga & Villarreal, *PLoS ONE* 2016. https://doi.org/10.1371/journal.pone.0155183
- **GNINA 1.3:** McNutt et al., *J. Cheminform.* 2025. https://doi.org/10.1186/s13321-025-00973-x
- **xtb / GFN2-xTB:** Bannwarth et al., *JCTC* 2019. https://doi.org/10.1021/acs.jctc.8b01176
- **GFN-FF:** Spicher & Grimme, *Angew. Chem. Int. Ed.* 2020. https://doi.org/10.1002/anie.202004239
- **xtb (programa):** https://github.com/grimme-lab/xtb — cobre Z=1–86 (inclui Boro).
- **SQM2.20 (evidência-chave: QM semiempírica batendo FF/ML em afinidade):** Pecina et al.,
  *Nat. Commun.* 2024. https://doi.org/10.1038/s41467-024-45431-8 · PMC10847445 ·
  benchmark PL-REX: https://github.com/Honza-R/PL-REX
- **PM6 (83 elementos, inclui Boro):** Stewart, *J. Mol. Model.* 2007. https://doi.org/10.1007/s00894-007-0233-4
- **MOPAC (open source):** https://openmopac.net · https://github.com/openmopac/mopac
- **PM6-ML (PM6 + correção ML):** Nováček & Řezáč, *JCTC* 2025. https://doi.org/10.1021/acs.jctc.4c01330 · https://github.com/Honza-R/mopac-ml
- **GFN2-xTB/GFN-FF para energia livre de ligação (host-guest):** *J. Mol. Liq.* 2025 —
  confirma que GFN2-xTB reproduz tendências energéticas experimentais (localizar DOI na publicação
  antes de citar formalmente).
- **OpenMM:** Eastman et al., *PLoS Comput. Biol.* 2017. https://doi.org/10.1371/journal.pcbi.1005659
- **OpenMM platforms/resources:** https://docs.openmm.org/development/userguide/library/04_platform_specifics.html
- **AutoDock-GPU:** https://github.com/ccsb-scripps/AutoDock-GPU
- **Vina-GPU:** https://pmc.ncbi.nlm.nih.gov/articles/PMC9103882/
- **openmmforcefields / GAFF2 & OpenFF:** https://github.com/openmm/openmmforcefields
- **UFF:** Rappé et al., *JACS* 1992. https://doi.org/10.1021/ja00051a040 (parametriza toda a tabela).
- **Lin_F9:** Yang & Zhang, *JCIM* 2021. https://doi.org/10.1021/acs.jcim.1c00737
- **OnionNet-SFCT:** Zheng et al., *Brief. Bioinform.* 2022. https://doi.org/10.1093/bib/bbac051
- **RTMScore:** Shen et al., *J. Med. Chem.* 2022. https://doi.org/10.1021/acs.jmedchem.2c00991
- **DeltaVinaXGB:** Lu et al., *JCIM* 2019. https://doi.org/10.1021/acs.jcim.9b00645
- **Viés/robustez de ML scoring:** Durant et al., *Bioinformatics* 2025. https://doi.org/10.1093/bioinformatics/btaf040

---

### Resumo de uma frase

VinaLab 2.0 = UI PySide6 em inglês, amigável e auditável + núcleo desacoplado, onde a caixa de
busca tem uma única fonte de verdade, geração de poses é separada de rescoring, e Boro/elementos
exóticos usam estados químicos explícitos, docking experimental/covalente validado e rescoring
físico-QM com solvatação. CPU, GPU e dependências são gerenciadas por motor, com recuperação,
testes de redocking e paridade real entre Windows e Ubuntu.
