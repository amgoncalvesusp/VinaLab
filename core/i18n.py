# -*- coding: utf-8 -*-
"""Runtime bilingual strings and user language preferences for VinaLab."""

from __future__ import annotations

import json
from pathlib import Path
import sys


class I18n:
    """Centralized PT-BR/EN translation registry."""

    STRINGS = {
        "app_title": {
            "pt": "VinaLab — Docking Molecular",
            "en": "VinaLab — Molecular Docking",
        },
        "window_title": {"pt": "VinaLab v0.0.5", "en": "VinaLab v0.0.5"},
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
        "tab_converter": {"pt": "Conversor (opcional)", "en": "Converter (optional)"},
        "tab_prepare_protein": {"pt": "Preparar Proteína", "en": "Prepare Protein"},
        "menu_file": {"pt": "Arquivo", "en": "File"},
        "menu_edit": {"pt": "Editar", "en": "Edit"},
        "menu_view": {"pt": "Exibir", "en": "View"},
        "menu_window": {"pt": "Janela", "en": "Window"},
        "menu_help": {"pt": "Ajuda", "en": "Help"},
        "menu_language": {"pt": "Idioma", "en": "Language"},
        "menu_analysis": {"pt": "Análise", "en": "Analysis"},
        "mw_exit_title": {"pt": "Sair do VinaLab", "en": "Quit VinaLab"},
        "mw_exit_question": {"pt": "Deseja sair?", "en": "Do you want to quit?"},
        "export_complex": {"pt": "Exportar complexo", "en": "Export Complex"},
        "generate_report": {"pt": "Gerar relatório", "en": "Generate Report"},
        "validate_protocol": {"pt": "Validar protocolo", "en": "Validate Protocol"},
        "view_selected_pose": {"pt": "Abrir no PyMOL", "en": "Open in PyMOL"},
        "pose_3d_view": {"pt": "Visualização 3D", "en": "3D View"},
        "compare_button": {"pt": "Comparar", "en": "Compare"},
        "export_filtered_subset": {
            "pt": "Exportar subconjunto filtrado",
            "en": "Export filtered subset",
        },
        "pinned_only": {"pt": "Somente fixadas", "en": "Pinned only"},
        "ligand_name_filter": {"pt": "Nome do ligante", "en": "Ligand name"},
        "scoring_all": {"pt": "Pontuação: todas", "en": "Scoring: all"},
        "select_pose_preview": {
            "pt": "Selecione uma pose para carregar a visualização 3D.",
            "en": "Select a pose to load the 3D preview.",
        },
        "export_interaction_table": {
            "pt": "Exportar tabela de interações",
            "en": "Export interaction table",
        },
        "export_best_cluster": {
            "pt": "Exportar melhor por cluster",
            "en": "Export best per cluster",
        },
        "protein_atom_center": {
            "pt": "Centro por átomo da proteína",
            "en": "Protein atom center",
        },
        "adjust_box_size_ligand": {
            "pt": "Ajustar TAMANHO da caixa (cubo: maior extensão + 1 Å) — centro inalterado",
            "en": "Adjust box SIZE (cube: max extent + 1 Å) — center unchanged",
        },
        "choose_receptor_atom": {
            "pt": "Escolher átomo do receptor como centro da caixa",
            "en": "Choose a receptor atom as box center",
        },
        "load_receptor_atoms": {
            "pt": "Carregar átomos do receptor",
            "en": "Load receptor atoms",
        },
        "snap_selected_atom": {
            "pt": "Centralizar no átomo/resíduo selecionado",
            "en": "Snap to selected atom/residue",
        },
        "snap_crystal_ligand": {
            "pt": "Centro no ligante de referência (co-cristal)",
            "en": "Center on reference ligand (co-crystal)",
        },
        "save_box": {"pt": "Salvar caixa", "en": "Save box"},
        "blind_dock": {"pt": "Modo blind docking (Rg)", "en": "Blind docking (Rg)"},
        "tip_blind_dock": {
            "pt": "Calcula o raio de giração do ligante e define tamanho da caixa = 2*Rg + 2 Å, centralizada no centroide.",
            "en": "Computes the ligand radius of gyration and sets the box size to 2*Rg + 2 Å, centered on the centroid.",
        },
        "tip_snap_atom": {
            "pt": "Use o átomo do receptor selecionado na árvore como centro da caixa.",
            "en": "Use the receptor atom selected in the tree as the box center.",
        },
        "tip_snap_ligand": {
            "pt": "Carregue um ligante PDBQT de referência e defina o centro no centro geométrico.",
            "en": "Load a reference PDBQT ligand and set the center at its geometric centroid.",
        },
        "tip_save_box": {
            "pt": "Salve o centro e o tamanho atuais como predefinição local nomeada.",
            "en": "Save the current center and size as a named local preset.",
        },
        "load_box_preset": {"pt": "Carregar predefinição...", "en": "Load preset..."},
        "tip_load_box": {
            "pt": "Carregue uma predefinição salva da caixa de busca (arquivo JSON).",
            "en": "Load a saved search-box preset (JSON file).",
        },
        "snap_atom_dialog_title": {
            "pt": "Centralizar no átomo selecionado",
            "en": "Center on selected atom",
        },
        "snap_atom_dialog_message": {
            "pt": "Selecione primeiro um átomo ou resíduo do receptor.",
            "en": "Please first select a receptor atom or residue.",
        },
        "load_box_dialog_title": {"pt": "Carregar predefinição", "en": "Load preset"},
        "load_box_failed_message": {
            "pt": "Falha ao ler arquivo: {exc}",
            "en": "Failed to read file: {exc}",
        },
        "load_box_select_label": {
            "pt": "Selecione a predefinição:",
            "en": "Select preset:",
        },
        "load_box_invalid_message": {
            "pt": "Arquivo não contém campos de caixa válidos.",
            "en": "File does not contain valid box fields.",
        },
        "load_box_filter": {
            "pt": "Predefinições JSON (*.json);;Todos os arquivos (*)",
            "en": "JSON presets (*.json);;All files (*)",
        },
        "pre_run_checklist": {
            "pt": "7. Checklist pré-execução",
            "en": "7. Pre-run Checklist",
        },
        "results_table": {"pt": "Tabela de resultados", "en": "Results Table"},
        "interactions": {"pt": "Interações", "en": "Interactions"},
        "consensus": {"pt": "Consenso", "en": "Consensus"},
        "clusters": {"pt": "Clusters", "en": "Clusters"},
        "pose_rank": {"pt": "Rank da pose", "en": "Pose rank"},
        "docking_score": {
            "pt": "Score de docking (kcal/mol)",
            "en": "Docking score (kcal/mol)",
        },
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
        "representative_pose": {
            "pt": "Pose representante",
            "en": "Representative pose",
        },
        "members": {"pt": "Membros", "en": "Members"},
        "mean_rank": {"pt": "Rank médio", "en": "Mean rank"},
        "borda_count": {"pt": "Contagem Borda", "en": "Borda count"},
        "zscore_consensus": {"pt": "Consenso Z-score", "en": "Z-score consensus"},
        "rank_sd": {"pt": "DP dos ranks", "en": "Rank SD"},
        "divergence_flag": {"pt": "Divergência", "en": "Divergence flag"},
        "action_exit": {"pt": "Sair", "en": "Exit"},
        "action_quick_help": {"pt": "Guia rápido", "en": "Quick Guide"},
        "action_show_help_panel": {
            "pt": "Mostrar painel de ajuda",
            "en": "Show Help Panel",
        },
        "lang_portuguese": {"pt": "Português", "en": "Portuguese"},
        "lang_english": {"pt": "Inglês", "en": "English"},
        "converter_title": {
            "pt": "Conversor de Arquivos Moleculares",
            "en": "Molecular File Converter",
        },
        "converter_subtitle": {
            "pt": "AutoDock Vina aceita apenas arquivos .pdbqt como entrada de docking. Converta arquivos .pdb ou .mol2 aqui antes de seguir para a Configuração.",
            "en": "AutoDock Vina accepts only .pdbqt files as docking input. Convert .pdb or .mol2 files here before moving to Setup.",
        },
        "converter_pdbqt_note": {
            "pt": "Atenção: receptor e ligantes usados no docking devem estar no formato .pdbqt.",
            "en": "Note: receptor and ligand files used for docking must be in .pdbqt format.",
        },
        "selected_files": {
            "pt": "{count} arquivo(s) selecionado(s)",
            "en": "{count} file(s) selected",
        },
        "select_input_files": {
            "pt": "Selecionar arquivo(s) moleculares",
            "en": "Select molecular file(s)",
        },
        "output_folder": {"pt": "Pasta de saída", "en": "Output folder"},
        "select_output_folder": {
            "pt": "Selecionar pasta de saída",
            "en": "Select output folder",
        },
        "mol_type_ligand": {"pt": "Ligante", "en": "Ligand"},
        "mol_type_receptor": {"pt": "Receptor (proteína)", "en": "Receptor (protein)"},
        "convert_button": {"pt": "⚙️ Converter para PDBQT", "en": "⚙️ Convert to PDBQT"},
        "use_as_receptor": {
            "pt": "➡️ Usar como receptor no Setup",
            "en": "➡️ Use as receptor in Setup",
        },
        "use_as_ligand": {
            "pt": "➡️ Usar como ligante no Setup",
            "en": "➡️ Use as ligand in Setup",
        },
        "use_as_ligand_batch": {
            "pt": "➡️ Usar pasta de ligantes no Setup",
            "en": "➡️ Use ligand folder in Setup",
        },
        "conv_success": {
            "pt": "✅ Conversão concluída",
            "en": "✅ Conversion complete",
        },
        "conv_failure": {"pt": "❌ Falha na conversão", "en": "❌ Conversion failed"},
        "conv_batch_success": {
            "pt": "✅ {count} arquivo(s) convertido(s)",
            "en": "✅ {count} file(s) converted",
        },
        "conv_batch_partial": {
            "pt": "⚠️ {ok}/{total} arquivo(s) convertido(s)",
            "en": "⚠️ {ok}/{total} file(s) converted",
        },
        "conv_no_input": {
            "pt": "Selecione ao menos um arquivo para converter.",
            "en": "Select at least one file to convert.",
        },
        "conv_receptor_single": {
            "pt": "Para receptor/proteína, selecione um arquivo por conversão.",
            "en": "For receptor/protein, select one file per conversion.",
        },
        "dep_status_title": {
            "pt": "Ferramentas disponíveis:",
            "en": "Available tools:",
        },
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
        "rigid_receptor": {
            "pt": "Receptor rígido (PDBQT)",
            "en": "Rigid receptor (PDBQT)",
        },
        "ligand_label": {"pt": "Ligante(s) (PDBQT)", "en": "Ligand(s) (PDBQT)"},
        "single_ligand": {"pt": "Ligante único", "en": "Single ligand"},
        "single_ligand_file": {
            "pt": "Arquivo do ligante único",
            "en": "Single ligand file",
        },
        "batch_folder": {"pt": "Pasta de triagem", "en": "Screening folder"},
        "batch_mode": {
            "pt": "Modo Triagem (múltiplos ligantes)",
            "en": "Screening mode (multiple ligands)",
        },
        "browse_button": {"pt": "Procurar...", "en": "Browse..."},
        "flexible_receptor": {
            "pt": "Cadeias laterais flexíveis (opcional)",
            "en": "Flexible side chains (optional)",
        },
        "batch_count": {
            "pt": "{count} arquivos PDBQT encontrados",
            "en": "{count} PDBQT files discovered",
        },
        "warn_receptor": {
            "pt": "Selecione um receptor .pdbqt válido.",
            "en": "Select a valid receptor .pdbqt file.",
        },
        "warn_rigid": {
            "pt": "O receptor rígido deve ser um arquivo .pdbqt válido quando informado.",
            "en": "Rigid receptor must be a valid .pdbqt file when provided.",
        },
        "warn_flex": {
            "pt": "As cadeias flexíveis devem ser um arquivo .pdbqt válido quando informadas.",
            "en": "Flexible sidechain file must be a valid .pdbqt file when provided.",
        },
        "warn_ligand": {
            "pt": "Selecione um ligante .pdbqt válido.",
            "en": "Select a valid ligand .pdbqt file.",
        },
        "warn_batch": {
            "pt": "Selecione uma pasta de triagem contendo arquivos .pdbqt.",
            "en": "Select a screening folder containing .pdbqt files.",
        },
        "select_ligand_folder": {
            "pt": "Selecionar pasta de ligantes",
            "en": "Select ligand folder",
        },
        "select_pdbqt": {"pt": "Selecionar arquivo PDBQT", "en": "Select PDBQT file"},
        "pdbqt_filter": {
            "pt": "Arquivos PDBQT (*.pdbqt)",
            "en": "PDBQT files (*.pdbqt)",
        },
        "docking_group": {
            "pt": "5. Parâmetros do AutoDock Vina",
            "en": "5. AutoDock Vina parameters",
        },
        "scoring_label": {"pt": "Função de pontuação", "en": "Scoring function"},
        "scoring_group": {"pt": "3. Função de Pontuação", "en": "3. Scoring Function"},
        "scoring_gnina_warn": {
            "pt": "GNINA não detectado. Sem suporte oficial nativo no Windows; use Linux/WSL ou forneça gnina.exe em tools/gnina ou no PATH.",
            "en": "GNINA not found. No official native Windows support; use Linux/WSL or provide gnina.exe in tools/gnina or PATH.",
        },
        "ref_button": {"pt": "📖 Referência", "en": "📖 Reference"},
        "search_box": {"pt": "4. Caixa de busca (Å)", "en": "4. Search box (Å)"},
        "center_label": {"pt": "Centro (x, y, z)", "en": "Center (x, y, z)"},
        "size_label": {"pt": "Tamanho (x, y, z)", "en": "Size (x, y, z)"},
        "box_preset_custom": {"pt": "Personalizado", "en": "Custom"},
        "box_preset_small_15": {"pt": "Pequena (15x15x15)", "en": "Small (15x15x15)"},
        "box_preset_medium_20": {"pt": "Média (20x20x20)", "en": "Medium (20x20x20)"},
        "box_preset_large_25": {"pt": "Grande (25x25x25)", "en": "Large (25x25x25)"},
        "auto_grid_ligand": {
            "pt": "Ajustar tamanho da caixa pelos ligantes",
            "en": "Adjust box size from ligand bounds",
        },
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
        "energy_range": {
            "pt": "Intervalo de energia (kcal/mol)",
            "en": "Energy range (kcal/mol)",
        },
        "cpu_label": {"pt": "CPUs (0 = automático)", "en": "CPUs (0 = automatic)"},
        "seed_label": {"pt": "Semente aleatória", "en": "Random seed"},
        "fix_seed": {
            "pt": "Fixar semente (reprodutibilidade)",
            "en": "Fix seed (reproducibility)",
        },
        "min_rmsd": {"pt": "RMSD mínimo (Å)", "en": "Minimum RMSD (Å)"},
        "tip_min_rmsd": {
            "pt": "Separação mínima de poses usada para evitar poses quase duplicadas.",
            "en": "Minimum pose separation used to avoid near-duplicate poses.",
        },
        "output_dir": {"pt": "6. Diretório de saída", "en": "6. Output directory"},
        "save_config": {"pt": "Salvar configuração (.txt)", "en": "Save config (.txt)"},
        "load_config": {"pt": "Carregar configuração", "en": "Load config"},
        "run_docking": {"pt": "▶ Executar Docking", "en": "▶ Run Docking"},
        "select_output_dir": {
            "pt": "Selecionar diretório de saída",
            "en": "Select output directory",
        },
        "save_vina_config": {
            "pt": "Salvar configuração Vina",
            "en": "Save Vina config",
        },
        "load_vina_config": {
            "pt": "Carregar configuração Vina",
            "en": "Load Vina config",
        },
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
        "chart_title": {
            "pt": "Distribuição de afinidade",
            "en": "Affinity distribution",
        },
        "export_excel_dialog": {"pt": "Exportar Excel", "en": "Export Excel"},
        "export_csv_dialog": {"pt": "Exportar CSV", "en": "Export CSV"},
        "summary_stats": {"pt": "Estatísticas resumidas", "en": "Summary statistics"},
        "best_affinity": {"pt": "Melhor afinidade", "en": "Best affinity"},
        "mean_affinity": {"pt": "Afinidade média", "en": "Mean affinity"},
        "ligands_docked": {
            "pt": "Número de ligantes dockados",
            "en": "Number of ligands docked",
        },
        "poses_per_ligand": {
            "pt": "Número de poses por ligante",
            "en": "Number of poses per ligand",
        },
        "generate_pdf": {"pt": "Gerar Relatório PDF", "en": "Generate PDF Report"},
        "open_folder": {"pt": "Abrir pasta de saída", "en": "Open output folder"},
        "report_title": {
            "pt": "Relatório de Docking VinaLab",
            "en": "VinaLab Docking Report",
        },
        "parameters": {"pt": "Parâmetros", "en": "Parameters"},
        "results": {"pt": "Resultados", "en": "Results"},
        "affinity_chart": {"pt": "Gráfico de afinidade", "en": "Affinity chart"},
        "no_results": {
            "pt": "Não há resultados de docking para relatar.",
            "en": "No docking results are available for reporting.",
        },
        "missing_output_folder": {
            "pt": "Selecione ou crie uma pasta de saída primeiro.",
            "en": "Select or create an output folder first.",
        },
        "env_ready": {
            "pt": "✅ Ambiente pronto — VinaLab operacional",
            "en": "✅ Environment ready — VinaLab fully operational",
        },
        "env_checking": {
            "pt": "⚙️ Verificando ambiente...",
            "en": "⚙️ Checking environment...",
        },
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
        "tip_cpu": {
            "pt": "Use 0 para seleção automática de CPUs.",
            "en": "Use 0 for automatic CPU selection.",
        },
        "tip_output": {
            "pt": "Pasta onde poses, tabelas e relatórios serão salvos.",
            "en": "Folder where poses, tables, and reports are saved.",
        },
        "error_title": {"pt": "Erro", "en": "Error"},
        "warning_title": {"pt": "Aviso", "en": "Warning"},
        "success_title": {"pt": "Concluído", "en": "Done"},
        "confirm_cancel": {
            "pt": "Cancelar o docking em andamento?",
            "en": "Cancel the ongoing docking run?",
        },
        "docking_running": {"pt": "Docking em execução", "en": "Docking running"},
        "docking_running_msg": {
            "pt": "O docking já está em execução.",
            "en": "Docking is already running.",
        },
        "invalid_setup": {"pt": "Configuração inválida", "en": "Invalid setup"},
        "invalid_setup_msg": {
            "pt": "Corrija as entradas antes de executar o docking.",
            "en": "Fix setup inputs before running docking.",
        },
        "missing_output": {
            "pt": "Diretório de saída ausente",
            "en": "Missing output directory",
        },
        "missing_output_msg": {
            "pt": "Selecione um diretório de saída.",
            "en": "Select an output directory.",
        },
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
            "pt": "No modo triagem, a pasta selecionada é varrida recursivamente e cada PDBQT é processado em sequência.",
            "en": "In screening mode, the selected folder is scanned recursively and each PDBQT is processed sequentially.",
        },
        "welcome_title": {"pt": "Bem-vindo ao VinaLab", "en": "Welcome to VinaLab"},
        "welcome_body": {
            "pt": "Interface gráfica para AutoDock Vina com instalação de ambiente, execução em triagem e relatórios.",
            "en": "Graphical interface for AutoDock Vina with environment setup, screening execution, and reports.",
        },
        "get_started": {"pt": "Começar", "en": "Get started"},
        "about_title": {"pt": "Sobre o VinaLab", "en": "About VinaLab"},
        "version_label": {"pt": "Versão 0.0.2", "en": "Version 0.0.2"},
        "license_label": {"pt": "Licença: Apache 2.0", "en": "License: Apache 2.0"},
        "vina_citation": {
            "pt": "Citação AutoDock Vina",
            "en": "AutoDock Vina citation",
        },
        "pdf_footer": {
            "pt": "Gerado por VinaLab v0.0.2 | Adriano Marques Gonçalves — UNIARA | {date}",
            "en": "Generated by VinaLab v0.0.2 | Adriano Marques Gonçalves — UNIARA | {date}",
        },
        "dt_box_size_preset_label": {
            "pt": "Predefinição de tamanho",
            "en": "Size preset",
        },
        "dt_box_presets_label": {"pt": "Predefinições da caixa", "en": "Box presets"},
        "dt_blind_need_ligand": {
            "pt": "Selecione ao menos um ligante antes de calcular o blind docking.",
            "en": "Select at least one ligand before computing blind docking.",
        },
        "dt_ligand_coords_unreadable": {
            "pt": "Não foi possível ler coordenadas do(s) ligante(s).",
            "en": "Could not read ligand coordinate(s).",
        },
        "dt_blind_result": {
            "pt": "Blind docking: Rg = {rg:.2f} Å, lado da caixa = {side:.2f} Å, centroide ({cx:.3f}, {cy:.3f}, {cz:.3f}).",
            "en": "Blind docking: Rg = {rg:.2f} Å, box side = {side:.2f} Å, centroid ({cx:.3f}, {cy:.3f}, {cz:.3f}).",
        },
        "dt_grid_result": {
            "pt": "Centro da caixa de busca mantido. Maior extensão do ligante: {extent:.2f} Å. Lado da caixa (cubo) definido em {side:.2f} Å (maior extensão + 1 Å).",
            "en": "Search-box center kept. Largest ligand extent: {extent:.2f} Å. Box side (cube) set to {side:.2f} Å (largest extent + 1 Å).",
        },
        "dt_ref_ligand_title": {
            "pt": "Ligante de referência (co-cristal)",
            "en": "Reference ligand (co-crystal)",
        },
        "dt_crystal_ligand_title": {
            "pt": "Ligante cristalográfico",
            "en": "Crystallographic ligand",
        },
        "dt_ligand_coords_fail": {
            "pt": "Não foi possível ler as coordenadas do ligante.",
            "en": "Could not read the ligand coordinates.",
        },
        "dt_save_box_title": {"pt": "Salvar caixa", "en": "Save box"},
        "dt_save_box_prompt": {"pt": "Nome da predefinição", "en": "Preset name"},
        "dt_checklist_dialog_title": {
            "pt": "Checklist pré-execução",
            "en": "Pre-run checklist",
        },
        "dt_ref_crystal_pose_title": {
            "pt": "Pose cristalográfica de referência",
            "en": "Reference crystallographic pose",
        },
        "dt_validate_protocol_title": {
            "pt": "Validar protocolo",
            "en": "Validate protocol",
        },
        "dt_topn_prompt": {
            "pt": "Corte de sucesso Top-N",
            "en": "Top-N success cutoff",
        },
        "dt_validation_start": {
            "pt": "Iniciando redocking de validação do protocolo em {path}.",
            "en": "Starting protocol validation redocking in {path}.",
        },
        "dt_validation_parsed": {
            "pt": "Validação do protocolo interpretou {count} pose(s).",
            "en": "Protocol validation parsed {count} pose(s).",
        },
        "dt_check_receptor_msg": {
            "pt": "Arquivo do receptor carregado e interpretável",
            "en": "Receptor file loaded and parseable",
        },
        "dt_check_receptor_detail": {
            "pt": "Selecione um arquivo de receptor .pdbqt válido.",
            "en": "Select a valid .pdbqt receptor file.",
        },
        "dt_check_ligand_msg": {
            "pt": "Arquivo do ligante carregado e interpretável",
            "en": "Ligand file loaded and parseable",
        },
        "dt_check_ligand_detail": {
            "pt": "Selecione um arquivo de ligante .pdbqt válido ou uma pasta contendo arquivos .pdbqt.",
            "en": "Select a valid .pdbqt ligand file or a folder containing .pdbqt files.",
        },
        "dt_check_overlap_unavailable_msg": {
            "pt": "Sobreposição ligante/caixa indisponível",
            "en": "Ligand/box overlap unavailable",
        },
        "dt_check_overlap_unavailable_detail": {
            "pt": "Carregue as coordenadas do ligante antes de verificar a sobreposição com a grade.",
            "en": "Load the ligand coordinates before checking grid overlap.",
        },
        "dt_check_overlap_ok_msg": {
            "pt": "Coordenadas do ligante sobrepõem a caixa de busca",
            "en": "Ligand coordinates overlap the search box",
        },
        "dt_check_overlap_ok_detail": {
            "pt": "Os limites do ligante sobrepõem a grade atual do Vina.",
            "en": "The ligand bounds overlap the current Vina grid.",
        },
        "dt_check_overlap_fail_msg": {
            "pt": "Coordenadas do ligante não sobrepõem a caixa de busca",
            "en": "Ligand coordinates do not overlap the search box",
        },
        "dt_check_overlap_fail_detail": {
            "pt": "Mova ou redimensione a caixa de busca para que as coordenadas do ligante sobreponham a grade.",
            "en": "Move or resize the search box so the ligand coordinates overlap the grid.",
        },
        "dt_check_obabel_msg": {
            "pt": "OpenBabel disponível",
            "en": "OpenBabel available",
        },
        "dt_check_obabel_detail": {
            "pt": "Instale o OpenBabel ou execute o inicializador para reparar o suporte de conversão.",
            "en": "Install OpenBabel or run the launcher to repair conversion support.",
        },
        "dt_check_scoring_msg": {"pt": "Pontuação {label}", "en": "Scoring {label}"},
        "dt_check_scoring_disabled_msg": {
            "pt": "Pontuação {label} desativada",
            "en": "Scoring {label} disabled",
        },
        "dt_check_scoring_ok_detail": {
            "pt": "Função de pontuação selecionada disponível.",
            "en": "Selected scoring function available.",
        },
        "dt_scoring_dep_missing": {
            "pt": "Dependência opcional de pontuação ausente.",
            "en": "Optional scoring dependency missing.",
        },
        "dt_scoring_archive_missing": {
            "pt": "Arquivo de pontuação não encontrado em pontuacao/.",
            "en": "Scoring archive not found in pontuacao/.",
        },
        "dt_check_vina_msg": {
            "pt": "Executável Vina encontrado",
            "en": "Vina executable found",
        },
        "dt_check_vina_detail": {
            "pt": "Execute o inicializador para instalar o Vina ou restaurar o fallback CLI incluído.",
            "en": "Run the launcher to install Vina or restore the bundled CLI fallback.",
        },
        "dt_status_unavailable": {
            "pt": "{description}\nStatus: indisponível - {reason}",
            "en": "{description}\nStatus: unavailable - {reason}",
        },
        "dt_status_available": {
            "pt": "{description}\nStatus: disponível",
            "en": "{description}\nStatus: available",
        },
        "dt_select_receptor_first": {
            "pt": "Selecione primeiro um arquivo PDBQT do receptor.",
            "en": "Select a receptor PDBQT file first.",
        },
        "dt_no_receptor_atoms": {
            "pt": "Nenhum átomo do receptor pôde ser lido do arquivo PDBQT.",
            "en": "No receptor atoms could be read from the PDBQT file.",
        },
        "dt_atoms_loaded": {
            "pt": "Carregados {count} átomos em {residues} resíduos de {name}.",
            "en": "Loaded {count} atoms across {residues} residues from {name}.",
        },
        "dt_center_set": {
            "pt": "Centro definido para {res} {chain}{num} {atom} ({x:.3f}, {y:.3f}, {z:.3f}).",
            "en": "Center set to {res} {chain}{num} {atom} ({x:.3f}, {y:.3f}, {z:.3f}).",
        },
        "dt_dep_checking": {
            "pt": "Dependências: verificando - execute o inicializador se um pacote obrigatório estiver ausente.",
            "en": "Dependencies: checking - run the launcher if a required package is missing.",
        },
        "dt_dep_red": {
            "pt": "Dependências: vermelho - runtime obrigatório ausente. Use Corrigir agora na barra de status.",
            "en": "Dependencies: red - required runtime missing. Use Fix now in the status bar.",
        },
        "dt_dep_yellow": {
            "pt": "Dependências: amarelo - docking principal pronto; pontuação desativada: ",
            "en": "Dependencies: yellow - core docking ready; scoring disabled: ",
        },
        "dt_dep_green": {
            "pt": "Dependências: verde - docking e runtimes opcionais de pontuação prontos.",
            "en": "Dependencies: green - docking and optional scoring runtimes ready.",
        },
        "mw_bundled_runtime_title": {"pt": "Runtime incluído", "en": "Bundled runtime"},
        "mw_bundled_runtime_msg": {
            "pt": "Esta instalação do VinaLab já inclui o runtime obrigatório. Dependências opcionais de pontuação podem ser instaladas separadamente.",
            "en": "This VinaLab installation already includes the required runtime. Optional scoring dependencies can be installed separately.",
        },
        "mw_pdb_ready": {
            "pt": "PDB preparado pronto para conversão: {name}",
            "en": "Prepared PDB ready for conversion: {name}",
        },
        "setup_rigid_tooltip": {
            "pt": "Ao usar receptor flexível, a parte rígida deve ser fornecida separadamente como PDBQT contendo todos os resíduos NÃO flexíveis. Se nenhum resíduo flexível for definido, use apenas o receptor principal e deixe este campo vazio.",
            "en": "When using a flexible receptor, the rigid part must be provided separately as a PDBQT containing all NON-flexible residues. If no flexible residue is defined, use only the main receptor and leave this field empty.",
        },
        "setup_flex_tooltip": {
            "pt": "PDBQT contendo a árvore de torsões (ROOT/ENDROOT/BRANCH) gerada por meeko ou prepare_flexreceptor4.py. Exemplo: flex_residues.pdbqt. Formato de seleção de resíduos: CHAIN:RESNAME:RESNUM (por exemplo, A:TYR:48,A:PHE:49).",
            "en": "PDBQT containing the torsion tree (ROOT/ENDROOT/BRANCH) generated by meeko or prepare_flexreceptor4.py. Example: flex_residues.pdbqt. Residue selection format: CHAIN:RESNAME:RESNUM (e.g., A:TYR:48,A:PHE:49).",
        },
        "rd_compare_title": {"pt": "Comparar poses", "en": "Compare poses"},
        "rd_mode_crystal": {"pt": "Pose vs cristal", "en": "Pose vs crystal"},
        "rd_mode_scoring": {
            "pt": "Comparação de pontuação",
            "en": "Scoring comparison",
        },
        "rd_run_compare": {"pt": "Executar comparação", "en": "Run comparison"},
        "rd_reference": {"pt": "Referência", "en": "Reference"},
        "rd_webengine_missing": {
            "pt": "PySide6-WebEngine está indisponível.",
            "en": "PySide6-WebEngine is unavailable.",
        },
        "rd_reference_pose_title": {"pt": "Pose de referência", "en": "Reference pose"},
        "rd_rmsd_not_comparable_status": {
            "pt": "RMSD: não comparável",
            "en": "RMSD: not comparable",
        },
        "rd_pose_comparison_title": {
            "pt": "Comparação de poses",
            "en": "Pose comparison",
        },
        "rd_not_comparable": {"pt": "não comparável", "en": "not comparable"},
        "rd_choose_reference_pdbqt": {
            "pt": "Escolha um arquivo .pdbqt de referência.",
            "en": "Choose a reference .pdbqt file.",
        },
        "rd_best_rmsd_not_comparable": {
            "pt": "Melhor RMSD para cristal: não comparável",
            "en": "Best RMSD to crystal: not comparable",
        },
        "rd_scoring_func_col": {"pt": "Função de pontuação", "en": "Scoring function"},
        "rd_scoring_compare_status": {
            "pt": "Comparação de pontuação para a pose selecionada.",
            "en": "Scoring comparison for the selected pose.",
        },
        "rd_title_pose_pair": {
            "pt": "Pose A vs Pose B | RMSD {rmsd:.3f} Å",
            "en": "Pose A vs Pose B | RMSD {rmsd:.3f} Å",
        },
        "rd_title_pose_vs_crystal_best": {
            "pt": "Pose vs cristal | melhor RMSD {rmsd:.3f} Å",
            "en": "Pose vs crystal | best RMSD {rmsd:.3f} Å",
        },
        "rd_rmsd_value": {
            "pt": "RMSD: {rmsd:.3f} Å",
            "en": "RMSD: {rmsd:.3f} Å",
        },
        "rd_best_rmsd_value": {
            "pt": "Melhor RMSD para cristal: {rmsd:.3f} Å",
            "en": "Best RMSD to crystal: {rmsd:.3f} Å",
        },
        "rd_export_validation": {
            "pt": "Exportar relatório de validação",
            "en": "Export validation report",
        },
        "rd_col_pose_rank": {"pt": "rank_da_pose", "en": "pose_rank"},
        "rd_col_score": {"pt": "score", "en": "score"},
        "rd_col_rmsd_crystal": {"pt": "RMSD_para_cristal", "en": "rmsd_to_crystal"},
        "rd_col_within_2a": {"pt": "dentro_de_2A", "en": "within_2A"},
        "rd_within_yes": {"pt": "sim", "en": "yes"},
        "rd_within_no": {"pt": "não", "en": "no"},
        "rd_within_na": {"pt": "n/d", "en": "n/a"},
        "rd_no_validation_poses": {
            "pt": "Nenhuma pose de validação disponível.",
            "en": "No validation poses available.",
        },
        "rd_no_comparable_summary": {
            "pt": "Nenhuma pose pôde ser comparada à referência ({count} pose(s) com composição atômica incompatível). Verifique se a pose e o cristal são a mesma molécula e foram preparados com o mesmo esquema de protonação/átomos.",
            "en": "No pose could be compared to the reference ({count} pose(s) with incompatible atomic composition). Check that the pose and the crystal are the same molecule and were prepared with the same protonation/atom scheme.",
        },
        "rd_incomparable_suffix": {
            "pt": " | {count} pose(s) não comparável(eis) excluída(s)",
            "en": " | {count} non-comparable pose(s) excluded",
        },
        "rd_csv_filter": {"pt": "Arquivos CSV (*.csv)", "en": "CSV files (*.csv)"},
        "rd_export_selected": {
            "pt": "Exportar apenas o complexo selecionado",
            "en": "Export only the selected complex",
        },
        "rd_export_all": {
            "pt": "Exportar todos os complexos",
            "en": "Export all complexes",
        },
        "rd_export_btn": {"pt": "Exportar", "en": "Export"},
        "rd_topn_per_ligand": {
            "pt": "Top N poses por ligante",
            "en": "Top N poses per ligand",
        },
        "rd_format_label": {"pt": "Formato", "en": "Format"},
        "rd_choose_output_folder": {
            "pt": "Escolha uma pasta de saída.",
            "en": "Choose an output folder.",
        },
        "rd_no_pose_selected": {
            "pt": "Nenhuma pose está selecionada no momento.",
            "en": "No pose is currently selected.",
        },
        "rd_obabel_missing_export": {
            "pt": "OpenBabel não encontrado. Instale-o para exportar arquivos .pdb ou .mol2.",
            "en": "OpenBabel not found. Install it to export .pdb or .mol2 files.",
        },
        "rd_exported_count": {
            "pt": "{count} arquivo(s) exportado(s) para {directory}.",
            "en": "{count} file(s) exported to {directory}.",
        },
        "rd_obabel_conv_fail": {
            "pt": "Falha na conversão com OpenBabel.",
            "en": "OpenBabel conversion failed.",
        },
        "rt_no_poses_export": {
            "pt": "Não há poses de docking disponíveis para exportar.",
            "en": "No docking poses available to export.",
        },
        "rt_no_poses_compare": {
            "pt": "Não há poses de docking disponíveis para comparar.",
            "en": "No docking poses available to compare.",
        },
        "rt_view_pose_title": {"pt": "Visualizar pose", "en": "View pose"},
        "rt_select_pose": {
            "pt": "Selecione uma pose de docking na tabela de resultados.",
            "en": "Select a docking pose in the results table.",
        },
        "rt_pymol_not_found": {
            "pt": "PyMOL não foi encontrado no PATH do sistema.\nInstale o PyMOL e certifique-se de que está acessível via linha de comando.",
            "en": "PyMOL was not found on the system PATH.\nInstall PyMOL and ensure it is accessible from the command line.",
        },
        "rt_pymol_open_error": {
            "pt": "Erro ao abrir pose no PyMOL.\n{exc}",
            "en": "Error opening pose in PyMOL.\n{exc}",
        },
        "rt_validation_no_poses": {
            "pt": "O docking de validação não produziu poses.",
            "en": "Validation docking produced no poses.",
        },
        "rt_no_visible_rows": {
            "pt": "Não há linhas visíveis para exportar.",
            "en": "No visible rows to export.",
        },
        "rt_no_interactions": {
            "pt": "Não há interações disponíveis para a pose selecionada.",
            "en": "No interactions available for the selected pose.",
        },
        "rt_no_clusters_export": {
            "pt": "Não há clusters disponíveis para exportar.",
            "en": "No clusters available to export.",
        },
        "rt_cluster_exported": {
            "pt": "{count} pose(s) representativa(s) exportada(s) para {directory}.",
            "en": "{count} representative pose(s) exported to {directory}.",
        },
        "rt_tip_export_filtered": {
            "pt": "Exporta apenas as linhas visíveis no momento.",
            "en": "Exports only the currently visible rows.",
        },
        "rt_tip_compare": {
            "pt": "Compara poses, referências cristalográficas ou funções de pontuação.",
            "en": "Compares poses, crystallographic references, or scoring functions.",
        },
        "rt_tip_export_interactions": {
            "pt": "Exporta as interações da pose selecionada como CSV.",
            "en": "Exports the selected pose interactions as CSV.",
        },
        "rt_tip_view_pymol": {
            "pt": "Abre o complexo receptor-pose selecionado no PyMOL.",
            "en": "Opens the selected receptor-pose complex in PyMOL.",
        },
        "rt_tip_export_complex": {
            "pt": "Exporta complexos de docking selecionados ou filtrados.",
            "en": "Exports selected or filtered docking complexes.",
        },
        "rt_tip_cluster_export": {
            "pt": "Exporta poses representativas de cada cluster por RMSD.",
            "en": "Exports the representative pose of each RMSD cluster.",
        },
        "rt_consensus_hint": {
            "pt": "O ranking de consenso fica disponível após a conclusão de 2 ou mais funções de pontuação.",
            "en": "Consensus ranking becomes available after 2 or more scoring functions complete.",
        },
        "rt_export_this_pose": {"pt": "Exportar esta pose", "en": "Export this pose"},
        "rt_exported_to": {
            "pt": "Exportado para {path}.",
            "en": "Exported to {path}.",
        },
        "rt_pose_export_filter": {
            "pt": "PDBQT (*.pdbqt);;PDB (*.pdb);;MOL2 (*.mol2)",
            "en": "PDBQT (*.pdbqt);;PDB (*.pdb);;MOL2 (*.mol2)",
        },
        "pp_prepare_title": {"pt": "Preparar proteína", "en": "Prepare protein"},
        "pp_select_valid_pdb": {
            "pt": "Selecione um arquivo PDB válido antes de prosseguir.",
            "en": "Select a valid PDB file before continuing.",
        },
        "pp_define_output": {
            "pt": "Defina o arquivo de saída.",
            "en": "Set the output file.",
        },
        "pp_read_fail": {
            "pt": "Falha ao ler PDB: {exc}",
            "en": "Failed to read PDB: {exc}",
        },
        "pp_save_fail": {"pt": "Falha ao salvar: {exc}", "en": "Failed to save: {exc}"},
        "pp_add_h_title": {"pt": "Adicionar hidrogênios", "en": "Add hydrogens"},
        "pp_obabel_missing": {
            "pt": "Open Babel não encontrado. Instale obabel ou use H++/Reduce externamente. Funcionalidade indisponível neste ambiente.",
            "en": "Open Babel not found. Install obabel or use H++/Reduce externally. Feature unavailable in this environment.",
        },
        "pp_obabel_run_fail": {
            "pt": "Falha ao executar Open Babel: {exc}",
            "en": "Failed to run Open Babel: {exc}",
        },
        "rp_report_title": {
            "pt": "Relatório completo de docking VinaLab",
            "en": "VinaLab full docking report",
        },
        "rp_section_params": {
            "pt": "1. Parâmetros de docking",
            "en": "1. Docking parameters",
        },
        "rp_section_results": {
            "pt": "2. Tabela de resultados",
            "en": "2. Results table",
        },
        "rp_section_consensus": {
            "pt": "3. Ranking de consenso",
            "en": "3. Consensus ranking",
        },
        "rp_section_clusters": {
            "pt": "4. Resumo de clusters",
            "en": "4. Cluster summary",
        },
        "rp_section_interactions": {
            "pt": "5. Resumo de interações",
            "en": "5. Interaction summary",
        },
        "rp_section_errors": {
            "pt": "6. Erros e avisos",
            "en": "6. Errors and warnings",
        },
        "rp_pdf_filter": {"pt": "Arquivos PDF (*.pdf)", "en": "PDF files (*.pdf)"},
        "rp_consensus_need_two": {
            "pt": "O consenso requer pelo menos duas funções de pontuação.",
            "en": "Consensus requires at least two scoring functions.",
        },
        "rp_col_ligand": {"pt": "Ligante", "en": "Ligand"},
        "rp_col_pose": {"pt": "Pose", "en": "Pose"},
        "rp_col_docking_score": {"pt": "Score de docking", "en": "Docking score"},
        "rp_col_mean_rank": {"pt": "Rank médio", "en": "Mean rank"},
        "rp_col_borda": {"pt": "Borda", "en": "Borda"},
        "rp_col_zscore": {"pt": "Z-score", "en": "Z-score"},
        "rp_col_divergence": {"pt": "Divergência", "en": "Divergence"},
        "rp_no_clusters": {
            "pt": "Nenhum resumo de clusters disponível ainda. Abra a aba Clusters após o docking para preencher esta seção.",
            "en": "No cluster summary available yet. Open the Clusters tab after docking to populate this section.",
        },
        "rp_col_cluster_id": {"pt": "ID do cluster", "en": "Cluster ID"},
        "rp_col_size": {"pt": "Tamanho", "en": "Size"},
        "rp_col_representative": {
            "pt": "Pose representante",
            "en": "Representative pose",
        },
        "rp_col_best_score": {"pt": "Melhor score", "en": "Best score"},
        "rp_interactions_provider_missing": {
            "pt": "Provedor de interações indisponível.",
            "en": "Interaction provider unavailable.",
        },
        "rp_interaction_helpers_missing": {
            "pt": "Auxiliares de interação indisponíveis.",
            "en": "Interaction helpers unavailable.",
        },
        "rp_col_top_residues": {
            "pt": "Principais resíduos por frequência de contato",
            "en": "Top residues by contact frequency",
        },
        "rp_no_contacts": {
            "pt": "Nenhum contato detectado",
            "en": "No contact detected",
        },
        "rp_skipped": {"pt": "Ignorado: {exc}", "en": "Skipped: {exc}"},
        "rp_col_type": {"pt": "Tipo", "en": "Type"},
        "rp_col_message": {"pt": "Mensagem", "en": "Message"},
        "rp_scoring": {"pt": "Pontuação", "en": "Scoring"},
        "rp_none": {"pt": "Nenhum", "en": "None"},
        "rp_no_scoring_errors": {
            "pt": "Nenhum erro de pontuação registrado nos resultados atuais.",
            "en": "No scoring errors recorded in the current results.",
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
        path.write_text(
            json.dumps(prefs, indent=2, ensure_ascii=False), encoding="utf-8"
        )
