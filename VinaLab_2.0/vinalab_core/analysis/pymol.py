"""Optional PyMOL export using Python literals, not interpolated PML commands."""
import json
import shutil
import subprocess
from pathlib import Path
from tempfile import mkdtemp


def _path_literal(path):
    path = Path(path).resolve()
    if not path.is_file():
        raise ValueError(f"Structure file does not exist: {path}")
    if path.suffix.lower() not in {".pdb", ".pdbqt", ".sdf", ".mol", ".mol2", ".xyz"}:
        raise ValueError("Only molecular data files may be loaded into PyMOL")
    return json.dumps(str(path), ensure_ascii=True)


def export_pymol(receptor_path, pose_paths, output_path, *, reference=None, search_box=None):
    pose_paths = tuple(pose_paths)
    lines = ["python", "from pymol import cmd", f"cmd.load({_path_literal(receptor_path)}, 'receptor')"]
    for index, path in enumerate(pose_paths, 1):
        lines.append(f"cmd.load({_path_literal(path)}, 'pose_{index}')")
    if reference is not None:
        lines.append(f"cmd.load({_path_literal(reference)}, 'reference')")
    if search_box is not None:
        lines.extend(_box_lines(search_box))
    lines.extend(["cmd.hide('everything', 'all')", "cmd.show('cartoon', 'receptor')",
        "cmd.show('sticks', 'pose_*')", "cmd.show('sticks', 'reference')", "cmd.zoom('all')", "python end", ""])
    output = Path(output_path)
    if output.suffix.lower() != ".pml":
        raise ValueError("PyMOL script output must end in .pml")
    if output.resolve() in {Path(receptor_path).resolve(), *(Path(p).resolve() for p in pose_paths)}:
        raise ValueError("Export must not overwrite molecular input")
    with output.open("x", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
    return output


def pymol_launch_arguments(script_path):
    script = Path(script_path).resolve()
    if script.suffix.lower() != ".pml" or not script.is_file():
        raise ValueError("Expected an existing .pml script")
    executable = shutil.which("pymol")
    return (executable, str(script)) if executable else None


def _box_lines(box):
    import math
    from itertools import product
    if isinstance(box, dict):
        center, size = box["center"], box["size"]
    elif hasattr(box, "center"):
        center, size = box.center, box.size
    else:
        center = (box.center_x, box.center_y, box.center_z)
        size = (box.size_x, box.size_y, box.size_z)
    center, size = tuple(map(float, center)), tuple(map(float, size))
    if len(center) != 3 or len(size) != 3 or not all(math.isfinite(x) for x in (*center, *size)) or min(size) <= 0:
        raise ValueError("Invalid PyMOL search box")
    corners = tuple(tuple(c + s * sign / 2 for c, s, sign in zip(center, size, signs)) for signs in product((-1, 1), repeat=3))
    vertices = [point for i, a in enumerate(corners) for b in corners[i+1:]
        if sum(x != y for x, y in zip(a, b)) == 1 for point in (a, b)]
    return ["from pymol.cgo import BEGIN, END, LINES, VERTEX, COLOR",
        "box = [BEGIN, LINES, COLOR, 0.2, 0.8, 0.3]",
        *[f"box.extend([VERTEX, {x!r}, {y!r}, {z!r}])" for x, y, z in vertices],
        "box.append(END)", "cmd.load_cgo(box, 'search_box')"]


def launch_pymol(receptor, poses, reference=None, search_box=None):
    """Export a persistent unique script and launch only when PyMOL is on PATH.

    Returns the script Path even without PyMOL, so the UI can offer manual opening.
    """
    directory = Path(mkdtemp(prefix="vinalab-pymol-"))
    script = export_pymol(receptor, poses, directory / "view.pml", reference=reference, search_box=search_box)
    arguments = pymol_launch_arguments(script)
    if arguments is not None:
        subprocess.Popen(arguments, shell=False)
    return script
