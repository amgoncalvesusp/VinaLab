"""Validate and publish molecular conversion outputs without damaging inputs."""

from functools import wraps
import math
from pathlib import Path
import tempfile

from core.file_utils import VALID_AUTODOCK_TYPES, validate_ligand_pdbqt


def validate_prepared_pdbqt(path: Path, role: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    atoms = [line for line in lines if line.startswith(("ATOM  ", "HETATM"))]
    if not atoms:
        raise ValueError("O PDBQT não contém átomos.")
    for line in atoms:
        values = [float(line[30:38]), float(line[38:46]), float(line[46:54]), float(line[70:76])]
        if not all(math.isfinite(value) for value in values):
            raise ValueError("O PDBQT contém coordenadas ou cargas não finitas.")
        if line[77:].strip() not in VALID_AUTODOCK_TYPES:
            raise ValueError("O PDBQT contém um tipo atômico não suportado pelo Vina.")
    tags = [line.split()[0] for line in lines if line.strip()]
    if role == "ligand":
        validate_ligand_pdbqt(path)
        if tags.count("ROOT") != 1 or tags.count("ENDROOT") != 1 or tags.count("TORSDOF") != 1:
            raise ValueError("O PDBQT do ligante não contém uma árvore de torsões única.")
    elif any(tag in tags for tag in ("ROOT", "BRANCH", "TORSDOF")):
        raise ValueError("O receptor rígido não pode conter torsões de ligante.")


def atomic_conversion(role):
    """Stage beside the destination and replace only a fully validated result."""
    def decorate(function):
        @wraps(function)
        def wrapped(input_path, output_path, *args, **kwargs):
            from core.converter import ConversionResult

            source, target = Path(input_path), Path(output_path)
            try:
                if source.resolve() == target.resolve() or (target.exists() and source.samefile(target)):
                    raise ValueError("Entrada e saída devem ser arquivos diferentes.")
                target.parent.mkdir(parents=True, exist_ok=True)
                with tempfile.TemporaryDirectory(prefix=".vinalab-", dir=target.parent) as directory:
                    staged = Path(directory) / "prepared.pdbqt"
                    result = function(source, staged, *args, **kwargs)
                    if result is None:
                        return None
                    if result.success:
                        actual_role = role
                        if role == "dynamic":
                            receptor = kwargs.get("receptor", args[0] if args else False)
                            actual_role = "receptor" if receptor else "ligand"
                        validate_prepared_pdbqt(staged, actual_role)
                        staged.replace(target)
                    return ConversionResult(result.success, target, result.log, result.errors)
            except Exception as exc:
                return ConversionResult(False, target, "", f"Falha na conversão: {exc}")
        return wrapped
    return decorate
