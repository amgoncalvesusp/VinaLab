"""File and PDBQT validation helpers for VinaLab."""

from collections import Counter
from dataclasses import dataclass
from pathlib import Path


ALLOWED_PDBQT_TAGS = {
    "ATOM",
    "HETATM",
    "REMARK",
    "ROOT",
    "ENDROOT",
    "BRANCH",
    "ENDBRANCH",
    "TORSDOF",
    "MODEL",
    "ENDMDL",
    "TER",
    "END",
}

RECEPTOR_ONLY_TAGS = {
    "ATOM",
    "HETATM",
    "REMARK",
    "MODEL",
    "ENDMDL",
    "TER",
    "END",
}

RECEPTOR_ROLES = {"receptor", "rigid_receptor", "flex_receptor"}

VALID_AUTODOCK_TYPES = {
    "C",
    "A",
    "N",
    "NA",
    "NS",
    "OA",
    "OS",
    "S",
    "SA",
    "P",
    "F",
    "Cl",
    "CL",
    "Br",
    "BR",
    "I",
    "H",
    "HD",
    "HS",
    "Mg",
    "MG",
    "Mn",
    "MN",
    "Zn",
    "ZN",
    "Ca",
    "CA",
    "Fe",
    "FE",
    "Cu",
    "CU",
}

AUTODOCK_TYPE_ALIASES = {
    "CL": "Cl",
    "BR": "Br",
    "MG": "Mg",
    "MN": "Mn",
    "ZN": "Zn",
    "CA": "Ca",
    "FE": "Fe",
    "CU": "Cu",
}

RESIDUE_ONE_LETTER = {
    "ALA": "A",
    "ARG": "R",
    "ASN": "N",
    "ASP": "D",
    "CYS": "C",
    "GLN": "Q",
    "GLU": "E",
    "GLY": "G",
    "HIS": "H",
    "ILE": "I",
    "LEU": "L",
    "LYS": "K",
    "MET": "M",
    "PHE": "F",
    "PRO": "P",
    "SER": "S",
    "THR": "T",
    "TRP": "W",
    "TYR": "Y",
    "VAL": "V",
}


@dataclass(frozen=True)
class PdbqtSanitizationResult:
    """Result of removing records that AutoDock Vina cannot parse."""

    path: Path
    changed: bool
    removed_counts: dict[str, int]
    normalized_counts: dict[str, int]


@dataclass(frozen=True)
class PdbqtLigandIntegrity:
    """Connectivity summary for one ligand PDBQT input."""

    atom_count: int
    heavy_atom_count: int
    model_count: int
    component_count: int
    component_sizes: tuple[int, ...]


def is_pdbqt_file(path: Path | None) -> bool:
    """Return True when path exists and points to a PDBQT file."""
    return bool(path and path.exists() and path.is_file() and path.suffix.lower() == ".pdbqt")


def validate_optional_pdbqt(path: Path | None) -> bool:
    """Return True when an optional path is empty or a valid PDBQT file."""
    return path is None or str(path) == "" or is_pdbqt_file(path)


def discover_pdbqt_files(folder: Path | None) -> list[Path]:
    """Recursively discover PDBQT files under a folder."""
    if not folder or not folder.exists() or not folder.is_dir():
        return []
    return sorted(item for item in folder.rglob("*.pdbqt") if item.is_file())


def safe_stem(path: Path) -> str:
    """Return a filesystem-safe stem for generated output files."""
    cleaned = "".join(char if char.isalnum() or char in ("-", "_") else "_" for char in path.stem)
    return cleaned or "ligand"


def ensure_directory(path: Path) -> Path:
    """Create a directory if necessary and return its resolved path."""
    path.mkdir(parents=True, exist_ok=True)
    return path.resolve()


def pdbqt_coordinate_bounds(paths: list[Path]) -> tuple[tuple[float, float], ...] | None:
    """Return min/max X, Y, Z bounds across one or more PDBQT files."""
    coordinates: list[tuple[float, float, float]] = []
    for path in paths:
        coordinates.extend(pdbqt_coordinates(path))
    if not coordinates:
        return None
    return tuple((min(values), max(values)) for values in zip(*coordinates))


