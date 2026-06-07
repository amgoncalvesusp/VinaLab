# -*- coding: utf-8 -*-
"""Self-installing environment management for VinaLab."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ProgressCallback = Callable[[str, int, str], None]

NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0


class EnvironmentManager:
    """Create, validate, and repair the local VinaLab Python environment."""

    _FULL_STATUS_CACHE: dict[str, dict] = {}
    _SCORING_STATUS_CACHE: dict[str, dict] = {}

    @classmethod
    def clear_caches(cls) -> None:
        """Drop cached status reports so the next query re-probes the environment.

        Must be called after installing or removing packages at runtime; otherwise
        the GUI keeps reporting freshly installed scorers/runtimes as unavailable
        until the process restarts.
        """
        cls._FULL_STATUS_CACHE.clear()
        cls._SCORING_STATUS_CACHE.clear()

    CORE_PACKAGES = [
        {
            "import_name": "PySide6.QtWidgets",
            "pip_name": "PySide6",
            "version": ">=6.7,<6.8",
            "description": "GUI framework",
        },
        {
            "import_name": "PySide6.QtWebEngineWidgets",
            "pip_name": "PySide6-Addons",
            "version": ">=6.7,<6.8",
            "description": "Embedded molecular visualization browser",
            "version_optional": True,
        },
        {
            "import_name": "vina",
            "pip_name": "vina",
            "version": ">=1.2",
            "description": "AutoDock Vina engine",
            "fallback": "vina_cli",
        },
        {
            "import_name": "meeko",
            "pip_name": "meeko",
            "version": ">=0.4",
            "description": "PDBQT preparation",
        },
        {
            "import_name": "scipy",
            "pip_name": "scipy",
            "version": ">=1.10",
            "description": "Scientific routines required by meeko",
        },
        {
            "import_name": "gemmi",
            "pip_name": "gemmi",
            "version": ">=0.6",
            "description": "Macromolecular structure support required by meeko",
        },
        {
            "import_name": "rdkit",
            "pip_name": "rdkit",
            "version": ">=2023.3",
            "description": "Molecular structure handling",
        },
        # openbabel-wheel provides both CLI obabel and Python bindings on Windows without requiring a separate installation.
        {
            "import_name": "openbabel",
            "pip_name": "openbabel-wheel",
            "version": ">=3.1",
            "description": "Format conversion fallback",
        },
        {
            "import_name": "pandas",
            "pip_name": "pandas",
            "version": ">=1.5",
            "description": "Results management",
        },
        {
            "import_name": "matplotlib",
            "pip_name": "matplotlib",
            "version": ">=3.6",
            "description": "Score charts",
        },
        {
            "import_name": "openpyxl",
            "pip_name": "openpyxl",
            "version": ">=3.0",
            "description": "Excel export",
        },
        {
            "import_name": "reportlab",
            "pip_name": "reportlab",
            "version": ">=3.6",
            "description": "PDF reports",
        },
        {
            "import_name": "numpy",
            "pip_name": "numpy",
            "version": ">=1.23,<2",
            "description": "Numerical support",
        },
        {
            "import_name": "py3Dmol",
            "pip_name": "py3Dmol",
            "version": ">=2.0",
            "description": "3Dmol molecular viewer bridge",
        },
        {
            "import_name": "wheel",
            "pip_name": "wheel",
            "version": ">=0.40",
            "description": "Python wheel build support",
        },
    ]
    OPTIONAL_SCORING_PACKAGES = [
        {
            "import_name": "click",
            "pip_name": "Click",
            "version": ">=7.0",
            "description": "DeltaVinaXGB-Light command-line runner",
            "required": False,
        },
        {
            "import_name": "xgboost",
            "pip_name": "xgboost",
            "version": ">=1.4,<2.0",
            "description": "DeltaVinaXGB-Light model runtime",
            "required": False,
        },
        {
            "import_name": "sklearn",
            "pip_name": "scikit-learn",
            "version": ">=1.0",
            "description": "ML model compatibility for scoring functions",
            "required": False,
        },
        {
            "import_name": "joblib",
            "pip_name": "joblib",
            "version": ">=1.0",
            "description": "Serialized model loading for scoring functions",
            "required": False,
        },
        {
            "import_name": "torch",
            "pip_name": "torch",
            "version": "",
            "description": "RTMScore neural-network runtime",
            "required": False,
        },
        {
            "import_name": "torchdata",
            "pip_name": "torchdata",
            "version": "==0.7.1",
            "description": "DGL data pipeline dependency",
            "required": False,
        },
        {
            "import_name": "dgl",
            "pip_name": "dgl",
            "version": ">=1.1",
            "description": "RTMScore graph neural-network runtime",
            "required": False,
        },
        {
            "import_name": "yaml",
            "pip_name": "PyYAML",
            "version": ">=6.0",
            "description": "DGL GraphBolt metadata parsing",
            "required": False,
        },
        {
            "import_name": "pydantic",
            "pip_name": "pydantic",
            "version": ">=2.0",
            "description": "DGL GraphBolt metadata validation",
            "required": False,
        },
        {
            "import_name": "dgllife",
            "pip_name": "dgllife",
            "version": ">=0.3",
            "description": "Molecular graph utilities for RTMScore",
            "required": False,
        },
        {
            "import_name": "MDAnalysis",
            "pip_name": "MDAnalysis",
            "version": ">=2.0",
            "description": "RTMScore structure parsing",
            "required": False,
        },
        {
            "import_name": "prody",
            "pip_name": "ProDy",
            "version": ">=2.4",
            "description": "RTMScore pocket extraction dependency",
            "required": False,
        },
        {
            "import_name": "torch_scatter",
            "pip_name": "torch-scatter",
            "version": ">=2.1",
            "description": "RTMScore PyTorch graph operations",
            "required": False,
        },
    ]
    REQUIRED_PACKAGES = CORE_PACKAGES + OPTIONAL_SCORING_PACKAGES

    SCORING_DEPENDENCIES = {
        "rtmscore": {
            "label": "RTMScore",
            "archive": "RTMScore-main.zip",
            "imports": [
                "torch",
                "torchdata",
                "yaml",
                "pydantic",
                "dgl",
                "dgllife",
                "MDAnalysis",
                "prody",
                "torch_scatter",
            ],
        },
        "delta_vina_xgb": {
            "label": "DeltaVinaXGB-Light",
            "archive": "deltaVinaXGB-Light.zip",
            "imports": ["click", "xgboost", "sklearn", "joblib", "rdkit", "openbabel"],
        },
        "deltavina_rf20": {
            "label": "DeltaVinaRF20",
            "archive": "deltavina-master.zip",
            "imports": [],
            "unsupported_reason": "Requires its original Python 2/R runtime; disabled in the Python 3 GUI.",
        },
    }
    TORCH_CPU_REQUIREMENT = "torch==2.2.2+cpu"

    def __init__(self, app_dir: Path | None = None) -> None:
        """Initialize paths for the local virtual environment and logs."""
        self.app_dir = (app_dir or Path(__file__).resolve().parents[1]).resolve()
        self.user_dir = self._user_data_dir()
        self.venv_path = (
            self.user_dir if self._is_frozen_bundle() else self.app_dir
        ) / ".venv"
        self.logs_dir = self.user_dir / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.install_log_path = (
            self.logs_dir / f"install_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )
        self.error_log_path = self.logs_dir / "install_error.log"
        self.base_python = (
            None if self._is_frozen_bundle() else self._find_base_python()
        )

    def detect_python_env(self) -> dict:
        """Return detected Python and local virtual environment paths."""
        scripts_dir = self.venv_path / (
            "Scripts" if sys.platform.startswith("win") else "bin"
        )
        python_name = "python.exe" if sys.platform.startswith("win") else "python"
        pip_name = "pip.exe" if sys.platform.startswith("win") else "pip"
        return {
            "python_version": sys.version_info[:3],
            "venv_path": self.venv_path,
            "pip_path": scripts_dir / pip_name,
            "python_path": scripts_dir / python_name,
            "base_python_path": self.base_python,
        }

    def create_virtualenv(self) -> bool:
        """Create the local .venv and upgrade pip inside it."""
        if self._is_frozen_bundle():
            return True
        env = self.detect_python_env()
        if env["python_path"].exists() and not self._venv_python_is_valid(
            env["python_path"]
        ):
            shutil.rmtree(self.venv_path, ignore_errors=True)
        if not env["python_path"].exists():
            if self.base_python is None:
                self._write_error_log(
                    "Não foi possível localizar um interpretador Python 3.10+ real para criar .venv."
                )
                return False
            create_result = subprocess.run(
                [str(self.base_python), "-m", "venv", str(self.venv_path)],
                cwd=self.app_dir,
                capture_output=True,
                text=True,
                check=False,
                creationflags=NO_WINDOW,
            )
            self._append_install_log(create_result.stdout)
            self._append_install_log(create_result.stderr)
            if create_result.returncode != 0:
                self._write_error_log(create_result.stderr or create_result.stdout)
                return False
        result = subprocess.run(
            [
                str(env["python_path"]),
                "-m",
                "pip",
                "install",
                "--upgrade",
                "pip",
                "--no-input",
                "--disable-pip-version-check",
            ],
            cwd=self.app_dir,
            capture_output=True,
            text=True,
            check=False,
            creationflags=NO_WINDOW,
        )
        self._append_install_log(result.stdout)
        self._append_install_log(result.stderr)
        if result.returncode != 0:
            self._write_error_log(result.stderr or result.stdout)
        return result.returncode == 0

    def check_missing(self, include_optional: bool = False) -> list[dict]:
        """Return packages that are missing or cannot be imported in the local venv."""
        env = self.detect_python_env()
        packages = self.REQUIRED_PACKAGES if include_optional else self.CORE_PACKAGES
        if self._is_frozen_bundle():
            return [
                package
                for package in packages
                if not self._package_import_ok(
                    env["python_path"], package["import_name"]
                )
            ]
        if not env["python_path"].exists():
            return list(packages)

        missing: list[dict] = []
        for package in packages:
            if package["import_name"] == "vina" and self._vina_cli_path() is not None:
                continue
            code = (
                f"import importlib; importlib.import_module({package['import_name']!r})"
            )
            result = subprocess.run(
                [str(env["python_path"]), "-c", code],
                cwd=self.app_dir,
                capture_output=True,
                text=True,
                check=False,
                creationflags=NO_WINDOW,
            )
            if result.returncode != 0:
                missing.append(package)
        return missing

    def install_package(
        self, package: dict, progress_callback: ProgressCallback
    ) -> bool:
        """Install one required package into the local venv with streamed progress."""
        env = self.detect_python_env()
        requirement = f"{package['pip_name']}{package['version']}"
        command = [
            str(env["python_path"]),
            "-m",
            "pip",
            "install",
            "--no-input",
            "--prefer-binary",
            "--disable-pip-version-check",
            requirement,
        ]
        if package["pip_name"] == "vina":
            command = [
                str(env["python_path"]),
                "-m",
                "pip",
                "install",
                "--no-input",
                "--only-binary=:all:",
                "--disable-pip-version-check",
                requirement,
            ]
        elif package["pip_name"] == "torch":
            command = [
                str(env["python_path"]),
                "-m",
                "pip",
                "install",
                "--no-input",
                "--disable-pip-version-check",
                self.TORCH_CPU_REQUIREMENT,
                "--index-url",
                "https://download.pytorch.org/whl/cpu",
            ]
        elif package["pip_name"] == "torch-scatter":
            torch_package = next(
                item
                for item in self.OPTIONAL_SCORING_PACKAGES
                if item["pip_name"] == "torch"
            )
            if not self._package_import_ok(env["python_path"], "torch"):
                self.install_package(torch_package, progress_callback)
            if not self._package_import_ok(env["python_path"], "torch"):
                self._append_install_log(
                    "AVISO torch-scatter ignorado porque torch não pôde ser instalado primeiro.\n"
                )
                progress_callback(
                    "torch-scatter",
                    0,
                    "AVISO torch-scatter ignorado porque torch não pôde ser instalado primeiro.",
                )
                return False
            command = [
                str(env["python_path"]),
                "-m",
                "pip",
                "install",
                "--no-input",
                "--prefer-binary",
                "--no-cache-dir",
                "--no-build-isolation",
                "--disable-pip-version-check",
                requirement,
            ]
        process = subprocess.Popen(
            command,
            cwd=self.app_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            creationflags=NO_WINDOW,
        )

        lines: list[str] = []
        if process.stdout:
            for line in process.stdout:
                clean_line = line.rstrip()
                lines.append(clean_line)
                self._append_install_log(clean_line + "\n")
                progress_callback(package["pip_name"], 0, clean_line)

        return_code = process.wait()
        if return_code != 0:
            if package["pip_name"] == "vina" and self._vina_cli_path() is not None:
                self._append_install_log(
                    "Wheel Python do vina indisponível; usando fallback Vina CLI incluído.\n"
                )
                progress_callback(
                    "vina",
                    100,
                    "Wheel Python do vina indisponível; usando fallback Vina CLI incluído.",
                )
                return True
            if not package.get("required", True):
                warning = f"AVISO dependência opcional {package['pip_name']} falhou ao instalar; funções de pontuação relacionadas serão desativadas.\n"
                self._append_install_log(warning)
                progress_callback(package["pip_name"], 100, warning.strip())
                return True
            self._write_error_log("\n".join(lines))
            return False
        return True

    def install_all_missing(
        self, progress_callback: ProgressCallback, include_optional: bool = False
    ) -> bool:
        """Install missing core packages sequentially.

        Optional scoring runtimes are intentionally not installed during first run because
        Torch/DGL wheels are large and often platform-specific. The GUI reports those
        scorers as disabled until a user installs their runtime explicitly.
        """
        missing = self.check_missing(include_optional=include_optional)
        if not missing:
            return True

        total = len(missing)
        for index, package in enumerate(missing, start=1):
            percent = int((index - 1) / total * 100)
            progress_callback(
                package["pip_name"], percent, f"Instalando {package['pip_name']}..."
            )
            if not self.install_package(package, progress_callback):
                if not package.get("required", True):
                    progress_callback(
                        package["pip_name"],
                        percent,
                        f"Dependência opcional {package['pip_name']} indisponível.",
                    )
                    continue
                progress_callback(
                    package["pip_name"],
                    percent,
                    f"Falha ao instalar {package['pip_name']}.",
                )
                return False
            if package.get("required", True) or self._package_import_ok(
                self.detect_python_env()["python_path"], package["import_name"]
            ):
                progress_callback(
                    package["pip_name"],
                    int(index / total * 100),
                    f"{package['pip_name']} instalado.",
                )
            else:
                progress_callback(
                    package["pip_name"],
                    int(index / total * 100),
                    f"Dependência opcional {package['pip_name']} indisponível; pontuações relacionadas serão desativadas.",
                )
        return True

    def verify_autodock_vina(self) -> dict:
        """Run a functional import and constructor check for the Vina Python API."""
        env = self.detect_python_env()
        if self._is_frozen_bundle():
            try:
                version = importlib.metadata.version("vina")
            except importlib.metadata.PackageNotFoundError:
                version = "incluído"
            try:
                from vina import Vina

                Vina(sf_name="vina")
                return {"ok": True, "mode": "bundled_python", "version": version}
            except Exception as exc:  # noqa: BLE001 - fallback CLI is acceptable here
                vina_cli = self._vina_cli_path()
                if vina_cli is not None:
                    return {
                        "ok": True,
                        "mode": "cli_fallback",
                        "version": vina_cli.name,
                        "path": str(vina_cli),
                    }
                return {"ok": False, "mode": "missing", "error": str(exc)}
        code = (
            "import importlib.metadata\n"
            "from vina import Vina\n"
            "v = Vina(sf_name='vina')\n"
            "print(importlib.metadata.version('vina'))\n"
        )
        result = subprocess.run(
            [str(env["python_path"]), "-c", code],
            cwd=self.app_dir,
            capture_output=True,
            text=True,
            check=False,
            creationflags=NO_WINDOW,
        )
        if result.returncode == 0:
            return {
                "ok": True,
                "mode": "python",
                "version": result.stdout.strip() or "unknown",
            }
        vina_cli = self._vina_cli_path()
        if vina_cli is not None:
            return {
                "ok": True,
                "mode": "cli_fallback",
                "version": vina_cli.name,
                "path": str(vina_cli),
            }
        return {
            "ok": False,
            "mode": "missing",
            "error": (result.stderr or result.stdout).strip(),
        }

    def full_status_report(self) -> dict:
        """Return and persist the current environment readiness report."""
        cache_key = str(self.app_dir)
        if cache_key in self._FULL_STATUS_CACHE:
            return dict(self._FULL_STATUS_CACHE[cache_key])
        env = self.detect_python_env()
        packages = self._package_statuses(env["python_path"])
        venv_ready = self._is_frozen_bundle() or env["python_path"].exists()
        vina_status = (
            self.verify_autodock_vina()
            if venv_ready
            else {"ok": False, "error": "venv ausente"}
        )
        report = {
            "python_version": ".".join(str(part) for part in sys.version_info[:3]),
            "venv_ready": venv_ready,
            "packages": packages,
            "vina_functional": bool(vina_status["ok"]),
            "vina": vina_status,
            "scoring_functions": self.scoring_function_statuses(),
            "all_ready": venv_ready
            and all(
                package["installed"]
                for package in packages
                if package.get("required", True)
            )
            and bool(vina_status["ok"]),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        (self.logs_dir / "environment_status.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        self._FULL_STATUS_CACHE[cache_key] = dict(report)
        return report

    def cached_status_report(self) -> dict:
        """Return the last persisted environment report without running expensive imports."""
        cache_key = str(self.app_dir)
        if cache_key in self._FULL_STATUS_CACHE:
            return dict(self._FULL_STATUS_CACHE[cache_key])
        status_path = self.logs_dir / "environment_status.json"
        if not status_path.exists():
            if self._is_frozen_bundle():
                return self.full_status_report()
            return {}
        try:
            report = json.loads(status_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        self._FULL_STATUS_CACHE[cache_key] = dict(report)
        return report

    def check_and_install(self, progress_callback: ProgressCallback) -> bool:
        """Create the venv, install missing packages, verify Vina, and persist status."""
        if self._is_frozen_bundle():
            self.clear_caches()
            report = self.full_status_report()
            ready = bool(report["all_ready"])
            if not ready:
                self._write_error_log(self._frozen_failure_report(report))
            return ready
        env = self.detect_python_env()
        if sys.version_info < (3, 10):
            self._write_error_log("Python 3.10 or newer is required.")
            return False
        if not env["python_path"].exists() and not self.create_virtualenv():
            return False
        if not self.install_all_missing(progress_callback):
            self.clear_caches()
            self.full_status_report()
            return False
        status = self.verify_autodock_vina()
        if not status["ok"]:
            self._write_error_log(status.get("error", "Falha na verificação do Vina."))
        # Packages may have changed on disk; drop stale status before the final probe.
        self.clear_caches()
        report = self.full_status_report()
        return bool(report["all_ready"])

    def scoring_function_statuses(self) -> dict[str, dict]:
        """Return availability details for bundled optional scoring functions."""
        env = self.detect_python_env()
        cache_key = f"{self.app_dir}|{env['python_path']}"
        if cache_key in self._SCORING_STATUS_CACHE:
            return dict(self._SCORING_STATUS_CACHE[cache_key])
        statuses: dict[str, dict] = {}
        pontuacao_dir = self.app_dir / "pontuacao"
        for key, config in self.SCORING_DEPENDENCIES.items():
            archive_path = pontuacao_dir / config["archive"]
            missing_imports = [
                import_name
                for import_name in config["imports"]
                if not self._package_import_ok(env["python_path"], import_name)
            ]
            unsupported_reason = config.get("unsupported_reason", "")
            available = (
                archive_path.exists() and not missing_imports and not unsupported_reason
            )
            reason = ""
            if not archive_path.exists():
                reason = f"Archive not found: {config['archive']}"
            elif unsupported_reason:
                reason = unsupported_reason
            elif missing_imports:
                reason = "Dependência Python ausente: " + ", ".join(missing_imports)
            statuses[key] = {
                "label": config["label"],
                "available": available,
                "archive_available": archive_path.exists(),
                "missing_imports": missing_imports,
                "reason": reason,
            }
        self._SCORING_STATUS_CACHE[cache_key] = dict(statuses)
        return statuses

    def _package_statuses(self, python_path: Path) -> list[dict]:
        """Return installed/version status for all required packages."""
        statuses: list[dict] = []
        for package in self.REQUIRED_PACKAGES:
            version = self._package_version(python_path, package["pip_name"])
            import_ok = self._package_import_ok(python_path, package["import_name"])
            if package["pip_name"] == "vina" and version is None:
                cli_path = self._vina_cli_path()
                if cli_path is not None:
                    version = f"bundled CLI fallback: {cli_path.name}"
                    import_ok = True
            if self._is_frozen_bundle() and import_ok and version is None:
                version = "incluído"
            installed = (
                import_ok
                if self._is_frozen_bundle()
                else version is not None and import_ok
            )
            statuses.append(
                {
                    "name": package["pip_name"],
                    "installed": installed
                    if not package.get("version_optional")
                    else import_ok,
                    "version": version or ("import ok" if import_ok else ""),
                    "description": package["description"],
                    "required": package.get("required", True),
                }
            )
        return statuses

    def _package_version(self, python_path: Path, distribution_name: str) -> str | None:
        """Return a package version from the venv, or current interpreter fallback."""
        if self._is_frozen_bundle():
            try:
                return importlib.metadata.version(distribution_name)
            except importlib.metadata.PackageNotFoundError:
                return None
        if python_path.exists():
            code = (
                "import importlib.metadata, sys\n"
                f"name = {distribution_name!r}\n"
                "try:\n"
                "    print(importlib.metadata.version(name))\n"
                "except importlib.metadata.PackageNotFoundError:\n"
                "    sys.exit(1)\n"
            )
            result = subprocess.run(
                [str(python_path), "-c", code],
                cwd=self.app_dir,
                capture_output=True,
                text=True,
                check=False,
                creationflags=NO_WINDOW,
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        try:
            return importlib.metadata.version(distribution_name)
        except importlib.metadata.PackageNotFoundError:
            return None

    def _package_import_ok(self, python_path: Path, import_name: str) -> bool:
        """Return True when a package can be imported in the venv."""
        if import_name == "vina" and self._vina_cli_path() is not None:
            return True
        if self._is_frozen_bundle():
            try:
                import importlib

                importlib.import_module(import_name)
                return True
            except Exception:  # noqa: BLE001 - imports may fail from missing bundled DLLs
                return False
        if not python_path.exists():
            return False
        result = subprocess.run(
            [
                str(python_path),
                "-c",
                f"import importlib; importlib.import_module({import_name!r})",
            ],
            cwd=self.app_dir,
            capture_output=True,
            text=True,
            check=False,
            creationflags=NO_WINDOW,
        )
        return result.returncode == 0

    def _append_install_log(self, message: str) -> None:
        """Append text to the timestamped installation log."""
        if message:
            with self.install_log_path.open("a", encoding="utf-8") as handle:
                handle.write(message)

    def _write_error_log(self, message: str) -> None:
        """Write installation failure details to install_error.log."""
        self.error_log_path.write_text(message, encoding="utf-8")

    def _frozen_failure_report(self, report: dict) -> str:
        """Build a human-readable diagnostic for a failed frozen-bundle check.

        The frozen bundle has no pip step, so failures are missing/broken bundled
        imports. Listing exactly which required packages and which Vina mode failed
        gives the user (and us) a concrete cause in logs/install_error.log instead
        of a generic "Configuração falhou".
        """
        lines = ["VinaLab frozen environment check failed.", ""]
        missing_required = [
            package
            for package in report.get("packages", [])
            if package.get("required", True) and not package.get("installed", False)
        ]
        if missing_required:
            lines.append("Pacotes obrigatórios ausentes ou não importáveis:")
            lines.extend(
                f"  - {package['name']} ({package.get('description', '')})"
                for package in missing_required
            )
        else:
            lines.append("Todos os pacotes obrigatórios foram importados.")
        vina = report.get("vina", {})
        if not vina.get("ok"):
            lines.append("")
            lines.append(
                f"AutoDock Vina indisponível: {vina.get('error', 'desconhecido')}"
            )
        disabled_scorers = [
            status.get("label", key)
            for key, status in report.get("scoring_functions", {}).items()
            if not status.get("available", False)
        ]
        if disabled_scorers:
            lines.append("")
            lines.append(
                "Funções de pontuação opcionais desativadas (não bloqueiam o uso principal): "
                + ", ".join(disabled_scorers)
            )
        return "\n".join(lines) + "\n"

    def _find_base_python(self) -> Path | None:
        """Find a real Python 3.10+ executable, avoiding the frozen VinaLab.exe."""
        if not getattr(sys, "frozen", False):
            return Path(sys.executable)

        current_executable = Path(sys.executable).resolve()
        commands = [
            ["py", "-3.10"],
            ["py", "-3"],
            ["python"],
            ["python3"],
        ]
        probe = (
            "import sys\n"
            "from pathlib import Path\n"
            "version = sys.version_info[:3]\n"
            "print(Path(sys.executable).resolve())\n"
            "print('.'.join(map(str, version)))\n"
            "raise SystemExit(0 if version >= (3, 10, 0) else 1)\n"
        )
        for command in commands:
            try:
                result = subprocess.run(
                    [*command, "-c", probe],
                    cwd=self.app_dir,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=10,
                    creationflags=NO_WINDOW,
                )
            except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
                continue
            if result.returncode != 0:
                continue
            lines = [
                line.strip() for line in result.stdout.splitlines() if line.strip()
            ]
            if not lines:
                continue
            candidate = Path(lines[0]).resolve()
            if (
                candidate.exists()
                and candidate != current_executable
                and "_MEI" not in str(candidate)
            ):
                return candidate
        return None

    def _vina_cli_path(self) -> Path | None:
        """Return a bundled AutoDock Vina executable fallback, if available."""
        bundle_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
        exe_dir = (
            Path(sys.executable).resolve().parent
            if getattr(sys, "frozen", False)
            else Path.cwd()
        )
        candidates = [
            self.app_dir / "tools" / "vina" / "vina_1.2.7_win.exe",
            bundle_dir / "tools" / "vina" / "vina_1.2.7_win.exe",
            exe_dir / "tools" / "vina" / "vina_1.2.7_win.exe",
            Path(__file__).resolve().parents[1]
            / "tools"
            / "vina"
            / "vina_1.2.7_win.exe",
        ]
        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                return candidate
        return None

    def _is_frozen_bundle(self) -> bool:
        """Return True when running from a PyInstaller executable."""
        return bool(getattr(sys, "frozen", False))

    def _user_data_dir(self) -> Path:
        """Return a writable per-user directory for logs and preferences."""
        if not self._is_frozen_bundle():
            return self.app_dir
        if sys.platform.startswith("win"):
            root = Path(
                os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")
            )
            return root / "VinaLab"
        if sys.platform == "darwin":
            return Path.home() / "Library" / "Application Support" / "VinaLab"
        return (
            Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share"))
            / "vinalab"
        )

    def _venv_python_is_valid(self, python_path: Path) -> bool:
        """Return True when the venv Python is a real interpreter, not the frozen app."""
        try:
            result = subprocess.run(
                [str(python_path), "-c", "import sys; print(sys.executable)"],
                cwd=self.app_dir,
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
                creationflags=NO_WINDOW,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False
        output = result.stdout.strip()
        return (
            result.returncode == 0
            and "VinaLab.exe" not in output
            and "_MEI" not in output
        )
