# -*- coding: utf-8 -*-
"""Standard-library bootstrap launcher for VinaLab."""

from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from core.i18n import I18n

NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0


def _open_path(path) -> None:
    """Open a file or directory with the OS default handler (cross-platform)."""
    if sys.platform.startswith("win"):
        os.startfile(path)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


BG_DARK = "#0f1117"
BG_CARD = "#1a1d27"
ACCENT = "#4f8ef7"
SUCCESS = "#2ecc71"
DANGER = "#e74c3c"
TEXT = "#e8eaf0"
TEXT_SUB = "#8892a4"
FONT_UI = ("Segoe UI", 10)
FONT_MONO = ("Cascadia Code", 9)


class BootstrapWindow:
    """Minimal tkinter environment setup window for first-run installation."""

    def __init__(self) -> None:
        """Create the bootstrap window without importing scientific dependencies."""
        self.app_dir = self._resolve_app_dir()
        self.lang = self._load_lang()
        self.cancelled = False
        self.root = tk.Tk()
        self.root.title("VinaLab - Configuração do ambiente")
        self.root.geometry("760x560")
        self.root.protocol("WM_DELETE_WINDOW", self.cancel)
        self._configure_theme()

        self.status_var = tk.StringVar(value="Verificando ambiente...")
        self.progress_var = tk.IntVar(value=0)
        self.package_labels = {}
        self.banner_label = None
        self.note_label = None
        self.launch_button = None
        self.retry_button = None
        self.log_button = None
        self._build_ui()

    def run(self) -> None:
        """Start the background setup thread and enter tkinter's event loop."""
        if self._environment_already_ready():
            self._launch_main_from_status()
            self.root.destroy()
            return
        if sys.version_info < (3, 10):
            messagebox.showerror(
                "Python 3.10 necessário",
                "Instale o Python 3.10+ em https://www.python.org",
            )
            self.root.destroy()
            return
        thread = threading.Thread(target=self._setup_environment, daemon=True)
        thread.start()
        self.root.mainloop()

    def cancel(self) -> None:
        """Request cancellation and close the bootstrap window."""
        self.cancelled = True
        self.root.destroy()

    def _build_ui(self) -> None:
        """Build all bootstrap widgets."""
        container = ttk.Frame(self.root, padding=16)
        container.pack(fill="both", expand=True)

        title = ttk.Label(container, text="VinaLab", style="Title.TLabel")
        title.pack(anchor="w")

        self.status_label = ttk.Label(
            container, textvariable=self.status_var, style="Status.TLabel"
        )
        self.status_label.pack(anchor="w", pady=(8, 4))
        self.banner_label = tk.Label(
            container, text="", font=("Segoe UI", 16, "bold"), fg="white"
        )
        self.banner_label.pack(fill="x", pady=(0, 8))
        self.banner_label.pack_forget()

        self.progress = ttk.Progressbar(
            container, variable=self.progress_var, mode="determinate", maximum=100
        )
        self.progress.pack(fill="x", pady=(0, 12))

        checklist_frame = ttk.LabelFrame(container, text="Pacotes obrigatórios")
        checklist_frame.pack(fill="x", pady=(0, 12))
        from core.environment_manager import EnvironmentManager

        package_names = [
            package["pip_name"] for package in EnvironmentManager.CORE_PACKAGES
        ]
        for name in package_names:
            label = ttk.Label(checklist_frame, text=f"... {name}")
            label.pack(anchor="w", padx=8, pady=2)
            self.package_labels[name] = label

        log_frame = ttk.LabelFrame(container, text="Log de instalação")
        log_frame.pack(fill="both", expand=True)
        self.log_text = tk.Text(
            log_frame,
            height=12,
            state="disabled",
            font=FONT_MONO,
            wrap="word",
            bg="#0a0c14",
            fg=ACCENT,
            insertbackground=TEXT,
            relief="flat",
            bd=0,
        )
        self.log_text.pack(fill="both", expand=True, padx=6, pady=6)

        button_frame = ttk.Frame(container)
        button_frame.pack(fill="x", pady=(12, 0))
        self.launch_button = tk.Button(
            button_frame,
            text=I18n.get("launch_button", self.lang),
            state="disabled",
            bg=SUCCESS,
            fg="white",
            activebackground="#27AE60",
            activeforeground="white",
            font=("Segoe UI", 12, "bold"),
            padx=12,
            pady=8,
            relief="flat",
            bd=0,
        )
        self.launch_button.pack(side="left")
        self.retry_button = ttk.Button(
            button_frame, text=I18n.get("retry_button", self.lang), command=self._retry
        )
        self.log_button = ttk.Button(
            button_frame,
            text=I18n.get("open_log_button", self.lang),
            command=lambda: None,
        )
        self.cancel_button = ttk.Button(
            button_frame, text="Cancelar", command=self.cancel
        )
        self.cancel_button.pack(side="right")
        self.note_label = ttk.Label(container, text="", wraplength=700)
        self.note_label.pack(fill="x", pady=(8, 0))

    def _configure_theme(self) -> None:
        """Apply a dark visual theme to the standard-library bootstrap window."""
        self.root.configure(bg=BG_DARK)
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TFrame", background=BG_DARK)
        style.configure("TLabel", background=BG_DARK, foreground=TEXT, font=FONT_UI)
        style.configure(
            "Title.TLabel",
            background=BG_DARK,
            foreground=ACCENT,
            font=("Segoe UI", 26, "bold"),
        )
        style.configure(
            "Status.TLabel", background=BG_DARK, foreground=TEXT, font=("Segoe UI", 11)
        )
        style.configure(
            "TLabelFrame",
            background=BG_DARK,
            foreground=TEXT_SUB,
            bordercolor="#2e3347",
        )
        style.configure(
            "TLabelFrame.Label",
            background=BG_DARK,
            foreground=TEXT_SUB,
            font=("Segoe UI", 9, "bold"),
        )
        style.configure(
            "TButton",
            background=BG_CARD,
            foreground=TEXT,
            borderwidth=0,
            focusthickness=0,
            font=FONT_UI,
        )
        style.map(
            "TButton",
            background=[("active", "#222636")],
            foreground=[("disabled", "#3d4356")],
        )
        style.configure(
            "Horizontal.TProgressbar",
            background=ACCENT,
            troughcolor=BG_CARD,
            bordercolor="#2e3347",
        )

    def _setup_environment(self) -> None:
        """Run environment setup in the background."""
        try:
            from core.environment_manager import EnvironmentManager

            manager = EnvironmentManager(self.app_dir)
            self._set_status("Criando/verificando ambiente local...")
            ready = manager.check_and_install(self._progress_callback)
            report = manager.full_status_report()
            self.root.after(
                0, lambda: self._finish(ready and report["all_ready"], report, manager)
            )
        except Exception as exc:  # noqa: BLE001 - bootstrap must surface all setup failures
            self.root.after(0, lambda: self._show_failure(str(exc), None))

    def _progress_callback(
        self, package_name: str, percent_complete: int, log_line: str
    ) -> None:
        """Receive installer progress from EnvironmentManager."""
        if self.cancelled:
            return
        self.root.after(
            0, lambda: self._apply_progress(package_name, percent_complete, log_line)
        )

    def _apply_progress(
        self, package_name: str, percent_complete: int, log_line: str
    ) -> None:
        """Update tkinter widgets from the main thread."""
        self.progress_var.set(max(0, min(100, percent_complete)))
        self.status_var.set(log_line or f"Instalando {package_name}...")
        label = self.package_labels.get(package_name)
        if label:
            label.configure(text=f"... {package_name}")
        self._append_log(log_line)

    def _finish(self, ready: bool, report: dict, manager) -> None:
        """Render the final setup state."""
        for package in report.get("packages", []):
            label = self.package_labels.get(package["name"])
            if label:
                icon = "OK" if package["installed"] else "FALHA"
                label.configure(
                    text=f"{icon} {package['name']} {package.get('version', '')}"
                )
        self.progress_var.set(100 if ready else self.progress_var.get())
        self.cancel_button.configure(text="Fechar")
        if ready:
            self._show_success(manager)
        else:
            self._show_failure(
                "Configuração falhou. Consulte logs/install_error.log.", manager
            )

    def _show_success(self, manager) -> None:
        """Show the ready state and a launch button."""
        self.status_var.set("Ambiente pronto - VinaLab totalmente operacional")
        if self.banner_label is not None:
            self.banner_label.configure(
                text=I18n.get("installer_ready_banner", self.lang), bg=SUCCESS
            )
            self.banner_label.pack(fill="x", pady=(0, 8), before=self.progress)
        if self.note_label is not None:
            self.note_label.configure(text=I18n.get("installer_note", self.lang))
        if self.launch_button is not None:
            self.launch_button.configure(
                text=I18n.get("launch_button", self.lang),
                state="normal",
                command=lambda: self._launch_main(manager),
            )
        if self.retry_button is not None:
            self.retry_button.pack_forget()
        if self.log_button is not None:
            self.log_button.pack_forget()

    def _show_failure(self, message: str, manager) -> None:
        """Show the failed state and retry/log buttons."""
        self.status_var.set(f"FALHA: {message}")
        if self.banner_label is not None:
            self.banner_label.configure(
                text=I18n.get("installer_failed_banner", self.lang), bg=DANGER
            )
            self.banner_label.pack(fill="x", pady=(0, 8), before=self.progress)
        if self.launch_button is not None:
            self.launch_button.configure(state="disabled")
            self.launch_button.pack_forget()
        if self.retry_button is not None:
            self.retry_button.pack(side="left", padx=(0, 8))
        if manager and self.log_button is not None:
            self.log_button.configure(
                command=lambda: _open_path(manager.error_log_path)
            )
            self.log_button.pack(side="left")

    def _retry(self) -> None:
        """Close and restart the launcher process."""
        subprocess.Popen(
            [*self._python_command(), str(self.app_dir / "launcher.py")],
            cwd=self.app_dir,
            creationflags=NO_WINDOW,
        )
        self.root.destroy()

    def _launch_main(self, manager) -> None:
        """Launch the PySide6 application using the local venv Python."""
        env = manager.detect_python_env()
        self.root.destroy()
        subprocess.Popen(
            [str(env["python_path"]), str(self.app_dir / "main.py")],
            cwd=self.app_dir,
            creationflags=NO_WINDOW,
        )

    def _set_status(self, message: str) -> None:
        """Update status text from the background thread."""
        self.root.after(0, lambda: self.status_var.set(message))

    def _append_log(self, message: str) -> None:
        """Append a line to the read-only log console."""
        if not message:
            return
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    @staticmethod
    def _resolve_app_dir() -> Path:
        """Resolve a stable app directory instead of PyInstaller's temporary folder."""
        if getattr(sys, "frozen", False):
            exe_dir = Path(sys.executable).resolve().parent
            candidates = [exe_dir, exe_dir.parent, Path.cwd()]
            for candidate in candidates:
                if (candidate / "main.py").exists() and (candidate / "core").exists():
                    return candidate
            runtime_dir = exe_dir / "VinaLab_runtime"
            BootstrapWindow._materialize_runtime(runtime_dir)
            if (runtime_dir / "main.py").exists() and (runtime_dir / "core").exists():
                return runtime_dir
            return exe_dir
        return Path(__file__).resolve().parent

    @staticmethod
    def _python_command() -> list[str]:
        """Return a usable Python launcher command for retrying the source launcher.

        Prefers the Windows ``py -3`` launcher, then ``python``/``python3`` on
        PATH, so the retry works on machines where only one of them is
        registered. Returned as argv tokens for ``subprocess``.
        """
        for candidate in (["py", "-3"], ["python"], ["python3"]):
            if shutil.which(candidate[0]):
                return candidate
        return ["python"]

    @staticmethod
    def _materialize_runtime(runtime_dir: Path) -> None:
        """Copy bundled source files from PyInstaller temp storage into a stable runtime dir."""
        bundle_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
        runtime_dir.mkdir(parents=True, exist_ok=True)
        for file_name in ("main.py", "mainwindow.py"):
            source = bundle_dir / file_name
            if source.exists():
                shutil.copy2(source, runtime_dir / file_name)
        for dir_name in ("core", "tabs", "ui", "config", "tools"):
            source_dir = bundle_dir / dir_name
            target_dir = runtime_dir / dir_name
            if source_dir.exists():
                shutil.copytree(source_dir, target_dir, dirs_exist_ok=True)

    def _load_lang(self) -> str:
        """Load the bootstrap language from user preferences."""
        prefs_path = self.app_dir / "config" / "user_prefs.json"
        return I18n.load_lang(str(prefs_path))

    def _environment_already_ready(self) -> bool:
        """Return True when the last environment report is fully ready."""
        status_path = self.app_dir / "logs" / "environment_status.json"
        if not status_path.exists():
            return False
        try:
            report = json.loads(status_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return False
        if not report.get("all_ready"):
            return False
        try:
            from core.environment_manager import EnvironmentManager

            manager = EnvironmentManager(self.app_dir)
            return not manager.check_missing() and bool(
                manager.verify_autodock_vina().get("ok")
            )
        except Exception:
            return False

    def _launch_main_from_status(self) -> None:
        """Launch the main app directly on future runs when the environment is ready."""
        python_path = (
            self.app_dir
            / ".venv"
            / ("Scripts" if sys.platform.startswith("win") else "bin")
            / ("python.exe" if sys.platform.startswith("win") else "python")
        )
        subprocess.Popen(
            [str(python_path), str(self.app_dir / "main.py")],
            cwd=self.app_dir,
            creationflags=NO_WINDOW,
        )


def main() -> int:
    """Run the VinaLab bootstrap launcher."""
    BootstrapWindow().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