def pdbqt_coordinates(path: Path) -> list[tuple[float, float, float]]:
    """Parse atom coordinates from a PDBQT file."""
    coordinates: list[tuple[float, float, float]] = []
    for line in clean_pdbqt_text(path.read_text(encoding="utf-8", errors="replace")).splitlines():
        if not line.startswith(("ATOM", "HETATM")):
            continue
        try:
            coordinates.append((float(line[30:38]), float(line[38:46]), float(line[46:54])))
        except ValueError:
            parts = line.split()
            try:
                coordinates.append((float(parts[5]), float(parts[6]), float(parts[7])))
            except (IndexError, ValueError):
                continue
    return coordinates


def pdbqt_receptor_atoms(path: Path) -> list[dict]:
    """Parse receptor atoms grouped by residue metadata from a PDBQT file."""
    atoms: list[dict] = []
    for line in clean_pdbqt_text(path.read_text(encoding="utf-8", errors="replace")).splitlines():
        if not line.startswith(("ATOM", "HETATM")):
            continue
        try:
            x = float(line[30:38])
            y = float(line[38:46])
            z = float(line[46:54])
        except ValueError:
            parts = line.split()
            try:
                x, y, z = float(parts[5]), float(parts[6]), float(parts[7])
            except (IndexError, ValueError):
                continue
        resname = line[17:20].strip().upper() or _token_at(line, 3, "UNK").upper()
        chain_id = line[21].strip() if len(line) > 21 else ""
        residue_number = line[22:26].strip() or _token_at(line, 4, "")
        atom_name = line[12:16].strip() or _token_at(line, 2, "ATOM")
        atoms.append(
            {
                "atom_name": atom_name,
                "resname": resname,
                "one_letter": RESIDUE_ONE_LETTER.get(resname, "X"),
                "chain_id": chain_id,
                "residue_number": residue_number,
                "x": x,
                "y": y,
                "z": z,
            }
        )
    return atoms


def _token_at(line: str, index: int, default: str) -> str:
    """Return a split token safely."""
    parts = line.split()
    return parts[index] if len(parts) > index else default


def clean_pdbqt_text(text: str) -> str:
    """Remove byte padding that some Vina CLI builds leave in PDBQT files."""
    return text.replace("\x00", "")


def clean_pdbqt_file(path: Path) -> bool:
    """Remove NUL padding from a PDBQT file in place and report whether it changed."""
    original = path.read_text(encoding="utf-8", errors="replace")
    cleaned = clean_pdbqt_text(original)
    if cleaned == original:
        return False
    path.write_text(cleaned, encoding="utf-8")
    return True


def validate_ligand_pdbqt(path: Path) -> PdbqtLigandIntegrity:
    """Validate that a ligand PDBQT represents one connected ligand, not multiple poses/fragments."""
    integrity = pdbqt_ligand_integrity(path)
    if integrity.atom_count == 0:
        raise ValueError(f"O PDBQT do ligante não contém átomos: {path}")
    if integrity.model_count > 1:
        raise ValueError(
            f"O PDBQT do ligante contém {integrity.model_count} blocos MODEL. "
            "Este é um arquivo de saída Vina com múltiplas poses, não um ligante único. "
            "Exporte/selecione uma pose antes de usá-la como ligante."
        )
    if integrity.component_count > 1:
        sizes = ", ".join(str(size) for size in integrity.component_sizes)
        raise ValueError(
            f"O PDBQT do ligante contém {integrity.component_count} componentes de átomos pesados desconectados "
            f"(tamanhos dos componentes: {sizes}). O Vina pode mover fragmentos desconectados de forma independente. "
            "Prepare um ligante covalentemente conectado ou remova sais/contraíons antes do docking."
        )
    return integrity


def pdbqt_ligand_integrity(path: Path) -> PdbqtLigandIntegrity:
    """Return a conservative connectivity summary for one ligand PDBQT file."""
    text = clean_pdbqt_text(path.read_text(encoding="utf-8", errors="replace"))
    lines = text.splitlines()
    model_count = sum(1 for line in lines if line.startswith("MODEL"))
    ligand_lines = _first_model_or_all_lines(lines)
    atoms: list[dict] = []
    forced_bonds: set[tuple[int, int]] = set()
    for line in ligand_lines:
        if line.startswith("BRANCH"):
            bond = _branch_bond(line)
            if bond is not None:
                forced_bonds.add(bond)
            continue
        if line.startswith(("ATOM", "HETATM")):
            atom = _pdbqt_atom_for_integrity(line)
            if atom is not None:
                atoms.append(atom)

    heavy_atoms = [atom for atom in atoms if atom["element"].upper() != "H"]
    component_sizes = _component_sizes(heavy_atoms, forced_bonds)
    return PdbqtLigandIntegrity(
        atom_count=len(atoms),
        heavy_atom_count=len(heavy_atoms),
        model_count=model_count,
        component_count=len(component_sizes),
        component_sizes=tuple(sorted(component_sizes, reverse=True)),
    )


