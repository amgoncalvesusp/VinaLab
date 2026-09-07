"""Setuptools backend staging platform-appropriate tools inside the core package."""

import shutil
import sys
from pathlib import Path

from build_support import tool_files
from setuptools import setup
from setuptools.build_meta import _BuildMetaBackend
from setuptools.command.build_py import build_py
from setuptools.command.sdist import sdist
from wheel.bdist_wheel import bdist_wheel

ROOT = Path(__file__).resolve().parents[1]


class BuildPy(build_py):
    def run(self):
        super().run()
        destination = Path(self.build_lib) / "vinalab_core" / "_bundled"
        # A reused Windows build tree must never contaminate a Linux wheel.
        if destination.exists():
            if not destination.resolve().is_relative_to(Path(self.build_lib).resolve()):
                raise RuntimeError("Unsafe build resource path")
            shutil.rmtree(destination)
        for source in tool_files(ROOT, sys.platform):
            target = destination / source.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)


class Sdist(sdist):
    def make_release_tree(self, base_dir, files):
        extra = [str(p.relative_to(ROOT)) for folder in ("tools", "packaging")
                 for p in (ROOT / folder).rglob("*")
                 if p.is_file() and "__pycache__" not in p.parts]
        super().make_release_tree(base_dir, sorted(set(files) | set(extra)))


class Wheel(bdist_wheel):
    def finalize_options(self):
        super().finalize_options()
        if sys.platform == "win32":
            self.root_is_pure = False

    def get_tag(self):
        if sys.platform == "win32":
            if sys.maxsize <= 2**32:
                raise RuntimeError("Bundled Windows engines require x64 Python")
            return "py3", "none", "win_amd64"
        return super().get_tag()


class Backend(_BuildMetaBackend):
    def run_setup(self, setup_script="setup.py"):
        setup(cmdclass={"build_py": BuildPy, "sdist": Sdist, "bdist_wheel": Wheel})


_backend = Backend()
build_wheel = _backend.build_wheel
build_sdist = _backend.build_sdist
build_editable = _backend.build_editable
get_requires_for_build_wheel = _backend.get_requires_for_build_wheel
get_requires_for_build_sdist = _backend.get_requires_for_build_sdist
get_requires_for_build_editable = _backend.get_requires_for_build_editable
prepare_metadata_for_build_wheel = _backend.prepare_metadata_for_build_wheel
prepare_metadata_for_build_editable = _backend.prepare_metadata_for_build_editable
