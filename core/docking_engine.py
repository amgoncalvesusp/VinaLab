# -*- coding: utf-8 -*-
"""Threaded AutoDock Vina docking engine for VinaLab."""

import csv
import os
from pathlib import Path
import tempfile
import shutil
import subprocess
import sys
import traceback
import zipfile

from PySide6.QtCore import QThread, Signal

from core.file_utils import (
    clean_pdbqt_file,
    clean_pdbqt_text,
    ensure_directory,
    pdbqt_coordinate_bounds,
    pdbqt_coordinates,
    repair_pdbqt_charges,
    safe_stem,
    sanitize_pdbqt_for_vina,
    validate_ligand_pdbqt,
    validate_pdbqt_charges,
)

NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0

# --------------------------------------------------------------------------- #
# Issue 4 — Inorganic/metal-containing complex scoring support (clarification) #
# --------------------------------------------------------------------------- #
# AutoDock Vina 1.2.x ships native parameters for a limited set of metal
# atom types (Mg, Mn, Zn, Ca, Fe, Cu) via the AutoDock atom-typing scheme.
#
# - Vina (default scoring): the empirical free-energy terms do not include a
#   dedicated coordination-bond term; metal ions are treated as Lennard-Jones
#   spheres. Predictions for metalloprotein binding sites are systematically
#   biased and should be interpreted qualitatively.
#
# - Vinardo: shares the Vina functional form with re-fitted coefficients;
#   the same Lennard-Jones limitation applies. No explicit metal correction.
#
# - AutoDock4 (ad4): supports atom-type-specific affinity grids and is the
#   preferred choice for metalloproteins because charged metal centers can be
#   modeled through AutoGrid affinity maps. Still, the force field lacks a
#   covalent or partial-covalent coordination term.
#
# Practical guidance: for transition-metal active sites (e.g., Zn proteases,
# heme iron), prefer (a) AD4 with custom affinity maps, (b) constrained
# docking against a reference metal-coordination geometry, or (c) external
# rescoring tools such as MetalDock/QM. None of the three native scoring
# functions reproduces coordination-bond strengths quantitatively, so
# absolute binding-energy estimates over metals should not be trusted.
# --------------------------------------------------------------------------- #

try:
    from vina import Vina
except (
    ImportError
):  # pragma: no cover - handled at runtime for missing optional dependency
    Vina = None


EXTERNAL_SCORING_ARCHIVES = {
    "deltavina_rf20": {
        "label": "DeltaVinaRF20",
        "archive": "deltavina-master.zip",
    },
    "delta_vina_xgb": {
        "label": "DeltaVinaXGB-Light",
        "archive": "deltaVinaXGB-Light.zip",
    },
    "rtmscore": {
        "label": "RTMScore",
        "archive": "RTMScore-main.zip",
    },
}

VINA_SCORING_NAMES = {
    "vina": ("Vina", "vina"),
    "vinardo": ("Vinardo", "vinardo"),
    "ad4": ("AutoDock4 (ad4)", "ad4"),
    "gnina": ("GNINA (CNN)", None),
}


def pontuacao_directory() -> Path:
    """Return the project-local directory that stores bundled scoring packages."""
    return Path(__file__).resolve().parents[1] / "pontuacao"


def discover_external_scoring_functions() -> list[dict]:
    """Return available external scoring function archives found in pontuacao/."""
    base_dir = pontuacao_directory()
    discovered: list[dict] = []
    for key, config in EXTERNAL_SCORING_ARCHIVES.items():
        archive_path = base_dir / config["archive"]
        if archive_path.exists():
            discovered.append(
                {
                    "key": key,
                    "label": config["label"],
                    "archive_path": archive_path,
                }
            )
    return discovered


def extract_pose_model(output_file: Path, mode: int, include_model: bool = True) -> str:
    """Return the text for a single MODEL block from a Vina output PDBQT file."""
    text = clean_pdbqt_text(output_file.read_text(encoding="utf-8", errors="replace"))
    lines = text.splitlines()
    if not any(line.startswith("MODEL") for line in lines):
        if mode == 1:
            return "\n".join(line for line in lines if line.strip()) + "\n"
        raise ValueError(f"Pose {mode} não encontrada em {output_file.name}.")

    current_mode: int | None = None
    inside_block = False
    block_lines: list[str] = []
    for line in lines:
        if line.startswith("MODEL"):
            parts = line.split()
            current_mode = (
                int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
            )
            inside_block = current_mode == mode
            block_lines = [line] if inside_block and include_model else []
            continue
        if inside_block:
            if not line.strip():
                continue
            if line.startswith("ENDMDL") and not include_model:
                return "\n".join(block_lines) + "\n"
            block_lines.append(line)
            if line.startswith("ENDMDL"):
                return "\n".join(block_lines) + "\n"
    raise ValueError(f"Pose {mode} não encontrada em {output_file.name}.")