def _first_model_or_all_lines(lines: list[str]) -> list[str]:
    """Return the first MODEL block when present, otherwise all lines."""
    if not any(line.startswith("MODEL") for line in lines):
        return lines
    selected: list[str] = []
    inside_first_model = False
    for line in lines:
        if line.startswith("MODEL"):
            if selected:
                break
            inside_first_model = True
            continue
        if line.startswith("ENDMDL") and inside_first_model:
            break
        if inside_first_model:
            selected.append(line)
    return selected


def _branch_bond(line: str) -> tuple[int, int] | None:
    """Parse a BRANCH line into a forced bond edge."""
    parts = line.split()
    if len(parts) < 3:
        return None
    try:
        left = int(parts[1])
        right = int(parts[2])
    except ValueError:
        return None
    return tuple(sorted((left, right)))


def _pdbqt_atom_for_integrity(line: str) -> dict | None:
    """Parse the atom fields needed for ligand connectivity checks."""
    try:
        serial = int(line[6:11])
        name = line[12:16].strip()
        x = float(line[30:38])
        y = float(line[38:46])
        z = float(line[46:54])
    except ValueError:
        parts = line.split()
        if len(parts) < 8:
            return None
        try:
            serial = int(parts[1])
            name = parts[2]
            x = float(parts[5])
            y = float(parts[6])
            z = float(parts[7])
        except (IndexError, ValueError):
            return None
    atom_type = line.rsplit(maxsplit=1)[-1] if line.split() else ""
    return {
        "serial": serial,
        "element": _autodock_type_to_element(name, atom_type),
        "x": x,
        "y": y,
        "z": z,
    }


def _component_sizes(atoms: list[dict], forced_bonds: set[tuple[int, int]]) -> list[int]:
    """Return connected-component sizes using BRANCH bonds plus conservative distance bonds."""
    if not atoms:
        return []
    serial_to_index = {atom["serial"]: index for index, atom in enumerate(atoms)}
    graph: list[set[int]] = [set() for _atom in atoms]
    for left_serial, right_serial in forced_bonds:
        left_index = serial_to_index.get(left_serial)
        right_index = serial_to_index.get(right_serial)
        if left_index is not None and right_index is not None:
            graph[left_index].add(right_index)
            graph[right_index].add(left_index)
    for left_index, left_atom in enumerate(atoms):
        for right_index in range(left_index + 1, len(atoms)):
            if _atoms_likely_connected(left_atom, atoms[right_index]):
                graph[left_index].add(right_index)
                graph[right_index].add(left_index)

    seen: set[int] = set()
    sizes: list[int] = []
    for index in range(len(atoms)):
        if index in seen:
            continue
        stack = [index]
        seen.add(index)
        size = 0
        while stack:
            current = stack.pop()
            size += 1
            for neighbour in graph[current]:
                if neighbour not in seen:
                    seen.add(neighbour)
                    stack.append(neighbour)
        sizes.append(size)
    return sizes


def _atoms_likely_connected(left_atom: dict, right_atom: dict) -> bool:
    """Return True when two non-hydrogen atoms are plausibly covalently bonded."""
    dx = float(left_atom["x"]) - float(right_atom["x"])
    dy = float(left_atom["y"]) - float(right_atom["y"])
    dz = float(left_atom["z"]) - float(right_atom["z"])
    distance = (dx * dx + dy * dy + dz * dz) ** 0.5
    if distance < 0.35:
        return False
    threshold = _covalent_radius(left_atom["element"]) + _covalent_radius(right_atom["element"]) + 0.45
    return distance <= min(threshold, 2.25)


