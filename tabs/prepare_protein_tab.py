# -*- coding: utf-8 -*-
"""Protein preparation tab: load PDB, strip ligands, select chain, optional H addition stub."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.file_utils import hetatm_residue_counts, hetatm_residue_lines
from core.i18n import I18n
from core.scrolling import ScrollManager


class PrepareProteinTab(QWidget):
    """Tab for basic protein preparation operations (UI-only stubs for protonation)."""

    receptor_prepared = Signal(str)

    def __init__(self) -> None:
        """Build prepare-protein controls."""
        super().__init__()
        self.lang = "pt"
        self.input_path: Path | None = None

        self.title_label = QLabel()
        self.input_label = QLabel()
        self.input_edit = QLineEdit()
        self.input_edit.setReadOnly(True)
        self.load_button = QPushButton()

        self.strip_group = QGroupBox()
        self.strip_checkbox = QCheckBox()
        self.keep_residues_label = QLabel()
        self.keep_residues_edit = QLineEdit()
        self.keep_residues_edit.setPlaceholderText("HEM, MG, ZN")

        self.chain_group = QGroupBox()
        self.chain_label = QLabel()
        self.chain_combo = QComboBox()
        self.chain_combo.addItem("(todas)")

        self.ligand_group = QGroupBox()
        self.ligand_label = QLabel()
        self.ligand_combo = QComboBox()
        self.extract_button = QPushButton()
        self.extract_button.setEnabled(False)

        self.proton_group = QGroupBox()
        self.proton_checkbox = QCheckBox()
        self.proton_note = QLabel()
        self.proton_note.setWordWrap(True)

        self.output_label = QLabel()
        self.output_edit = QLineEdit()
        self.output_edit.setReadOnly(True)
        self.output_button = QPushButton()

        self.run_button = QPushButton()
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)

        self._build_ui()
        self._connect_signals()
        self.retranslate_ui(self.lang)

    def retranslate_ui(self, lang: str) -> None:
        """Apply PT-BR/EN labels."""
        self.lang = lang
        is_pt = lang == "pt"
        self.title_label.setText("Preparar Proteína" if is_pt else "Prepare Protein")
        self.input_label.setText("Arquivo PDB:" if is_pt else "PDB file:")
        self.load_button.setText("Carregar PDB..." if is_pt else "Load PDB...")
        self.strip_group.setTitle(
            "Remoção de ligantes (HETATM)" if is_pt else "Strip ligands (HETATM)"
        )
        self.strip_checkbox.setText(
            "Remover registros HETATM" if is_pt else "Remove HETATM records"
        )
        self.keep_residues_label.setText(
            "Manter resíduos (vírgula):" if is_pt else "Keep residues (comma):"
        )
        self.chain_group.setTitle("Seleção de cadeia" if is_pt else "Chain selection")
        self.chain_label.setText("Cadeia:" if is_pt else "Chain:")
        self.ligand_group.setTitle(
            "Ligante co-cristalizado" if is_pt else "Co-crystallized ligand"
        )
        self.ligand_label.setText("Resíduo HETATM:" if is_pt else "HETATM residue:")
        self.extract_button.setText(
            "Extrair ligante..." if is_pt else "Extract ligand..."
        )
        self.proton_group.setTitle("Protonação" if is_pt else "Protonation")
        self.proton_checkbox.setText(
            "Adicionar hidrogênios" if is_pt else "Add hydrogens"
        )
        self.proton_note.setText(
            "Nota: ferramentas externas (H++ ou Reduce) podem ser necessárias para protonação completa."
            if is_pt
            else "Note: external tools (H++ or Reduce) may be needed for full protonation."
        )
        self.output_label.setText("Arquivo de saída:" if is_pt else "Output file:")
        self.output_button.setText("Procurar..." if is_pt else "Browse...")
        self.run_button.setText("Preparar e salvar" if is_pt else "Prepare and save")

    def _build_ui(self) -> None:
        """Lay out the tab inside a scroll area."""
        outer = QVBoxLayout(self)
        content = QWidget()
        layout = QVBoxLayout(content)

        layout.addWidget(self.title_label)

        input_row = QHBoxLayout()
        input_row.addWidget(self.input_label)
        input_row.addWidget(self.input_edit)
        input_row.addWidget(self.load_button)
        layout.addLayout(input_row)

        strip_layout = QVBoxLayout(self.strip_group)
        strip_layout.addWidget(self.strip_checkbox)
        keep_row = QHBoxLayout()
        keep_row.addWidget(self.keep_residues_label)
        keep_row.addWidget(self.keep_residues_edit)
        strip_layout.addLayout(keep_row)
        layout.addWidget(self.strip_group)

        chain_layout = QHBoxLayout(self.chain_group)
        chain_layout.addWidget(self.chain_label)
        chain_layout.addWidget(self.chain_combo)
        chain_layout.addStretch()
        layout.addWidget(self.chain_group)

        ligand_layout = QHBoxLayout(self.ligand_group)
        ligand_layout.addWidget(self.ligand_label)
        ligand_layout.addWidget(self.ligand_combo, stretch=1)
        ligand_layout.addWidget(self.extract_button)
        layout.addWidget(self.ligand_group)

        proton_layout = QVBoxLayout(self.proton_group)
        proton_layout.addWidget(self.proton_checkbox)
        proton_layout.addWidget(self.proton_note)
        layout.addWidget(self.proton_group)

        output_row = QHBoxLayout()
        output_row.addWidget(self.output_label)
        output_row.addWidget(self.output_edit)
        output_row.addWidget(self.output_button)
        layout.addLayout(output_row)

        layout.addWidget(self.run_button)
        layout.addWidget(self.log_console)
        layout.addStretch()

        outer.addWidget(ScrollManager.wrap(content))

    def _connect_signals(self) -> None:
        """Wire button clicks."""
        self.load_button.clicked.connect(self._pick_input)
        self.output_button.clicked.connect(self._pick_output)
        self.run_button.clicked.connect(self._run_preparation)
        self.extract_button.clicked.connect(self._extract_ligand)

    def _pick_input(self) -> None:
        """Open a native file dialog for PDB selection."""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar PDB" if self.lang == "pt" else "Select PDB",
            "",
            "PDB (*.pdb);;Todos os arquivos (*)",
        )
        if not file_name:
            return
        self.input_path = Path(file_name)
        self.input_edit.setText(str(self.input_path))
        self._populate_chains()
        self._populate_ligands()
        self._suggest_output()

    def _pick_output(self) -> None:
        """Pick the prepared-PDB output path."""
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar PDB preparado" if self.lang == "pt" else "Save prepared PDB",
            "",
            "PDB (*.pdb)",
        )
        if file_name:
            self.output_edit.setText(str(Path(file_name)))

    def _suggest_output(self) -> None:
        """Suggest an output path next to the input file."""
        if not self.input_path:
            return
        suggestion = self.input_path.with_name(f"{self.input_path.stem}_prep.pdb")
        self.output_edit.setText(str(suggestion))

    def _populate_chains(self) -> None:
        """Parse chain IDs from the input PDB and fill the combo box."""
        self.chain_combo.clear()
        self.chain_combo.addItem("(todas)" if self.lang == "pt" else "(all)")
        if not self.input_path or not self.input_path.exists():
            return
        try:
            text = self.input_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            self.log_console.append(f"Erro ao ler PDB: {exc}")
            return
        chains: list[str] = []
        for line in text.splitlines():
            if not line.startswith(("ATOM", "HETATM")):
                continue
            if len(line) <= 21:
                continue
            chain_id = line[21].strip()
            if chain_id and chain_id not in chains:
                chains.append(chain_id)
        for chain_id in chains:
            self.chain_combo.addItem(chain_id)
        self.log_console.append(
            f"{len(chains)} cadeia(s) detectada(s): {', '.join(chains) or '—'}"
        )

    def _populate_ligands(self) -> None:
        """List HETATM residues so a co-crystal ligand can be extracted as its own PDB.

        Waters are skipped; everything else (inhibitors, cofactors, cryoprotectants
        such as GOL) is offered with its atom count so the real ligand is obvious.
        """
        self.ligand_combo.clear()
        if not self.input_path or not self.input_path.exists():
            return
        try:
            text = self.input_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            self.log_console.append(f"Erro ao ler PDB: {exc}")
            return
        counts = hetatm_residue_counts(text)
        for (resname, chain, resseq), atom_count in sorted(counts.items()):
            label = f"{resname} {chain}{resseq} ({atom_count} átomos)"
            self.ligand_combo.addItem(label, (resname, chain, resseq))
        self.extract_button.setEnabled(bool(counts))
        self.log_console.append(
            f"{len(counts)} ligante(s) HETATM detectado(s)."
            if counts
            else "Nenhum ligante HETATM encontrado (fora águas)."
        )

    def _extract_ligand(self) -> None:
        """Write the selected HETATM residue to its own PDB file."""
        selection = self.ligand_combo.currentData()
        if not self.input_path or selection is None:
            QMessageBox.warning(
                self,
                I18n.get("pp_prepare_title", self.lang),
                "Carregue um PDB e selecione um resíduo HETATM."
                if self.lang == "pt"
                else "Load a PDB and select a HETATM residue.",
            )
            return
        resname, chain, resseq = selection
        suggested = self.input_path.with_name(
            f"{self.input_path.stem}_{resname}_{chain or 'X'}{resseq}.pdb"
        )
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar ligante extraído" if self.lang == "pt" else "Save extracted ligand",
            str(suggested),
            "PDB (*.pdb)",
        )
        if not file_name:
            return
        lines = hetatm_residue_lines(
            self.input_path.read_text(encoding="utf-8", errors="replace"),
            (resname, chain, resseq),
        )
        output_path = Path(file_name)
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text("\n".join(lines + ["END"]) + "\n", encoding="utf-8")
        except OSError as exc:
            QMessageBox.warning(
                self,
                I18n.get("pp_prepare_title", self.lang),
                I18n.get("pp_save_fail", self.lang).format(exc=exc),
            )
            return
        self.log_console.append(
            f"Ligante {resname} {chain}{resseq} ({len(lines)} átomos) salvo em {output_path}. "
            "Converta-o na aba Conversor para usá-lo como ligante de referência da caixa."
        )

    def _run_preparation(self) -> None:
        """Strip HETATM, filter chain, and write the prepared PDB. Protonation stays a stub."""
        if not self.input_path or not self.input_path.exists():
            QMessageBox.warning(
                self,
                I18n.get("pp_prepare_title", self.lang),
                I18n.get("pp_select_valid_pdb", self.lang),
            )
            return
        output_text = self.output_edit.text().strip()
        if not output_text:
            QMessageBox.warning(
                self,
                I18n.get("pp_prepare_title", self.lang),
                I18n.get("pp_define_output", self.lang),
            )
            return
        output_path = Path(output_text)

        try:
            lines = self.input_path.read_text(
                encoding="utf-8", errors="replace"
            ).splitlines()
        except OSError as exc:
            QMessageBox.warning(
                self,
                I18n.get("pp_prepare_title", self.lang),
                I18n.get("pp_read_fail", self.lang).format(exc=exc),
            )
            return

        keep_residues = {
            token.strip().upper()
            for token in self.keep_residues_edit.text().split(",")
            if token.strip()
        }
        selected_chain = self.chain_combo.currentText()
        chain_filter = (
            selected_chain if selected_chain and len(selected_chain) == 1 else None
        )

        kept: list[str] = []
        removed_hetatm = 0
        skipped_chain = 0
        for line in lines:
            if line.startswith("HETATM") and self.strip_checkbox.isChecked():
                resname = line[17:20].strip().upper() if len(line) > 20 else ""
                if resname not in keep_residues:
                    removed_hetatm += 1
                    continue
            if line.startswith(("ATOM", "HETATM")) and chain_filter is not None:
                line_chain = line[21] if len(line) > 21 else ""
                if line_chain != chain_filter:
                    skipped_chain += 1
                    continue
            kept.append(line)

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text("\n".join(kept) + "\n", encoding="utf-8")
        except OSError as exc:
            QMessageBox.warning(
                self,
                I18n.get("pp_prepare_title", self.lang),
                I18n.get("pp_save_fail", self.lang).format(exc=exc),
            )
            return

        self.log_console.append(
            f"PDB preparado salvo em {output_path}. HETATM removidos: {removed_hetatm}; "
            f"linhas descartadas por cadeia: {skipped_chain}."
        )

        if self.proton_checkbox.isChecked():
            self._add_hydrogens_stub(output_path)

        self.receptor_prepared.emit(str(output_path))

    def _add_hydrogens_stub(self, output_path: Path) -> None:
        """Add hydrogens via Open Babel CLI (`obabel -h`) at neutral pH.

        For physiologically accurate protonation (pKa-aware), users should still
        run H++/Reduce externally. This pipeline only adds polar/explicit
        hydrogens via Open Babel and overwrites the prepared PDB in-place.
        """
        import subprocess
        import sys
        from core.native_tools import find_obabel_executable, native_tool_env

        obabel = find_obabel_executable()
        if obabel is None:
            QMessageBox.information(
                self,
                I18n.get("pp_add_h_title", self.lang),
                I18n.get("pp_obabel_missing", self.lang),
            )
            self.log_console.append(
                f"Adição de hidrogênios solicitada para {output_path.name} — Open Babel indisponível."
            )
            return

        no_window = subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0
        protonated_path = output_path.with_name(f"{output_path.stem}_H.pdb")
        try:
            completed = subprocess.run(
                [str(obabel), str(output_path), "-O", str(protonated_path), "-h"],
                env=native_tool_env(obabel),
                capture_output=True,
                text=True,
                check=False,
                creationflags=no_window,
            )
        except OSError as exc:
            QMessageBox.warning(
                self,
                I18n.get("pp_add_h_title", self.lang),
                I18n.get("pp_obabel_run_fail", self.lang).format(exc=exc),
            )
            return

        if completed.returncode != 0 or not protonated_path.exists():
            message = (
                completed.stderr.strip()
                or completed.stdout.strip()
                or "Open Babel retornou erro."
            )
            QMessageBox.warning(self, I18n.get("pp_add_h_title", self.lang), message)
            self.log_console.append(f"Adição de hidrogênios falhou: {message}")
            return

        try:
            output_path.write_text(
                protonated_path.read_text(encoding="utf-8", errors="replace"),
                encoding="utf-8",
            )
        finally:
            try:
                protonated_path.unlink(missing_ok=True)
            except OSError:
                pass

        self.log_console.append(
            f"Hidrogênios adicionados via Open Babel em {output_path.name}. "
            "Para protonação dependente de pKa, considere H++ ou Reduce."
        )
