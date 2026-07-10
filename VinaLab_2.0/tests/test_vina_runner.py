from __future__ import annotations

import importlib
import sys
from pathlib import Path


def _runner_type():
    try:
        module = importlib.import_module("vinalab_core.docking.vina_runner")
    except ModuleNotFoundError:
        return None
    return getattr(module, "VinaRunner", None)


def test_vina_runner_is_available_for_safe_subprocess_execution() -> None:
    assert _runner_type() is not None


def test_vina_runner_executes_an_argument_list_with_cpu_thread_limits() -> None:
    runner_type = _runner_type()
    assert runner_type is not None

    result = runner_type().execute(
        [sys.executable, "-c", "import os; print(os.environ['OMP_NUM_THREADS'])"],
        cpu_threads=3,
        timeout_seconds=5,
    )

    assert result.ok
    assert result.returncode == 0
    assert result.stdout.strip() == "3"
    assert result.command[0] == sys.executable


def test_vina_runner_can_isolate_a_process_in_a_requested_working_directory(tmp_path: Path) -> None:
    runner_type = _runner_type()
    assert runner_type is not None

    result = runner_type().execute(
        [sys.executable, "-c", "import os; print(os.getcwd())"],
        cpu_threads=1,
        timeout_seconds=5,
        working_directory=tmp_path,
    )

    assert result.ok
    assert Path(result.stdout.strip()) == tmp_path