def _autodock_type_to_element(atom_name: str, atom_type: str) -> str:
    """Convert AutoDock atom types to chemical elements for validation."""
    token = "".join(character for character in atom_type.strip() if character.isalpha()).upper()
    if token == "A":
        return "C"
    if token.startswith("CL"):
        return "Cl"
    if token.startswith("BR"):
        return "Br"
    if token[:2] in {"OA", "OS"}:
        return "O"
    if token[:2] in {"NA", "NS"}:
        return "N"
    if token[:2] == "SA":
        return "S"
    if token[:2] in {"HD", "HS"}:
        return "H"
    if token[:2] in {"MG", "ZN", "FE", "CA", "MN", "CU"}:
        return token[:2].title()
    if token:
        return token[0].upper()
    letters = "".join(character for character in atom_name if character.isalpha()).upper()
    return letters[:1] if letters else "C"


def _covalent_radius(element: str) -> float:
    """Return approximate covalent radius in Angstrom for connectivity checks."""
    return {
        "H": 0.31,
        "C": 0.76,
        "N": 0.71,
        "O": 0.66,
        "S": 1.05,
        "P": 1.07,
        "F": 0.57,
        "CL": 1.02,
        "BR": 1.20,
        "I": 1.39,
        "MG": 1.30,
        "ZN": 1.22,
        "FE": 1.24,
        "CA": 1.74,
    }.get(element.upper(), 0.77)


def _pdbqt_charge_token(line: str) -> str:
    """Return the textual charge token from a PDBQT ATOM/HETATM line.

    AutoDock PDBQT places the partial charge in the second-to-last whitespace
    token (column ~71-76 in fixed-width layout). Returns "" when no token can
    be isolated.
    """
    parts = line.rstrip("\n").rstrip().split()
    if len(parts) < 2:
        return ""
    return parts[-2]


def _pdbqt_atom_type_token(line: str) -> str:
    """Return the AutoDock atom type token (last column) from a PDBQT line."""
    parts = line.rstrip("\n").rstrip().split()
    return parts[-1] if parts else ""


