"""SQLite-backed persistence for reproducible VinaLab projects."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Self
from uuid import uuid4

from vinalab_core.docking.search_box import SearchBox
from vinalab_core.docking.vina_engine import VinaCommandBuilder
from vinalab_core.docking.vina_results import VinaPoseResult


@dataclass(frozen=True, slots=True)
class RunRecord:
    id: str
    receptor_hash: str
    search_box: SearchBox
    engine_key: str
    seed: int
    cpu_threads: int
    created_at: datetime
    ligand_hash: str = ""
    receptor_path: str = ""
    ligand_path: str = ""
    output_path: str = ""
    exhaustiveness: int = 8
    scoring: str = "vina"
    num_modes: int = 9
    energy_range: float = 3.0
    status: str = "pending"
    error: str = ""
    stdout: str = ""
    stderr: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)


class ProjectStore:
    """Owns a VinaLab SQLite project and persists only canonical run state."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.connection = sqlite3.connect(self.path)
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.row_factory = sqlite3.Row
        self._migrate()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self.connection.close()

    def create_run(
        self,
        *,
        receptor_hash: str,
        search_box: SearchBox,
        engine_key: str,
        seed: int,
        cpu_threads: int,
        run_id: str | None = None,
        ligand_hash: str = "",
        receptor_path: str | Path = "",
        ligand_path: str | Path = "",
        output_path: str | Path = "",
        exhaustiveness: int = 8,
        scoring: str = "vina",
        num_modes: int = 9,
        energy_range: float = 3.0,
        status: str = "pending",
        error: str = "",
        stdout: str = "",
        stderr: str = "",
        metadata: Mapping[str, Any] | None = None,
    ) -> RunRecord:
        if not receptor_hash:
            raise ValueError("receptor_hash is required")
        if not engine_key:
            raise ValueError("engine_key is required")
        if cpu_threads < 1:
            raise ValueError("cpu_threads must be at least one")
        VinaCommandBuilder("vina").build(
            receptor=receptor_path,
            ligand=ligand_path,
            output=output_path,
            search_box=search_box,
            cpu_threads=cpu_threads,
            exhaustiveness=exhaustiveness,
            seed=seed,
            scoring=scoring,
            num_modes=num_modes,
            energy_range=energy_range,
        )
        _validate_status(status)
        if run_id is not None and not run_id.strip():
            raise ValueError("run_id must not be empty")
        metadata_json = json.dumps(dict(metadata or {}), allow_nan=False)
        record = RunRecord(
            id=run_id if run_id is not None else str(uuid4()),
            receptor_hash=receptor_hash,
            search_box=search_box,
            engine_key=engine_key,
            seed=seed,
            cpu_threads=cpu_threads,
            created_at=datetime.now(UTC),
        )
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO runs (
                    id, receptor_hash, center_x, center_y, center_z, size_x, size_y, size_z,
                    coordinate_frame, margin, box_source, engine_key, seed, cpu_threads, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.receptor_hash,
                    *record.search_box.center,
                    *record.search_box.size,
                    record.search_box.coordinate_frame,
                    record.search_box.margin,
                    record.search_box.source,
                    record.engine_key,
                    record.seed,
                    record.cpu_threads,
                    record.created_at.isoformat(),
                ),
            )
            self.connection.execute(
                """UPDATE runs SET ligand_hash=?, receptor_path=?, ligand_path=?, output_path=?,
                exhaustiveness=?, scoring=?, num_modes=?, energy_range=?, status=?, error=?,
                stdout=?, stderr=?, metadata_json=? WHERE id=?""",
                (
                    ligand_hash,
                    str(receptor_path),
                    str(ligand_path),
                    str(output_path),
                    exhaustiveness,
                    scoring,
                    num_modes,
                    energy_range,
                    status,
                    error,
                    stdout,
                    stderr,
                    metadata_json,
                    record.id,
                ),
            )
        return self.get_run(record.id)

    def get_run(self, run_id: str) -> RunRecord:
        row = self.connection.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        if row is None:
            raise KeyError(f"run not found: {run_id}")
        search_box = SearchBox(
            center=(row["center_x"], row["center_y"], row["center_z"]),
            size=(row["size_x"], row["size_y"], row["size_z"]),
            coordinate_frame=row["coordinate_frame"],
            margin=row["margin"],
            source=row["box_source"],  # type: ignore[arg-type]
        )
        return RunRecord(
            id=row["id"],
            receptor_hash=row["receptor_hash"],
            search_box=search_box,
            engine_key=row["engine_key"],
            seed=row["seed"],
            cpu_threads=row["cpu_threads"],
            created_at=datetime.fromisoformat(row["created_at"]),
            ligand_hash=row["ligand_hash"],
            receptor_path=row["receptor_path"],
            ligand_path=row["ligand_path"],
            output_path=row["output_path"],
            exhaustiveness=row["exhaustiveness"],
            scoring=row["scoring"],
            num_modes=row["num_modes"],
            energy_range=row["energy_range"],
            status=row["status"],
            error=row["error"],
            stdout=row["stdout"],
            stderr=row["stderr"],
            metadata=json.loads(row["metadata_json"]),
        )

    def list_runs(self) -> tuple[RunRecord, ...]:
        rows = self.connection.execute(
            "SELECT id FROM runs ORDER BY created_at DESC, rowid DESC"
        ).fetchall()
        return tuple(self.get_run(row["id"]) for row in rows)

    def get_output_path(self, run_id: str) -> Path | None:
        value = self.get_run(run_id).output_path
        return Path(value) if value else None

    def update_run_status(
        self,
        run_id: str,
        status: str,
        error: str = "",
        *,
        stdout: str | None = None,
        stderr: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> RunRecord:
        _validate_status(status)
        old = self.get_run(run_id)
        metadata_json = json.dumps(
            dict(old.metadata if metadata is None else metadata), allow_nan=False
        )
        with self.connection:
            self.connection.execute(
                "UPDATE runs SET status=?, error=?, stdout=?, stderr=?, metadata_json=? WHERE id=?",
                (
                    status,
                    error,
                    old.stdout if stdout is None else stdout,
                    old.stderr if stderr is None else stderr,
                    metadata_json,
                    run_id,
                ),
            )
        return self.get_run(run_id)

    def record_vina_poses(self, run_id: str, poses: list[VinaPoseResult]) -> None:
        self.get_run(run_id)
        with self.connection:
            self.connection.execute("DELETE FROM vina_poses WHERE run_id = ?", (run_id,))
            self.connection.executemany(
                """
                INSERT INTO vina_poses (run_id, mode, affinity, rmsd_lb, rmsd_ub)
                VALUES (?, ?, ?, ?, ?)
                """,
                [(run_id, pose.mode, pose.affinity, pose.rmsd_lb, pose.rmsd_ub) for pose in poses],
            )

    def list_vina_poses(self, run_id: str) -> tuple[VinaPoseResult, ...]:
        rows = self.connection.execute(
            """
            SELECT mode, affinity, rmsd_lb, rmsd_ub
            FROM vina_poses WHERE run_id = ? ORDER BY mode
            """,
            (run_id,),
        ).fetchall()
        return tuple(
            VinaPoseResult(row["mode"], row["affinity"], row["rmsd_lb"], row["rmsd_ub"])
            for row in rows
        )

    def _migrate(self) -> None:
        with self.connection:
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    receptor_hash TEXT NOT NULL,
                    center_x REAL NOT NULL, center_y REAL NOT NULL, center_z REAL NOT NULL,
                    size_x REAL NOT NULL, size_y REAL NOT NULL, size_z REAL NOT NULL,
                    coordinate_frame TEXT NOT NULL,
                    margin REAL NOT NULL,
                    box_source TEXT NOT NULL,
                    engine_key TEXT NOT NULL,
                    seed INTEGER NOT NULL,
                    cpu_threads INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS vina_poses (
                    run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
                    mode INTEGER NOT NULL,
                    affinity REAL NOT NULL,
                    rmsd_lb REAL NOT NULL,
                    rmsd_ub REAL NOT NULL,
                    PRIMARY KEY (run_id, mode)
                )
                """
            )
            columns = {row["name"] for row in self.connection.execute("PRAGMA table_info(runs)")}
            additions = {
                "ligand_hash": "TEXT NOT NULL DEFAULT ''",
                "receptor_path": "TEXT NOT NULL DEFAULT ''",
                "ligand_path": "TEXT NOT NULL DEFAULT ''",
                "output_path": "TEXT NOT NULL DEFAULT ''",
                "exhaustiveness": "INTEGER NOT NULL DEFAULT 8",
                "scoring": "TEXT NOT NULL DEFAULT 'vina'",
                "num_modes": "INTEGER NOT NULL DEFAULT 9",
                "energy_range": "REAL NOT NULL DEFAULT 3.0",
                "status": "TEXT NOT NULL DEFAULT 'unknown'",
                "error": "TEXT NOT NULL DEFAULT ''",
                "stdout": "TEXT NOT NULL DEFAULT ''",
                "stderr": "TEXT NOT NULL DEFAULT ''",
                "metadata_json": "TEXT NOT NULL DEFAULT '{}'",
            }
            for name, definition in additions.items():
                if name not in columns:
                    self.connection.execute(f"ALTER TABLE runs ADD COLUMN {name} {definition}")


def _validate_status(status: str) -> None:
    if status not in {"unknown", "pending", "running", "completed", "failed", "cancelled"}:
        raise ValueError("invalid run status")
