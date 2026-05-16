"""Runtime bilingual strings and user language preferences for VinaLab."""

from __future__ import annotations

import json
from pathlib import Path
import sys


class I18n:
    """Centralized PT-BR/EN translation registry."""

    STRINGS = {
        "app_title": {"pt": "VinaLab — Docking Molecular", "en": "VinaLab — Molecular Docking"},
        "window_title": {"pt": "VinaLab v0.0.2", "en": "VinaLab v0.0.2"},
        "author_label": {
            "pt": "Desenvolvido por Adriano Marques Gonçalves — UNIARA",
            "en": "Developed by Adriano Marques Gonçalves — UNIARA",
        },
        "author_status": {
            "pt": "© Adriano M. Gonçalves — UNIARA",
            "en": "© Adriano M. Gonçalves — UNIARA",
        },
        "tab_setup": {"pt": "Configuração", "en": "Setup"},
        "tab_docking": {"pt": "Docking", "en": "Docking"},
        "tab_results": {"pt": "Resultados", "en": "Results"},
        "tab_report": {"pt": "Relatório", "en": "Report"},
        "tab_converter": {"pt": "Conversor", "en": "Converter"},
        "menu_file": {"pt": "Arquivo", "en": "File"},
        "menu_edit": {"pt": "Editar", "en": "Edit"},
        "menu_view": {"pt": "Exibir", "en": "View"},
        "menu_window": {"pt": "Janela", "en": "Window"},
        "menu_help": {"pt": "Ajuda", "en": "Help"},
        "menu_language": {"pt": "Idioma", "en": "Language"},
        "menu_analysis": {"pt": "Análise", "en": "Analysis"},
        "export_complex": {"pt": "Exportar complexo", "en": "Export Complex"},
        "generate_report": {"pt": "Gerar relatório", "en": "Generate Report"},
        "validate_protocol": {"pt": "Validar protocolo", "en": "Validate Protocol"},
        "view_selected_pose": {"pt": "Abrir no PyMOL", "en": "Open in PyMOL"},
        "compare_button": {"pt": "Comparar", "en": "Compare"},
        "export_filtered_subset": {"pt": "Exportar subconjunto filtrado", "en": "Export filtered subset"},
        "pinned_only": {"pt": "Somente fixadas", "en": "Pinned only"},
        "ligand_name_filter": {"pt": "Nome do ligante", "en": "Ligand name"},
        "scoring_all": {"pt": "Pontuação: todas", "en": "Scoring: all"},
        "select_pose_preview": {"pt": "Selecione uma pose para carregar a visualização 3D.", "en": "Select a pose to load the 3D preview."},
        "export_interaction_table": {"pt": "Exportar tabela de interações", "en": "Export interaction table"},
        "export_best_cluster": {"pt": "Exportar melhor por cluster", "en": "Export best per cluster"},
        "protein_atom_center": {"pt": "Centro por átomo da proteína", "en": "Protein atom center"},
        "adjust_box_size_ligand": {"pt": "Ajustar tamanho da caixa pelos limites do ligante", "en": "Adjust box size from ligand bounds"},
        "choose_receptor_atom": {"pt": "Escolher átomo do receptor como centro da caixa", "en": "Choose a receptor atom as box center"},
        "load_receptor_atoms": {"pt": "Carregar átomos do receptor", "en": "Load receptor atoms"},
        "snap_selected_atom": {"pt": "Centralizar no átomo/resíduo selecionado", "en": "Snap to selected atom/residue"},
        "snap_crystal_ligand": {"pt": "Centralizar no ligante cristalográfico", "en": "Snap to crystallographic ligand"},
        "save_box": {"pt": "Salvar caixa", "en": "Save box"},
        "pre_run_checklist": {"pt": "Checklist pré-execução", "en": "Pre-run Checklist"},
        "results_table": {"pt": "Tabela de resultados", "en": "Results Table"},
        "interactions": {"pt": "Interações", "en": "Interactions"},
        "consensus": {"pt": "Consenso", "en": "Consensus"},
        "clusters": {"pt": "Clusters", "en": "Clusters"},
        "pose_rank": {"pt": "Rank da pose", "en": "Pose rank"},
        "docking_score": {"pt": "Score de docking (kcal/mol)", "en": "Docking score (kcal/mol)"},
        "rmsd_best_pose": {"pt": "RMSD para melhor pose", "en": "RMSD to best pose"},
        "pinned": {"pt": "Fixada", "en": "Pinned"},
        "notes": {"pt": "Notas", "en": "Notes"},
        "scoring_error": {"pt": "Erro de pontuação", "en": "Scoring error"},
        "residue": {"pt": "Resíduo", "en": "Residue"},
        "interaction_type": {"pt": "Tipo de interação", "en": "Interaction type"},
        "donor": {"pt": "Doador", "en": "Donor"},
        "acceptor": {"pt": "Aceptor", "en": "Acceptor"},
        "distance_a": {"pt": "Distância Å", "en": "Distance Å"},
        "angle": {"pt": "Ângulo", "en": "Angle"},
        "frequency_top10": {"pt": "Frequência top10", "en": "Frequency top10"},
        "contact_cutoff": {"pt": "Corte de contato (Å)", "en": "Contact cutoff (Å)"},
        "cluster_id": {"pt": "ID do cluster", "en": "Cluster ID"},
        "cluster_size": {"pt": "Tamanho", "en": "Size"},
        "best_score": {"pt": "Melhor score", "en": "Best score"},
        "representative_pose": {"pt": "Pose representante", "en": "Representative pose"},
        "members": {"pt": "Membros", "en": "Members"},
        "mean_rank": {"pt": "Rank médio", "en": "Mean rank"},
        "borda_count": {"pt": "Contagem Borda", "en": "Borda count"},
        "zscore_consensus": {"pt": "Consenso Z-score", "en": "Z-score consensus"},
        "rank_sd": {"pt": "DP dos ranks", "en": "Rank SD"},
        "divergence_flag": {"pt": "Divergência", "en": "Divergence flag"},
        "action_exit": {"pt": "Sair", "en": "Exit"},
        "action_quick_help": {"pt": "Guia rápido", "en": "Quick Guide"},
        "action_show_help_panel": {"pt": "Mostrar painel de ajuda", "en": "Show Help Panel"},
        "lang_portuguese": {"pt": "Português", "en": "Portuguese"},
        "lang_english": {"pt": "Inglês", "en": "English"},
        "converter_title": {"pt": "Conversor de Arquivos Moleculares", "en": "Molecular File Converter"},
        "converter_subtitle": {
            "pt": "AutoDock Vina aceita apenas arquivos .pdbqt como entrada de docking. Converta arquivos .pdb ou .mol2 aqui antes de seguir para a Configuração.",
            "en": "AutoDock Vina accepts only .pdbqt files as docking input. Convert .pdb or .mol2 files here before moving to Setup.",
        },
        "converter_pdbqt_note": {
            "pt": "Atenção: receptor e ligantes usados no docking devem estar no formato .pdbqt.",
            "en": "Note: receptor and ligand files used for docking must be in .pdbqt format.",
        },
        "selected_files": {"pt": "{count} arquivo(s) selecionado(s)", "en": "{count} file(s) selected"},
        "select_input_files": {"pt": "Selecionar arquivo(s) moleculares", "en": "Select molecular file(s)"},
        "output_folder": {"pt": "Pasta de saída", "en": "Output folder"},
        "select_output_folder": {"pt": "Selecionar pasta de saída", "en": "Select output folder"},
        "mol_type_ligand": {"pt": "Ligante", "en": "Ligand"},
        "mol_type_receptor": {"pt": "Receptor (proteína)", "en": "Receptor (protein)"},
        "convert_button": {"pt": "⚙️ Converter para PDBQT", "en": "⚙️ Convert to PDBQT"},
        "use_as_receptor": {"pt": "➡️ Usar como receptor no Setup", "en": "➡️ Use as receptor in Setup"},
        "use_as_ligand": {"pt": "➡️ Usar como ligante no Setup", "en": "➡️ Use as ligand in Setup"},
        "use_as_ligand_batch": {
            "pt": "➡️ Usar pasta de ligantes no Setup",
            "en": "➡️ Use ligand folder in Setup",
        },
        "conv_success": {"pt": "✅ Conversão concluída", "en": "✅ Conversion complete"},
        "conv_failure": {"pt": "❌ Falha na conversão", "en": "❌ Conversion failed"},
        "conv_batch_success": {"pt": "✅ {count} arquivo(s) convertido(s)", "en": "✅ {count} file(s) converted"},
        "conv_batch_partial": {
            "pt": "⚠️ {ok}/{total} arquivo(s) convertido(s)",
            "en": "⚠️ {ok}/{total} file(s) converted",
        },
        "conv_no_input": {"pt": "Selecione ao menos um arquivo para converter.", "en": "Select at least one file to convert."},
        "conv_receptor_single": {
            "pt": "Para receptor/proteína, selecione um arquivo por conversão.",
            "en": "For receptor/protein, select one file per conversion.",
        },
        "dep_status_title": {"pt": "Ferramentas disponíveis:", "en": "Available tools:"},
        "tip_rdkit": {
            "pt": "RDKit: biblioteca preferencial para preparação de ligantes com meeko. Alta precisão na atribuição de tipos atômicos.",
            "en": "RDKit: preferred library for ligand preparation with meeko. High accuracy in atom type assignment.",
        },
        "tip_openbabel": {
            "pt": "OpenBabel (obabel): ferramenta de conversão universal. Usada como alternativa quando RDKit não está disponível.",
            "en": "OpenBabel (obabel): universal conversion tool. Used as fallback when RDKit is unavailable.",
        },
        "input_file": {"pt": "Arquivo de entrada", "en": "Input file"},
        "output_file": {"pt": "Arquivo de saída", "en": "Output file"},
        "molecule_type": {"pt": "Tipo de molécula", "en": "Molecule type"},
        "setup_group": {"pt": "Configuração do receptor", "en": "Receptor setup"},
        "ligand_group": {"pt": "Configuração de ligantes", "en": "Ligand setup"},
        "receptor_label": {"pt": "Receptor (PDBQT)", "en": "Receptor (PDBQT)"},
        "rigid_receptor": {"pt": "Receptor rígido (PDBQT)", "en": "Rigid receptor (PDBQT)"},
        "ligand_label": {"pt": "Ligante(s) (PDBQT)", "en": "Ligand(s) (PDBQT)"},
        "single_ligand": {"pt": "Ligante único", "en": "Single ligand"},
        "single_ligand_file": {"pt": "Arquivo do ligante único", "en": "Single ligand file"},
        "batch_folder": {"pt": "Pasta do lote", "en": "Batch folder"},
        "batch_mode": {"pt": "Modo lote (múltiplos ligantes)", "en": "Batch mode (multiple ligands)"},
        "browse_button": {"pt": "Procurar...", "en": "Browse..."},
        "flexible_receptor": {
            "pt": "Cadeias laterais flexíveis (opcional)",
            "en": "Flexible side chains (optional)",
        },
        "batch_count": {"pt": "{count} arquivos PDBQT encontrados", "en": "{count} PDBQT files discovered"},
        "warn_receptor": {"pt": "Selecione um receptor .pdbqt válido.", "en": "Select a valid receptor .pdbqt file."},
        "warn_rigid": {
            "pt": "O receptor rígido deve ser um arquivo .pdbqt válido quando informado.",
            "en": "Rigid receptor must be a valid .pdbqt file when provided.",
        },
        "warn_flex": {
            "pt": "As cadeias flexíveis devem ser um arquivo .pdbqt válido quando informadas.",
            "en": "Flexible sidechain file must be a valid .pdbqt file when provided.",
        },
        "warn_ligand": {"pt": "Selecione um ligante .pdbqt válido.", "en": "Select a valid ligand .pdbqt file."},
        "warn_batch": {
            "pt": "Selecione uma pasta de lote contendo arquivos .pdbqt.",
            "en": "Select a batch folder containing .pdbqt files.",
        },
        "select_ligand_folder": {"pt": "Selecionar pasta de ligantes", "en": "Select ligand folder"},
        "select_pdbqt": {"pt": "Selecionar arquivo PDBQT", "en": "Select PDBQT file"},
        "pdbqt_filter": {"pt": "Arquivos PDBQT (*.pdbqt)", "en": "PDBQT files (*.pdbqt)"},
        "docking_group": {"pt": "Parâmetros do AutoDock Vina", "en": "AutoDock Vina parameters"},
        "scoring_label": {"pt": "Função de pontuação", "en": "Scoring function"},
        "scoring_group": {"pt": "Função de Pontuação", "en": "Scoring Function"},
        "scoring_gnina_warn": {
            "pt": "GNINA não detectado. Sem suporte oficial nativo no Windows; use Linux/WSL ou forneça gnina.exe em tools/gnina ou no PATH.",
            "en": "GNINA not found. No official native Windows support; use Linux/WSL or provide gnina.exe in tools/gnina or PATH.",
        },
        "badge_best": {"pt": "🥇 Melhor", "en": "🥇 Best"},
        "badge_recommended": {"pt": "🥈 Recomendado", "en": "🥈 Recommended"},
        "badge_default": {"pt": "✅ Padrão", "en": "✅ Default"},
        "badge_specialized": {"pt": "🔬 Especializado", "en": "🔬 Specialized"},
        "ref_button": {"pt": "📖 Referência", "en": "📖 Reference"},
        "search_box": {"pt": "Caixa de busca (Å)", "en": "Search box (Å)"},
        "center_label": {"pt": "Centro (x, y, z)", "en": "Center (x, y, z)"},
        "size_label": {"pt": "Tamanho (x, y, z)", "en": "Size (x, y, z)"},
        "auto_grid_ligand": {"pt": "Ajustar tamanho da caixa pelos ligantes", "en": "Adjust box size from ligand bounds"},
        "auto_grid_success": {
            "pt": "Caixa ajustada ao(s) ligante(s): centro ({x:.3f}, {y:.3f}, {z:.3f}), tamanho ({sx:.1f}, {sy:.1f}, {sz:.1f}).",
            "en": "Box fitted to ligand(s): center ({x:.3f}, {y:.3f}, {z:.3f}), size ({sx:.1f}, {sy:.1f}, {sz:.1f}).",
        },
        "auto_grid_failed": {
            "pt": "Não foi possível calcular a caixa: selecione ligante(s) PDBQT válido(s) no Setup.",
            "en": "Could not calculate the box: select valid PDBQT ligand(s) in Setup.",
        },
        "exhaustiveness": {"pt": "Exaustividade", "en": "Exhaustiveness"},
        "num_modes": {"pt": "Número de poses", "en": "Number of poses"},
        "energy_range": {"pt": "Intervalo de energia (kcal/mol)", "en": "Energy range (kcal/mol)"},
        "cpu_label": {"pt": "CPUs (0 = automático)", "en": "CPUs (0 = automatic)"},
        "seed_label": {"pt": "Semente aleatória", "en": "Random seed"},
        "fix_seed": {"pt": "Fixar semente (reprodutibilidade)", "en": "Fix seed (reproducibility)"},
        "min_rmsd": {"pt": "RMSD mínimo (Å)", "en": "Minimum RMSD (Å)"},
        "output_dir": {"pt": "Diretório de saída", "en": "Output directory"},
        "save_config": {"pt": "Salvar configuração (.txt)", "en": "Save config (.txt)"},
        "load_config": {"pt": "Carregar configuração", "en": "Load config"},
        "run_docking": {"pt": "▶ Executar Docking", "en": "▶ Run Docking"},
        "select_output_dir": {"pt": "Selecionar diretório de saída", "en": "Select output directory"},
        "save_vina_config": {"pt": "Salvar configuração Vina", "en": "Save Vina config"},
        "load_vina_config": {"pt": "Carregar configuração Vina", "en": "Load Vina config"},
        "text_files": {"pt": "Arquivos de texto (*.txt)", "en": "Text files (*.txt)"},
        "all_files": {"pt": "Todos os arquivos (*)", "en": "All files (*)"},
        "ligand_col": {"pt": "Ligante", "en": "Ligand"},
        "mode_col": {"pt": "Modo", "en": "Mode"},
        "affinity_col": {"pt": "Afinidade (kcal/mol)", "en": "Affinity (kcal/mol)"},
        "rmsd_lb_col": {"pt": "RMSD l.i.", "en": "RMSD l.b."},
        "rmsd_ub_col": {"pt": "RMSD l.s.", "en": "RMSD u.b."},
        "col_cnn_score": {"pt": "CNNscore", "en": "CNNscore"},
        "col_cnn_affinity": {"pt": "CNNafinidade", "en": "CNNaffinity"},
        "export_excel": {"pt": "Exportar Excel (.xlsx)", "en": "Export Excel (.xlsx)"},
        "export_csv": {"pt": "Exportar CSV", "en": "Export CSV"},
        "chart_title": {"pt": "Distribuição de afinidade", "en": "Affinity distribution"},
        "export_excel_dialog": {"pt": "Exportar Excel", "en": "Export Excel"},
        "export_csv_dialog": {"pt": "Exportar CSV", "en": "Export CSV"},
        "summary_stats": {"pt": "Estatísticas resumidas", "en": "Summary statistics"},
        "best_affinity": {"pt": "Melhor afinidade", "en": "Best affinity"},
        "mean_affinity": {"pt": "Afinidade média", "en": "Mean affinity"},
        "ligands_docked": {"pt": "Número de ligantes dockados", "en": "Number of ligands docked"},
        "poses_per_ligand": {"pt": "Número de poses por ligante", "en": "Number of poses per ligand"},
        "generate_pdf": {"pt": "Gerar Relatório PDF", "en": "Generate PDF Report"},
        "open_folder": {"pt": "Abrir pasta de saída", "en": "Open output folder"},
        "report_title": {"pt": "Relatório de Docking VinaLab", "en": "VinaLab Docking Report"},
        "parameters": {"pt": "Parâmetros", "en": "Parameters"},
        "results": {"pt": "Resultados", "en": "Results"},
        "affinity_chart": {"pt": "Gráfico de afinidade", "en": "Affinity chart"},
        "no_results": {"pt": "Não há resultados de docking para relatar.", "en": "No docking results are available for reporting."},
        "missing_output_folder": {"pt": "Selecione ou crie uma pasta de saída primeiro.", "en": "Select or create an output folder first."},
        "env_ready": {"pt": "✅ Ambiente pronto — VinaLab operacional", "en": "✅ Environment ready — VinaLab fully operational"},
        "env_checking": {"pt": "⚙️ Verificando ambiente...", "en": "⚙️ Checking environment..."},
        "env_error": {"pt": "❌ Dependência ausente", "en": "❌ Dependency missing"},
        "fix_now": {"pt": "Corrigir agora", "en": "Fix now"},
        "launch_button": {"pt": "🚀 Iniciar VinaLab", "en": "🚀 Launch VinaLab"},
        "installer_note": {
            "pt": "O instalador permanecerá aberto até que a janela principal seja fechada.",
            "en": "The installer will remain open until the main window is closed.",
        },
        "retry_button": {"pt": "🔁 Tentar novamente", "en": "🔁 Retry"},
        "open_log_button": {"pt": "📄 Abrir log", "en": "📄 Open log"},
        "installer_ready_banner": {
            "pt": "✅ Ambiente pronto!",
            "en": "✅ Environment Ready",
        },
        "installer_failed_banner": {
            "pt": "❌ Falha na instalação",
            "en": "❌ Installation failed",
        },
        "help_button": {"pt": "❓ Ajuda", "en": "❓ Help"},
        "about_button": {"pt": "Sobre", "en": "About"},
        "tip_exhaustiveness": {
            "pt": "Controla o esforço computacional. Padrão: 8. Aumente para mais precisão (32–64 para publicações).",
            "en": "Controls computational effort. Default: 8. Increase for accuracy (32–64 for publications).",
        },
        "tip_num_modes": {
            "pt": "Número máximo de poses de ligação a gerar. Padrão: 9.",
            "en": "Maximum number of binding poses to generate. Default: 9.",
        },
        "tip_energy_range": {
            "pt": "Diferença máxima de energia (kcal/mol) em relação à melhor pose. Poses fora desse intervalo são descartadas.",
            "en": "Maximum energy difference (kcal/mol) from the best pose. Poses outside this range are discarded.",
        },
        "tip_scoring": {
            "pt": "vina: função padrão. vinardo: alternativa empírica. ad4: força AutoDock 4 (requer mapas de afinidade).",
            "en": "vina: standard function. vinardo: empirical alternative. ad4: AutoDock 4 force field (requires affinity maps).",
        },
        "tip_seed": {
            "pt": "Fixar a semente garante resultados idênticos em execuções repetidas com os mesmos parâmetros.",
            "en": "Fixing the seed ensures identical results across repeated runs with the same parameters.",
        },
        "tip_batch": {
            "pt": "Selecione uma pasta contendo múltiplos arquivos PDBQT. Todos serão encaminhados automaticamente.",
            "en": "Select a folder containing multiple PDBQT files. All will be docked automatically.",
        },
        "tip_center": {
            "pt": "Coordenadas do centro da caixa de busca no sítio de ligação.",
            "en": "Search box center coordinates over the binding site.",
        },
        "tip_size": {
            "pt": "Dimensões da caixa de busca em Å.",
            "en": "Search box dimensions in Å.",
        },
        "tip_cpu": {"pt": "Use 0 para seleção automática de CPUs.", "en": "Use 0 for automatic CPU selection."},
        "tip_output": {"pt": "Pasta onde poses, tabelas e relatórios serão salvos.", "en": "Folder where poses, tables, and reports are saved."},
        "error_title": {"pt": "Erro", "en": "Error"},
        "warning_title": {"pt": "Aviso", "en": "Warning"},
        "success_title": {"pt": "Concluído", "en": "Done"},
        "confirm_cancel": {"pt": "Cancelar o docking em andamento?", "en": "Cancel the ongoing docking run?"},
        "docking_running": {"pt": "Docking em execução", "en": "Docking running"},
        "docking_running_msg": {"pt": "O docking já está em execução.", "en": "Docking is already running."},
        "invalid_setup": {"pt": "Configuração inválida", "en": "Invalid setup"},
        "invalid_setup_msg": {"pt": "Corrija as entradas antes de executar o docking.", "en": "Fix setup inputs before running docking."},
        "missing_output": {"pt": "Diretório de saída ausente", "en": "Missing output directory"},
        "missing_output_msg": {"pt": "Selecione um diretório de saída.", "en": "Select an output directory."},
        "help_title": {"pt": "Guia Rápido", "en": "Quick Guide"},
        "help_what_is_vina": {
            "pt": "O AutoDock Vina prediz como uma molécula pequena (ligante) se encaixa em uma proteína (receptor), estimando a energia de ligação em kcal/mol. Valores mais negativos indicam maior afinidade.",
            "en": "AutoDock Vina predicts how a small molecule (ligand) fits into a protein (receptor), estimating binding energy in kcal/mol. More negative values indicate stronger binding.",
        },
        "help_pdbqt": {
            "pt": "Arquivos PDBQT são derivados do formato PDB com informações de carga e tipo atômico. Use o MGLTools ou Meeko para preparar seus arquivos.",
            "en": "PDBQT files are derived from PDB format with charge and atom type information. Use MGLTools or Meeko to prepare your files.",
        },
        "help_search_box": {
            "pt": "A caixa de busca define a região onde o docking será realizado. Centre-a sobre o sítio de ligação do receptor. O tamanho típico é 20–25 Å por dimensão.",
            "en": "The search box defines the region where docking will occur. Center it over the receptor's binding site. Typical size is 20–25 Å per dimension.",
        },
        "help_exhaustiveness": {
            "pt": "Exaustividade aumenta a profundidade da busca. Valores maiores demoram mais, mas podem melhorar a amostragem.",
            "en": "Exhaustiveness increases search depth. Higher values take longer but may improve sampling.",
        },
        "help_affinity": {
            "pt": "Afinidade é reportada em kcal/mol. Em geral, valores mais negativos indicam ligação prevista mais favorável.",
            "en": "Affinity is reported in kcal/mol. More negative values generally indicate more favorable predicted binding.",
        },
        "help_rmsd": {
            "pt": "RMSD compara poses. Valores baixos indicam poses geometricamente semelhantes.",
            "en": "RMSD compares poses. Low values indicate geometrically similar poses.",
        },
        "help_batch": {
            "pt": "No modo lote, a pasta selecionada é varrida recursivamente e cada PDBQT é processado em sequência.",
            "en": "In batch mode, the selected folder is scanned recursively and each PDBQT is processed sequentially.",
        },
        "welcome_title": {"pt": "Bem-vindo ao VinaLab", "en": "Welcome to VinaLab"},
        "welcome_body": {
            "pt": "Interface gráfica para AutoDock Vina com instalação de ambiente, execução em lote e relatórios.",
            "en": "Graphical interface for AutoDock Vina with environment setup, batch execution, and reports.",
        },
        "get_started": {"pt": "Começar", "en": "Get started"},
        "about_title": {"pt": "Sobre o VinaLab", "en": "About VinaLab"},
        "version_label": {"pt": "Versão 0.0.2", "en": "Version 0.0.2"},
        "license_label": {"pt": "Licença: Apache 2.0", "en": "License: Apache 2.0"},
        "vina_citation": {"pt": "Citação AutoDock Vina", "en": "AutoDock Vina citation"},
        "pdf_footer": {
            "pt": "Gerado por VinaLab v0.0.2 | Adriano Marques Gonçalves — UNIARA | {date}",
            "en": "Generated by VinaLab v0.0.2 | Adriano Marques Gonçalves — UNIARA | {date}",
        },
    }

    @classmethod
    def get(cls, key: str, lang: str) -> str:
        """Return a translated string for the user interface."""
        translations = cls.STRINGS.get(key, {})
        text = translations.get(lang) or translations.get("pt") or key
        return cls._repair_mojibake(text)

    @staticmethod
    def _repair_mojibake(text: str) -> str:
        """Repair UTF-8 text that was previously decoded as Latin-1/CP1252."""
        if not any(marker in text for marker in ("Ã", "Â", "â", "ï")):
            return text
        try:
            return text.encode("latin1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return text

    @classmethod
    def load_lang(cls, path: str) -> str:
        """Load the saved language from user preferences."""
        prefs = cls._read_prefs(Path(path))
        lang = prefs.get("language", "pt")
        return lang if lang in ("pt", "en") else "pt"

    @classmethod
    def save_lang(cls, lang: str, path: str) -> None:
        """Save the selected language to user preferences."""
        prefs_path = Path(path)
        prefs = cls._read_prefs(prefs_path)
        prefs["language"] = lang
        cls._write_prefs(prefs_path, prefs)

    @classmethod
    def validate_all_keys(cls) -> None:
        """Validate that every translation key has PT and EN values."""
        for key, translations in cls.STRINGS.items():
            for lang in ("pt", "en"):
                if not translations.get(lang):
                    raise ValueError(f"Missing translation: {key} → {lang}")
            for lang, text in translations.items():
                if (
                    " / " in text
                    and any(character.isalpha() for character in text.split(" / ")[0])
                    and any(character.isalpha() for character in text.split(" / ")[-1])
                ):
                    raise ValueError(
                        f"i18n contamination detected in key '{key}' [{lang}]: "
                        f"value appears to contain bilingual content: '{text}'"
                    )
            line = f"✅ {key}\n"
            if hasattr(sys.stdout, "buffer"):
                sys.stdout.buffer.write(line.encode("utf-8"))
            else:
                print(line.rstrip())

    @staticmethod
    def _read_prefs(path: Path) -> dict:
        """Read a JSON preference file."""
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def _write_prefs(path: Path, prefs: dict) -> None:
        """Write a JSON preference file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(prefs, indent=2, ensure_ascii=False), encoding="utf-8")