def validate_pdbqt_charges(filepath: Path) -> bool:
    """Return True when every ATOM/HETATM line in `filepath` has a parseable float charge.

    Pre-flight check called before handing a PDBQT to the Vina CLI. Empty token,
    non-numeric token (e.g., a stray atom type or chain ID slid into column 9),
    or a missing column counts as failure.
    """
    try:
        text = clean_pdbqt_text(filepath.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return False
    for line in text.splitlines():
        if not line.startswith(("ATOM", "HETATM")):
            continue
        charge_token = _pdbqt_charge_token(line)
        if not charge_token:
            return False
        try:
            float(charge_token)
        except ValueError:
            return False
    return True


def repair_pdbqt_charges(filepath: Path, role: str = "ligand") -> bool:
    """Rewrite `filepath` so every ATOM/HETATM line has a numeric charge column.

    For receptors (role in RECEPTOR_ROLES), missing charges are filled with 0.000.
    For ligands, the function tries to recompute Gasteiger charges via RDKit and
    falls back to 0.000 when RDKit cannot map the atoms. Returns True when the
    file is left in a Vina-parseable state.
    """
    try:
        text = clean_pdbqt_text(filepath.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return False

    repaired_lines: list[str] = []
    needs_repair = False
    for line in text.splitlines():
        if not line.startswith(("ATOM", "HETATM")):
            repaired_lines.append(line)
            continue
        charge_token = _pdbqt_charge_token(line)
        try:
            float(charge_token)
            repaired_lines.append(line)
            continue
        except ValueError:
            needs_repair = True

        atom_type = _pdbqt_atom_type_token(line)
        body = line.rstrip("\n").rstrip()
        if atom_type and body.endswith(atom_type):
            body = body[: -len(atom_type)].rstrip()
        if charge_token and body.endswith(charge_token):
            body = body[: -len(charge_token)].rstrip()
        repaired_lines.append(f"{body} {'0.000':>7} {atom_type or 'C'}")

    if not needs_repair:
        return True

    if role not in RECEPTOR_ROLES:
        ligand_repaired = _rewrite_ligand_charges_with_rdkit(filepath, repaired_lines)
        if ligand_repaired is None:
            ligand_repaired = _rewrite_ligand_charges_with_obabel(filepath, repaired_lines)
        if ligand_repaired is not None:
            repaired_lines = ligand_repaired

    filepath.write_text("\n".join(repaired_lines) + "\n", encoding="utf-8")
    return validate_pdbqt_charges(filepath)


def _rewrite_ligand_charges_with_rdkit(filepath: Path, current_lines: list[str]) -> list[str] | None:
    """Compute Gasteiger charges via RDKit and rewrite PDBQT charge columns.

    PDBQT files keep AutoDock atom-type tokens (e.g., HD, OA, NA) in the last
    column that RDKit's PDB parser does not understand. The function strips
    those tokens into a temporary PDB before calling RDKit, computes Gasteiger
    charges, then rewrites the original PDBQT lines preserving atom types.
    Returns None when atom counts diverge or RDKit fails entirely.
    """
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem
    except ImportError:
        return None

    pdb_lines: list[str] = []
    for line in current_lines:
        if line.startswith(("ATOM", "HETATM")) and len(line) >= 78:
            pdb_lines.append(line[:66])
        elif line.startswith(("ATOM", "HETATM")):
            pdb_lines.append(line)
        elif line.startswith(("ROOT", "ENDROOT", "BRANCH", "ENDBRANCH", "TORSDOF")):
            continue
        else:
            pdb_lines.append(line)

    import tempfile

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".pdb", delete=False, encoding="utf-8"
    ) as handle:
        handle.write("\n".join(pdb_lines) + "\n")
        temp_pdb = Path(handle.name)
    try:
        mol = Chem.MolFromPDBFile(str(temp_pdb), removeHs=False, sanitize=False)
        if mol is None:
            return None
        try:
            Chem.SanitizeMol(mol)
        except Exception:  # noqa: BLE001 - fall through to partial sanitize
            try:
                Chem.SanitizeMol(
                    mol,
                    sanitizeOps=Chem.SanitizeFlags.SANITIZE_ALL
                    ^ Chem.SanitizeFlags.SANITIZE_PROPERTIES,
                )
            except Exception:  # noqa: BLE001
                return None
        try:
            AllChem.ComputeGasteigerCharges(mol)
        except Exception:  # noqa: BLE001
            return None

        charges: list[float] = []
        for atom in mol.GetAtoms():
            if not atom.HasProp("_GasteigerCharge"):
                return None
            try:
                value = float(atom.GetProp("_GasteigerCharge"))
            except ValueError:
                return None
            if value != value:  # NaN
                return None
            charges.append(value)
    finally:
        try:
            temp_pdb.unlink(missing_ok=True)
        except OSError:
            pass

    atom_indices = [
        index for index, line in enumerate(current_lines) if line.startswith(("ATOM", "HETATM"))
    ]
    if len(atom_indices) != len(charges):
        return None

    updated = list(current_lines)
    for line_index, charge in zip(atom_indices, charges):
        original = updated[line_index]
        atom_type = _pdbqt_atom_type_token(original)
        body = original.rstrip("\n").rstrip()
        old_charge = _pdbqt_charge_token(original)
        if atom_type and body.endswith(atom_type):
            body = body[: -len(atom_type)].rstrip()
        if old_charge and body.endswith(old_charge):
            body = body[: -len(old_charge)].rstrip()
        updated[line_index] = f"{body} {charge:7.3f} {atom_type or 'C'}"
    return updated


def _rewrite_ligand_charges_with_obabel(filepath: Path, current_lines: list[str]) -> list[str] | None:
    """Open Babel fallback: regenerate PDBQT and copy its charges into current lines."""
    import shutil
    import subprocess
    import sys

    obabel = shutil.which("obabel")
    if obabel is None:
        candidate = Path(sys.executable).resolve().parent / (
            "obabel.exe" if sys.platform.startswith("win") else "obabel"
        )
        obabel = str(candidate) if candidate.exists() else None
    if obabel is None:
        return None

    import tempfile

    no_window = subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0
    with tempfile.NamedTemporaryFile(suffix=".pdbqt", delete=False) as handle:
        regen_path = Path(handle.name)
    try:
        completed = subprocess.run(
            [obabel, str(filepath), "-O", str(regen_path), "--partialcharge", "gasteiger"],
            capture_output=True,
            text=True,
            check=False,
            creationflags=no_window,
        )
        if completed.returncode != 0 or not regen_path.exists():
            return None
        regen_lines = clean_pdbqt_text(
            regen_path.read_text(encoding="utf-8", errors="replace")
        ).splitlines()
    finally:
        try:
            regen_path.unlink(missing_ok=True)
        except OSError:
            pass

    regen_atom_lines = [line for line in regen_lines if line.startswith(("ATOM", "HETATM"))]
    original_atom_indices = [
        index for index, line in enumerate(current_lines) if line.startswith(("ATOM", "HETATM"))
    ]
    if len(regen_atom_lines) != len(original_atom_indices):
        return None

    updated = list(current_lines)
    for original_index, regen_line in zip(original_atom_indices, regen_atom_lines):
        new_charge = _pdbqt_charge_token(regen_line)
        try:
            charge_value = float(new_charge)
        except ValueError:
            continue
        original_line = updated[original_index]
        atom_type = _pdbqt_atom_type_token(original_line)
        body = original_line.rstrip("\n").rstrip()
        old_charge = _pdbqt_charge_token(original_line)
        if atom_type and body.endswith(atom_type):
            body = body[: -len(atom_type)].rstrip()
        if old_charge and body.endswith(old_charge):
            body = body[: -len(old_charge)].rstrip()
        updated[original_index] = f"{body} {charge_value:7.3f} {atom_type or 'C'}"
    return updated


def sanitize_pdbqt_for_vina(input_path: Path, output_directory: Path, role: str) -> PdbqtSanitizationResult:
    """Return a Vina-compatible PDBQT path, removing unsupported PDB records if needed."""
    removed_tags: Counter[str] = Counter()
    normalized_types: Counter[str] = Counter()
    kept_lines: list[str] = []
    original_text = input_path.read_text(encoding="utf-8", errors="replace")
    nul_count = original_text.count("\x00")
    if nul_count:
        removed_tags["NUL"] = nul_count
    original_lines = clean_pdbqt_text(original_text).splitlines()

    allowed_tags = RECEPTOR_ONLY_TAGS if role in RECEPTOR_ROLES else ALLOWED_PDBQT_TAGS
    for line in original_lines:
        if not line.strip():
            kept_lines.append(line)
            continue
        tag = line.split(maxsplit=1)[0].upper()
        if tag in allowed_tags:
            if tag in {"ATOM", "HETATM"}:
                sanitized_line, normalized_from = _normalize_autodock_type(line)
                kept_lines.append(sanitized_line)
                if normalized_from:
                    normalized_types[normalized_from] += 1
            else:
                kept_lines.append(line)
        else:
            removed_tags[tag] += 1

    if not removed_tags and not normalized_types:
        return PdbqtSanitizationResult(path=input_path, changed=False, removed_counts={}, normalized_counts={})

    sanitized_dir = output_directory / "sanitized_inputs"
    sanitized_dir.mkdir(parents=True, exist_ok=True)
    sanitized_path = sanitized_dir / f"{safe_stem(input_path)}_{role}_vina.pdbqt"
    sanitized_path.write_text("\n".join(kept_lines) + "\n", encoding="utf-8")
    return PdbqtSanitizationResult(
        path=sanitized_path,
        changed=True,
        removed_counts=dict(sorted(removed_tags.items())),
        normalized_counts=dict(sorted(normalized_types.items())),
    )


def _normalize_autodock_type(line: str) -> tuple[str, str | None]:
    """Normalize common non-AutoDock atom type annotations in ATOM/HETATM records."""
    parts = line.rsplit(maxsplit=1)
    if len(parts) != 2:
        return line, None
    prefix, atom_type = parts
    normalized = _valid_autodock_type(atom_type) or _infer_type_from_token(atom_type)
    if normalized is None or normalized == atom_type:
        return line, None
    start = line.rfind(atom_type)
    if start >= 0:
        return f"{line[:start]}{normalized:<{len(atom_type)}}{line[start + len(atom_type):]}", atom_type
    return f"{prefix} {normalized}", atom_type


def _valid_autodock_type(atom_type: str) -> str | None:
    """Return a canonical AutoDock type when the token is already valid."""
    if atom_type in VALID_AUTODOCK_TYPES:
        return AUTODOCK_TYPE_ALIASES.get(atom_type, atom_type)
    return None


def _infer_type_from_token(atom_type: str) -> str | None:
    """Infer a basic AutoDock atom type from common PDB element annotations."""
    letters = "".join(character for character in atom_type if character.isalpha()).upper()
    if not letters:
        return None
    if letters.startswith("CL"):
        return "Cl"
    if letters.startswith("BR"):
        return "Br"
    if letters[:2] in AUTODOCK_TYPE_ALIASES:
        return AUTODOCK_TYPE_ALIASES[letters[:2]]
    first = letters[0]
    if first in {"C", "N", "O", "S", "P", "F", "I", "H"}:
        return first
    return None
