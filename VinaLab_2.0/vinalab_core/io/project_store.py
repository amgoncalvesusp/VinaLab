"""SQLite-backed persistence for reproducible VinaLab projects."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from vinalab_core.docking.search_box import SearchBox, SearchBoxSource
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


class ProjectStore:
    """Owns a VinaLab SQLite project and persists only canonical run state."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self._migrate()

    def __enter__(self) -> "ProjectStore":
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
    ) -> RunRecord:
        if not receptor_hash:
            raise ValueError("receptor_hash is required")
        if not engine_key:
            raise ValueError("engine_key is required")
        if cpu_threads < 1:
            raise ValueError("cpu_threads must be at least one")
        record = RunRecord(
            id=str(uuid4()),
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
        return record

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
        )

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