def find_obabel_executable() -> str | None:
    """Return the Open Babel CLI executable when available."""
    obabel = shutil.which("obabel")
    if obabel:
        return obabel
    candidate = Path(sys.executable).resolve().parent / (
        "obabel.exe" if sys.platform.startswith("win") else "obabel"
    )
    return str(candidate) if candidate.exists() else None


def convert_with_obabel(input_path: Path, output_path: Path) -> Path:
    """Convert a molecular file with Open Babel."""
    obabel = find_obabel_executable()
    if obabel is None:
        raise RuntimeError("OpenBabel não encontrado.")
    completed = subprocess.run(
        [obabel, str(input_path), "-O", str(output_path)],
        capture_output=True,
        text=True,
        check=False,
        creationflags=NO_WINDOW,
    )
    if completed.returncode != 0:
        message = (
            completed.stderr.strip()
            or completed.stdout.strip()
            or "Falha na conversão com OpenBabel."
        )
        raise RuntimeError(message)
    return output_path


def os_environ_with_pythonpath(extra_path: str) -> dict[str, str]:
    """Return an environment dict extended with an extra PYTHONPATH entry."""
    env = dict(os.environ)
    current = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        extra_path if not current else os.pathsep.join([extra_path, current])
    )
    return env


class DockingWorker(QThread):
    """Run AutoDock Vina docking jobs off the GUI thread."""

    progress_signal = Signal(int)
    log_signal = Signal(str)
    result_signal = Signal(list)
    error_signal = Signal(str)

    def __init__(
        self,
        receptor_path: Path,
        rigid_receptor_path: Path | None,
        flexible_receptor_path: Path | None,
        ligand_paths: list[Path],
        output_directory: Path,
        parameters: dict,
    ) -> None:
        """Initialize the worker with validated file paths and docking parameters."""
        super().__init__()
        self.receptor_path = receptor_path
        self.rigid_receptor_path = rigid_receptor_path
        self.flexible_receptor_path = flexible_receptor_path
        self.ligand_paths = list(ligand_paths)
        self.ligand_display_names: dict[Path, str] = {}
        self.output_directory = output_directory
        self.parameters = dict(parameters)
        self._scoring_archives = {
            item["key"]: item for item in discover_external_scoring_functions()
        }
        self._scoring_extract_dirs: dict[str, Path] = {}

    def run(self) -> None:
        """Execute all docking jobs and emit incremental results."""
        gnina_cli = self._gnina_cli_path()
        selected_scoring = self._selected_scoring_functions()
        if "gnina" in selected_scoring and gnina_cli is None:
            self.error_signal.emit(
                "GNINA not found. Put gnina.exe in tools/gnina, add gnina to PATH, or select another scoring function."
            )
            return
        vina_cli = self._vina_cli_path()
        if (
            any(scoring_key != "gnina" for scoring_key in selected_scoring)
            and Vina is None
            and vina_cli is None
        ):
            self.error_signal.emit(
                "O pacote Python vina não está instalado e nenhum fallback Vina CLI incluído foi encontrado."
            )
            return

        try:
            ensure_directory(self.output_directory)
        except OSError as exc:
            self.error_signal.emit(
                f"Não foi possível criar o diretório de saída: {exc}"
            )
            return

        if not self.ligand_paths:
            self.error_signal.emit("Nenhum arquivo PDBQT de ligante foi fornecido.")
            return

        try:
            self._prepare_pdbqt_inputs()
        except Exception as exc:  # noqa: BLE001 - input preparation errors must be shown in the GUI
            self.error_signal.emit(
                f"Não foi possível preparar as entradas PDBQT: {exc}"
            )
            return

        total = len(self.ligand_paths)
        all_results: list[dict] = []
        total_jobs = total * len(selected_scoring)
        completed_jobs = 0
        self.log_signal.emit(
            f"Iniciando docking para {total} ligante(s) com {len(selected_scoring)} função(ões) de pontuação."
        )

        for index, ligand_path in enumerate(self.ligand_paths, start=1):
            for scoring_key in selected_scoring:
                try:
                    grid_warning = self._validate_ligand_inside_grid(ligand_path)
                    if grid_warning:
                        self.log_signal.emit(f"AVISO {grid_warning}")
                    ligand_results = self._run_ligand_with_scoring(
                        ligand_path, scoring_key, gnina_cli, vina_cli
                    )
                    all_results.extend(ligand_results)
                    self.result_signal.emit(ligand_results)
                    self.log_signal.emit(
                        f"Concluído {ligand_path.name} com {self._scoring_label(scoring_key)}: "
                        f"{len(ligand_results)} pose(s)."
                    )
                except Exception as exc:  # noqa: BLE001 - per-ligand/scorer failures must not stop the batch
                    self.log_signal.emit(
                        f"ERRO no docking de {ligand_path.name} com {self._scoring_label(scoring_key)}: {exc}"
                    )
                    self.log_signal.emit(traceback.format_exc())
                finally:
                    completed_jobs += 1
                    self.progress_signal.emit(int(completed_jobs / total_jobs * 100))

        self.log_signal.emit(
            f"Docking finalizado. {len(all_results)} pose(s) interpretada(s)."
        )

    def _selected_scoring_functions(self) -> list[str]:
        """Return scoring functions requested by the GUI."""
        selected = list(self.parameters.get("scoring_functions") or [])
        if not selected:
            selected = [self.parameters.get("scoring_function", "vina")]
        return selected

    def _run_ligand_with_scoring(
        self,
        ligand_path: Path,
        scoring_key: str,
        gnina_cli: Path | None,
        vina_cli: Path | None,
    ) -> list[dict]:
        """Dock or score one ligand with one selected scoring function."""
        previous_parameters = dict(self.parameters)
        label, vina_sf_name = (
            self._scoring_label(scoring_key),
            self._vina_sf_name(scoring_key),
        )
        self.parameters = {
            **previous_parameters,
            "scoring_function": scoring_key,
            "vina_sf_name": vina_sf_name,
        }
        try:
            if scoring_key == "gnina":
                if gnina_cli is None:
                    raise RuntimeError("O executável GNINA não está disponível.")
                rows = self._dock_single_ligand_gnina(ligand_path, gnina_cli)
            elif scoring_key in VINA_SCORING_NAMES:
                rows = (
                    self._dock_single_ligand(ligand_path)
                    if Vina is not None
                    else self._dock_single_ligand_cli(ligand_path, vina_cli)
                )
            else:
                rows = (
                    self._dock_single_ligand(ligand_path)
                    if Vina is not None
                    else self._dock_single_ligand_cli(ligand_path, vina_cli)
                )
                try:
                    self._run_external_scoring(scoring_key, rows)
                except Exception as exc:  # noqa: BLE001 - keep docked poses visible even when rescoring dependencies fail
                    message = f"{type(exc).__name__}: {exc}"
                    self.log_signal.emit(
                        f"ERRO ao pontuar poses geradas com {label}: {message}"
                    )
                    self.log_signal.emit(traceback.format_exc())
                    for row in rows:
                        row["vina_affinity"] = row["affinity"]
                        row["external_score"] = ""
                        row["scoring_error"] = message
            for row in rows:
                row["scoring_function"] = label
                row["scoring_key"] = scoring_key
                row["receptor_file"] = str(
                    self.rigid_receptor_path or self.receptor_path
                )
            return rows
        finally:
            self.parameters = previous_parameters

    def _run_external_scoring(
        self, scoring_key: str, ligand_results: list[dict]
    ) -> None:
        """Run an external scoring function selected in the docking scoring list."""
        if not ligand_results:
            return
        scorer_label = self._scoring_label(scoring_key)
        self.log_signal.emit(f"Repontuando poses com {scorer_label}.")
        scores = self._score_ligand_results(scoring_key, ligand_results)
        for row in ligand_results:
            row["vina_affinity"] = row["affinity"]
            row["scoring_error"] = ""
            if row["mode"] in scores:
                row["affinity"] = scores[row["mode"]]
                row["external_score"] = scores[row["mode"]]
            else:
                row["external_score"] = ""
        self.log_signal.emit(f"Repontuação concluída com {scorer_label}.")

    def _score_ligand_results(
        self, scoring_key: str, ligand_results: list[dict]
    ) -> dict[int, float]:
        """Run one bundled scoring package for all poses of a single ligand."""
        if scoring_key == "deltavina_rf20":
            raise RuntimeError(
                "DeltaVinaRF20 bundle requires its original Python 2/R runtime and cannot run in this environment."
            )
        if scoring_key == "delta_vina_xgb":
            return self._run_delta_vina_xgb(ligand_results)
        if scoring_key == "rtmscore":
            return self._run_rtmscore(ligand_results)
        raise RuntimeError(f"Unknown scoring package: {scoring_key}")

    def _scoring_label(self, scoring_key: str) -> str:
        """Return display label for a scoring function key."""
        if scoring_key in VINA_SCORING_NAMES:
            return VINA_SCORING_NAMES[scoring_key][0]
        scorer = self._scoring_archives.get(scoring_key)
        return scorer["label"] if scorer else scoring_key

    @staticmethod
    def _vina_sf_name(scoring_key: str) -> str | None:
        """Return Vina's sf_name for native Vina scoring functions."""
        if scoring_key in VINA_SCORING_NAMES:
            return VINA_SCORING_NAMES[scoring_key][1]
        return "vina"

    def _run_delta_vina_xgb(self, ligand_results: list[dict]) -> dict[int, float]:
        """Run DeltaVinaXGB-Light over all poses for one ligand."""
        working_dir = Path(tempfile.mkdtemp(prefix="vinalab_dxgb_"))
        archive_root = self._extract_scoring_archive("delta_vina_xgb")
        score_rows = self._prepare_scoring_inputs(
            ligand_results, working_dir, ligand_format="mol2"
        )
        model_dir = archive_root / "deltaVinaXGB-Light" / "Model"
        script_path = archive_root / "deltaVinaXGB-Light" / "DXGB" / "run_DXGB.py"
        try:
            for row in score_rows:
                pose_name = row["pose_id"]
                receptor_target = working_dir / f"{pose_name}_protein_all.pdb"
                ligand_target = working_dir / f"{pose_name}_ligand.mol2"
                shutil.copy2(row["receptor_pdb"], receptor_target)
                shutil.copy2(row["ligand_file"], ligand_target)
            output_file = working_dir / "score.csv"
            env = os_environ_with_pythonpath(str(archive_root / "deltaVinaXGB-Light"))
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    "--datadir",
                    str(working_dir),
                    "--modeldir",
                    str(model_dir),
                    "--outfile",
                    str(output_file),
                    "--runfeatures",
                ],
                capture_output=True,
                text=True,
                check=False,
                cwd=working_dir,
                env=env,
                creationflags=NO_WINDOW,
            )
            if completed.returncode != 0:
                message = (
                    completed.stderr.strip()
                    or completed.stdout.strip()
                    or "DeltaVinaXGB-Light failed."
                )
                raise RuntimeError(message)
            scores: dict[int, float] = {}
            with output_file.open(
                encoding="utf-8", errors="replace", newline=""
            ) as handle:
                reader = csv.DictReader(handle)
                for csv_row in reader:
                    pose_id = csv_row.get("pdb", "")
                    mode = next(
                        (
                            item["mode"]
                            for item in score_rows
                            if item["pose_id"] == pose_id
                        ),
                        None,
                    )
                    score_value = csv_row.get("XGB")
                    if mode is not None and score_value not in {None, ""}:
                        scores[mode] = float(score_value)
            return scores
        finally:
            shutil.rmtree(working_dir, ignore_errors=True)

    def _run_rtmscore(self, ligand_results: list[dict]) -> dict[int, float]:
        """Run RTMScore over all poses for one ligand."""
        for module_name in ("torch", "dgl", "MDAnalysis", "prody", "torch_scatter"):
            __import__(module_name)
        working_dir = Path(tempfile.mkdtemp(prefix="vinalab_rtmscore_"))
        archive_root = self._extract_scoring_archive("rtmscore")
        score_rows = self._prepare_scoring_inputs(
            ligand_results, working_dir, ligand_format="mol2"
        )
        receptor_target = working_dir / "receptor.pdb"
        ligand_target = working_dir / "poses.mol2"
        model_path = (
            archive_root / "RTMScore-main" / "trained_models" / "rtmscore_model1.pth"
        )
        script_path = archive_root / "RTMScore-main" / "example" / "rtmscore.py"
        try:
            shutil.copy2(score_rows[0]["receptor_pdb"], receptor_target)
            with ligand_target.open("w", encoding="utf-8") as handle:
                for row in score_rows:
                    ligand_text = row["ligand_file"].read_text(
                        encoding="utf-8", errors="replace"
                    )
                    handle.write(ligand_text)
                    if not ligand_text.endswith("\n"):
                        handle.write("\n")
            output_prefix = working_dir / "rtmscore"
            env = os_environ_with_pythonpath(str(archive_root))
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    "--prot",
                    str(receptor_target),
                    "--lig",
                    str(ligand_target),
                    "--model",
                    str(model_path),
                    "--outprefix",
                    str(output_prefix),
                ],
                capture_output=True,
                text=True,
                check=False,
                cwd=working_dir,
                env=env,
                creationflags=NO_WINDOW,
            )
            if completed.returncode != 0:
                message = (
                    completed.stderr.strip()
                    or completed.stdout.strip()
                    or "RTMScore failed."
                )
                raise RuntimeError(message)
            result_file = output_prefix.with_suffix(".csv")
            scores: dict[int, float] = {}
            with result_file.open(
                encoding="utf-8", errors="replace", newline=""
            ) as handle:
                reader = csv.DictReader(handle)
                for index, csv_row in enumerate(reader):
                    mode = (
                        score_rows[index]["mode"] if index < len(score_rows) else None
                    )
                    score_value = csv_row.get("score")
                    if mode is not None and score_value not in {None, ""}:
                        scores[mode] = float(score_value)
            return scores
        finally:
            shutil.rmtree(working_dir, ignore_errors=True)

    def _prepare_scoring_inputs(
        self, ligand_results: list[dict], working_dir: Path, ligand_format: str
    ) -> list[dict]:
        """Prepare receptor and per-pose ligand files for external rescoring."""
        receptor_pdbqt = self.rigid_receptor_path or self.receptor_path
        if receptor_pdbqt is None:
            raise RuntimeError(
                "Nenhum arquivo de receptor está disponível para repontuação."
            )
        if find_obabel_executable() is None:
            raise RuntimeError("OpenBabel não encontrado.")

        receptor_pdb = working_dir / "receptor_source.pdb"
        convert_with_obabel(receptor_pdbqt, receptor_pdb)

        prepared_rows: list[dict] = []
        for row in ligand_results:
            pose_pdbqt = (
                working_dir
                / f"{safe_stem(Path(row['ligand_name']))}_pose{row['mode']}.pdbqt"
            )
            pose_pdbqt.write_text(
                extract_pose_model(
                    Path(row["output_file"]), int(row["mode"]), include_model=False
                ),
                encoding="utf-8",
            )
            ligand_file = (
                working_dir
                / f"{safe_stem(Path(row['ligand_name']))}_pose{row['mode']}.{ligand_format}"
            )
            convert_with_obabel(pose_pdbqt, ligand_file)
            prepared_rows.append(
                {
                    "mode": int(row["mode"]),
                    "pose_id": f"pose{int(row['mode'])}",
                    "receptor_pdb": receptor_pdb,
                    "ligand_file": ligand_file,
                }
            )
        return prepared_rows

    def _extract_scoring_archive(self, scoring_key: str) -> Path:
        """Extract a scoring-function zip to a cache directory once per worker."""
        if scoring_key in self._scoring_extract_dirs:
            return self._scoring_extract_dirs[scoring_key]
        scorer = self._scoring_archives.get(scoring_key)
        if scorer is None:
            raise RuntimeError(
                f"Arquivo de pontuação não encontrado para {scoring_key}."
            )
        extract_dir = Path(tempfile.mkdtemp(prefix=f"vinalab_{scoring_key}_"))
        _safe_extract_archive(Path(scorer["archive_path"]), extract_dir)
        self._scoring_extract_dirs[scoring_key] = extract_dir
        return extract_dir

    def _prepare_pdbqt_inputs(self) -> None:
        """Create sanitized PDBQT copies for files containing unsupported PDB records."""
        receptor_result = sanitize_pdbqt_for_vina(
            self.receptor_path, self.output_directory, "receptor"
        )
        self.receptor_path = receptor_result.path
        self._log_sanitization("receptor", receptor_result)

        if self.rigid_receptor_path:
            rigid_result = sanitize_pdbqt_for_vina(
                self.rigid_receptor_path, self.output_directory, "rigid_receptor"
            )
            self.rigid_receptor_path = rigid_result.path
            self._log_sanitization("rigid receptor", rigid_result)

        if self.flexible_receptor_path:
            flex_result = sanitize_pdbqt_for_vina(
                self.flexible_receptor_path, self.output_directory, "flex_receptor"
            )
            self.flexible_receptor_path = flex_result.path
            self._log_sanitization("flexible receptor", flex_result)

        prepared_ligands: list[Path] = []
        self.ligand_display_names = {}
        for ligand_path in self.ligand_paths:
            ligand_result = sanitize_pdbqt_for_vina(
                ligand_path, self.output_directory, "ligand"
            )
            validate_ligand_pdbqt(ligand_result.path)
            self._ensure_pdbqt_charges(ligand_result.path, "ligand")
            prepared_ligands.append(ligand_result.path)
            self.ligand_display_names[ligand_result.path] = ligand_path.name
            self._log_sanitization(ligand_path.name, ligand_result)
        self.ligand_paths = prepared_ligands

        for receptor_path, role in (
            (self.receptor_path, "receptor"),
            (self.rigid_receptor_path, "rigid_receptor"),
            (self.flexible_receptor_path, "flex_receptor"),
        ):
            if receptor_path is not None:
                self._ensure_pdbqt_charges(receptor_path, role)

    def _ensure_pdbqt_charges(self, path: Path, role: str) -> None:
        """Validate column-9 partial charges; auto-repair before Vina parses the file (Issue 21)."""
        if validate_pdbqt_charges(path):
            return
        self.log_signal.emit(
            f"AVISO: cargas parciais ausentes ou inválidas em {path.name}; corrigindo antes do docking."
        )
        if not repair_pdbqt_charges(path, role):
            raise RuntimeError(
                f"Falha ao corrigir cargas parciais em {path.name}; o arquivo PDBQT é incompatível com o Vina."
            )

    def _log_sanitization(self, label: str, result) -> None:
        """Log PDBQT sanitization details when a cleaned copy was created."""
        if not result.changed:
            return
        details: list[str] = []
        if result.removed_counts:
            removed = ", ".join(
                f"{tag}={count}" for tag, count in result.removed_counts.items()
            )
            details.append(f"tags incompatíveis removidas [{removed}]")
        if result.normalized_counts:
            normalized = ", ".join(
                f"{tag}={count}" for tag, count in result.normalized_counts.items()
            )
            details.append(f"tipos atômicos normalizados [{normalized}]")
        self.log_signal.emit(f"PDBQT sanitizado ({label}): {'; '.join(details)}.")
        self.log_signal.emit(f"Usando cópia sanitizada: {result.path}")
        if "receptor" in label.lower():
            ligand_only_tags = {"ROOT", "ENDROOT", "BRANCH", "ENDBRANCH"}
            removed_ligand_lines = sum(
                count
                for tag, count in result.removed_counts.items()
                if tag.upper() in ligand_only_tags
            )
            self.log_signal.emit(
                f"Receptor sanitizado: {removed_ligand_lines} linhas removidas (ROOT, ENDROOT, BRANCH, ENDBRANCH)."
            )

    def _dock_single_ligand(self, ligand_path: Path) -> list[dict]:
        """Dock a single ligand with the Vina Python API and return parsed pose rows."""
        ligand_name = self._ligand_display_name(ligand_path)
        sf_name = (
            self.parameters.get("vina_sf_name") or self.parameters["scoring_function"]
        )
        vina_instance = Vina(
            sf_name=sf_name,
            cpu=int(self.parameters["cpu"]),
            seed=int(self.parameters["seed"]),
        )

        receptor_for_maps = self.rigid_receptor_path or self.receptor_path
        if self.flexible_receptor_path:
            vina_instance.set_receptor(
                rigid_pdbqt_filename=str(receptor_for_maps),
                flex_pdbqt_filename=str(self.flexible_receptor_path),
            )
        else:
            vina_instance.set_receptor(str(receptor_for_maps))

        vina_instance.set_ligand_from_file(str(ligand_path))
        vina_instance.compute_vina_maps(
            center=[
                float(self.parameters["center_x"]),
                float(self.parameters["center_y"]),
                float(self.parameters["center_z"]),
            ],
            box_size=[
                float(self.parameters["size_x"]),
                float(self.parameters["size_y"]),
                float(self.parameters["size_z"]),
            ],
        )

        self.log_signal.emit(f"Executando docking de {ligand_name} com {sf_name}.")
        vina_instance.dock(
            exhaustiveness=int(self.parameters["exhaustiveness"]),
            n_poses=int(self.parameters["num_modes"]),
            min_rmsd=float(self.parameters["min_rmsd"]),
        )

        scoring_suffix = safe_stem(
            Path(str(self.parameters.get("scoring_function", "vina")))
        )
        output_file = (
            self.output_directory
            / f"{safe_stem(Path(ligand_name))}_{scoring_suffix}_out.pdbqt"
        )
        vina_instance.write_poses(
            str(output_file),
            n_poses=int(self.parameters["num_modes"]),
            energy_range=float(self.parameters["energy_range"]),
            overwrite=True,
        )
        clean_pdbqt_file(output_file)
        return self.parse_output_pdbqt(output_file, ligand_name)

    def _dock_single_ligand_gnina(
        self, ligand_path: Path, gnina_cli: Path
    ) -> list[dict]:
        """Dock a single ligand with GNINA when available."""
        ligand_name = self._ligand_display_name(ligand_path)
        output_file = (
            self.output_directory / f"{safe_stem(Path(ligand_name))}_gnina_out.pdbqt"
        )
        command = [
            str(gnina_cli),
            "--receptor",
            str(self.receptor_path),
            "--ligand",
            str(ligand_path),
            "--center_x",
            str(float(self.parameters["center_x"])),
            "--center_y",
            str(float(self.parameters["center_y"])),
            "--center_z",
            str(float(self.parameters["center_z"])),
            "--size_x",
            str(float(self.parameters["size_x"])),
            "--size_y",
            str(float(self.parameters["size_y"])),
            "--size_z",
            str(float(self.parameters["size_z"])),
            "--exhaustiveness",
            str(int(self.parameters["exhaustiveness"])),
            "--num_modes",
            str(int(self.parameters["num_modes"])),
            "--out",
            str(output_file),
            "--cnn_scoring",
            "rescore",
        ]
        self.log_signal.emit(
            f"Executando docking de {ligand_name} com pontuação GNINA CNN."
        )
        completed = subprocess.run(
            command,
            cwd=self.output_directory,
            capture_output=True,
            text=True,
            check=False,
            creationflags=NO_WINDOW,
        )
        for line in completed.stdout.splitlines():
            self.log_signal.emit(line)
        for line in completed.stderr.splitlines():
            self.log_signal.emit(line)
        if completed.returncode != 0:
            raise RuntimeError(f"GNINA finalizou com código {completed.returncode}.")
        clean_pdbqt_file(output_file)
        return self.parse_output_pdbqt(output_file, ligand_name)

    def _dock_single_ligand_cli(self, ligand_path: Path, vina_cli: Path) -> list[dict]:
        """Dock a single ligand with the bundled Vina CLI fallback."""
        ligand_name = self._ligand_display_name(ligand_path)
        scoring_suffix = safe_stem(
            Path(str(self.parameters.get("scoring_function", "vina")))
        )
        output_file = (
            self.output_directory
            / f"{safe_stem(Path(ligand_name))}_{scoring_suffix}_out.pdbqt"
        )
        receptor_for_maps = self.rigid_receptor_path or self.receptor_path
        command = [
            str(vina_cli),
            "--receptor",
            str(receptor_for_maps),
            "--ligand",
            str(ligand_path),
            "--center_x",
            str(float(self.parameters["center_x"])),
            "--center_y",
            str(float(self.parameters["center_y"])),
            "--center_z",
            str(float(self.parameters["center_z"])),
            "--size_x",
            str(float(self.parameters["size_x"])),
            "--size_y",
            str(float(self.parameters["size_y"])),
            "--size_z",
            str(float(self.parameters["size_z"])),
            "--exhaustiveness",
            str(int(self.parameters["exhaustiveness"])),
            "--num_modes",
            str(int(self.parameters["num_modes"])),
            "--energy_range",
            str(float(self.parameters["energy_range"])),
            "--min_rmsd",
            str(float(self.parameters["min_rmsd"])),
            "--cpu",
            str(int(self.parameters["cpu"])),
            "--scoring",
            str(
                self.parameters.get("vina_sf_name")
                or self.parameters["scoring_function"]
            ),
            "--out",
            str(output_file),
        ]
        if int(self.parameters["seed"]) != 0:
            command.extend(["--seed", str(int(self.parameters["seed"]))])
        if self.flexible_receptor_path:
            command.extend(["--flex", str(self.flexible_receptor_path)])

        self.log_signal.emit(
            f"Executando docking de {ligand_name} com fallback Vina CLI incluído."
        )
        completed = subprocess.run(
            command,
            cwd=self.output_directory,
            capture_output=True,
            text=True,
            check=False,
            creationflags=NO_WINDOW,
        )
        for line in completed.stdout.splitlines():
            self.log_signal.emit(line)
        for line in completed.stderr.splitlines():
            self.log_signal.emit(line)
        if completed.returncode != 0:
            raise RuntimeError(
                f"Vina CLI incluído finalizou com código {completed.returncode}."
            )
        clean_pdbqt_file(output_file)
        return self.parse_output_pdbqt(output_file, ligand_name)

    def _ligand_display_name(self, ligand_path: Path) -> str:
        """Return the original ligand name when a sanitized copy is being docked."""
        return self.ligand_display_names.get(ligand_path, ligand_path.name)

    def _validate_ligand_inside_grid(self, ligand_path: Path) -> str | None:
        """Return a clear warning when ligand coordinates start outside the search box."""
        coordinates = pdbqt_coordinates(ligand_path)
        if not coordinates:
            return None
        center = (
            float(self.parameters["center_x"]),
            float(self.parameters["center_y"]),
            float(self.parameters["center_z"]),
        )
        half_size = (
            float(self.parameters["size_x"]) / 2.0,
            float(self.parameters["size_y"]) / 2.0,
            float(self.parameters["size_z"]) / 2.0,
        )
        lower = tuple(center[index] - half_size[index] for index in range(3))
        upper = tuple(center[index] + half_size[index] for index in range(3))
        outside = [
            coordinate
            for coordinate in coordinates
            if any(
                coordinate[index] < lower[index] or coordinate[index] > upper[index]
                for index in range(3)
            )
        ]
        if not outside:
            return None
        bounds = pdbqt_coordinate_bounds([ligand_path])
        if bounds is None:
            return None
        suggested_size = tuple(
            max(
                float(self.parameters[f"size_{axis}"]),
                2
                * max(
                    abs(bounds[index][0] - center[index]),
                    abs(bounds[index][1] - center[index]),
                )
                + 2.0,
            )
            for index, axis in enumerate(("x", "y", "z"))
        )
        return (
            "Alguns átomos do ligante estão fora da caixa de busca atual. "
            f"Intervalos X/Y/Z da grade: {lower[0]:.3f}..{upper[0]:.3f}, "
            f"{lower[1]:.3f}..{upper[1]:.3f}, {lower[2]:.3f}..{upper[2]:.3f}. "
            f"Limites do ligante: X {bounds[0][0]:.3f}..{bounds[0][1]:.3f}, "
            f"Y {bounds[1][0]:.3f}..{bounds[1][1]:.3f}, "
            f"Z {bounds[2][0]:.3f}..{bounds[2][1]:.3f}. "
            f"O docking continuará, mas para validação por redocking considere size_x/y/z em torno de "
            f"{suggested_size[0]:.1f}/{suggested_size[1]:.1f}/{suggested_size[2]:.1f} Å ou recentralize a caixa."
        )

    @staticmethod
    def parse_output_pdbqt(output_file: Path, ligand_name: str) -> list[dict]:
        """Parse Vina output PDBQT MODEL/REMARK records into result rows."""
        results: list[dict] = []
        if not output_file.exists():
            return results

        current_mode: int | None = None
        current_cnn_score: float | None = None
        current_cnn_affinity: float | None = None
        for line in clean_pdbqt_text(
            output_file.read_text(encoding="utf-8", errors="replace")
        ).splitlines():
            if line.startswith("MODEL"):
                parts = line.split()
                current_mode = (
                    int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
                )
                current_cnn_score = None
                current_cnn_affinity = None
            elif "CNNscore" in line:
                current_cnn_score = _last_float(line)
            elif "CNNaffinity" in line:
                current_cnn_affinity = _last_float(line)
            elif "REMARK VINA RESULT:" in line:
                parts = line.split()
                try:
                    affinity = float(parts[3])
                    rmsd_lb = float(parts[4])
                    rmsd_ub = float(parts[5])
                except (IndexError, ValueError):
                    continue
                row = {
                    "ligand_name": ligand_name,
                    "mode": current_mode or len(results) + 1,
                    "pose_rank": current_mode or len(results) + 1,
                    "affinity": affinity,
                    "rmsd_lb": rmsd_lb,
                    "rmsd_ub": rmsd_ub,
                    "output_file": str(output_file),
                }
                if current_cnn_score is not None:
                    row["cnn_score"] = current_cnn_score
                if current_cnn_affinity is not None:
                    row["cnn_affinity"] = current_cnn_affinity
                results.append(row)
        return results

    @staticmethod
    def _vina_cli_path() -> Path | None:
        """Return the bundled AutoDock Vina executable fallback."""
        candidates = [
            Path(__file__).resolve().parents[1]
            / "tools"
            / "vina"
            / "vina_1.2.7_win.exe",
            Path.cwd() / "tools" / "vina" / "vina_1.2.7_win.exe",
        ]
        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                return candidate
        return None

    @staticmethod
    def _gnina_cli_path() -> Path | None:
        """Return a GNINA executable from PATH or a local tools directory."""
        path_value = shutil.which("gnina") or shutil.which("gnina.exe")
        if path_value:
            return Path(path_value)
        candidates = [
            Path(__file__).resolve().parents[1] / "tools" / "gnina" / "gnina.exe",
            Path.cwd() / "tools" / "gnina" / "gnina.exe",
        ]
        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                return candidate
        return None


def _safe_extract_archive(archive_path: Path, destination: Path) -> None:
    """Extract an archive into ``destination`` rejecting path-traversal members.

    ``shutil.unpack_archive`` / ``ZipFile.extractall`` will happily write outside the
    target directory if an archive contains members with ``..`` or absolute paths
    (zip-slip). Scoring bundles are shipped with the app, but a corrupt or swapped
    archive dropped into ``pontuacao/`` must not be able to escape the temp dir.
    """
    destination = destination.resolve()
    if zipfile.is_zipfile(archive_path):
        with zipfile.ZipFile(archive_path) as bundle:
            for member in bundle.namelist():
                target = (destination / member).resolve()
                if target != destination and destination not in target.parents:
                    raise RuntimeError(
                        f"Arquivo de pontuação rejeitado: membro fora do diretório de extração ({member})."
                    )
            bundle.extractall(destination)
        return
    shutil.unpack_archive(str(archive_path), str(destination))


def _last_float(line: str) -> float | None:
    """Return the last float token in a line."""
    for token in reversed(line.replace(":", " ").split()):
        try:
            return float(token)
        except ValueError:
            continue
    return None
