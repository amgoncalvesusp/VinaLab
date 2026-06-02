# -*- coding: utf-8 -*-
"""Pure helpers for the results tab: PDBQT-to-view conversion, 3Dmol HTML, tooltips.

Extracted from results_tab.py to keep that module focused on the ResultsTab
widget. Everything here is free of ResultsTab state so it can be imported by both
the tab and the comparison/validation/export dialogs without a circular import.
"""

from __future__ import annotations

import html
import json
from pathlib import Path

from PySide6.QtWidgets import QTableWidget

from core.docking_engine import extract_pose_model
from core.file_utils import clean_pdbqt_text

HEADER_TOOLTIPS = {
    "Ligante": "Nome do arquivo do ligante submetido ao docking",
    "Rank da pose": "Classificação da pose pelo score de docking (1 = melhor)",
    "Energia de docking (kcal/mol)": "Energia de ligação estimada. Valores mais negativos indicam maior afinidade",
    "Score de docking (kcal/mol)": "Energia de ligação estimada. Valores mais negativos indicam maior afinidade",
    "Afinidade (kcal/mol)": "Energia de ligação estimada. Valores mais negativos indicam maior afinidade",
    "ItaVinaXGB-Lig": "Score de afinidade previsto pelo modelo ItaVinaXGB para o ligante",
    "RTMScore": "Score de docking por aprendizado de máquina (RTMScore). Mais negativo = melhor",
    "Vinardo": "Score de docking Vinardo. Mais negativo = melhor afinidade estimada",
    "D para melhor (RMSD)": "Desvio quadrático médio em relação à melhor pose. Valores baixos indicam poses similares",
    "RMSD para melhor pose": "Desvio quadrático médio em relação à melhor pose. Valores baixos indicam poses similares",
    "Fixada": "Indica se a pose foi fixada/marcada pelo usuário",
    "Notas": "Anotações manuais do usuário para esta pose",
    "Rank médio": "Média dos ranks atribuídos por todas as funções de pontuação",
    "Pontuação Borda": "Pontuação combinada pelo método Borda Count",
    "Contagem Borda": "Pontuação combinada pelo método Borda Count",
    "Consenso Z-score": "Z-score do consenso entre múltiplas funções de pontuação",
    "DP dos ranks": "Desvio padrão dos ranks entre as funções de pontuação. Valores baixos = maior concordância",
    "Divergência": "Classificação qualitativa da concordância entre os scores (ex: Robust = alta concordância)",
    "Resíduo": "Resíduo do receptor envolvido na interação com a pose selecionada",
    "Tipo de interação": "Categoria da interação receptor-ligante estimada para a pose selecionada",
    "Doador": "Átomo doador identificado na interação",
    "Aceptor": "Átomo aceptor identificado na interação",
    "Distância (Å)": "Distância estimada entre os átomos envolvidos na interação",
    "Ângulo": "Ângulo estimado da interação quando aplicável",
    "Frequência Top 10": "Frequência da interação entre as 10 melhores poses do ligante",
    "ID do cluster": "Identificador do cluster de poses por RMSD",
    "Tamanho": "Número de poses agrupadas neste cluster",
    "Melhor score": "Melhor score de docking entre as poses do cluster",
    "Pose representante": "Pose escolhida para representar o cluster",
    "Membros": "Ranks das poses agrupadas neste cluster",
    "Erro de pontuação": "Mensagem de erro retornada por uma função de pontuação, se houver",
}


def apply_header_tooltips(table: QTableWidget) -> None:
    """Apply pt-BR tooltips to every visible column header in a table."""
    for column in range(table.columnCount()):
        item = table.horizontalHeaderItem(column)
        if item is None:
            continue
        header = item.text()
        item.setToolTip(HEADER_TOOLTIPS.get(header, _generic_header_tooltip(header)))


def _generic_header_tooltip(header: str) -> str:
    """Return a pt-BR fallback tooltip for dynamic or secondary table columns."""
    normalized = header.lower()
    if "itavina" in normalized:
        return HEADER_TOOLTIPS["ItaVinaXGB-Lig"]
    if "rtmscore" in normalized:
        return HEADER_TOOLTIPS["RTMScore"]
    if "vinardo" in normalized:
        return HEADER_TOOLTIPS["Vinardo"]
    if "score" in normalized or "vina" in normalized or "affinity" in normalized:
        return "Score de docking desta função de pontuação. Valores mais negativos indicam maior afinidade"
    if "cluster" in normalized:
        return "Informação do agrupamento de poses por RMSD"
    return f"Coluna {header} da tabela"


def safe_export_name(name: str) -> str:
    """Return a filesystem-safe ligand name for exports."""
    cleaned = "".join(
        char if char.isalnum() or char in {"-", "_"} else "_"
        for char in Path(name).stem
    )
    return cleaned or "ligand"


def prepare_pose_view_files(row: dict, view_dir: Path) -> tuple[Path, Path]:
    """Extract one PDBQT pose and write PDB files for 3Dmol without bond-guessing converters."""
    output_file = Path(row.get("output_file", ""))
    receptor_file = Path(row.get("receptor_file", ""))
    if not output_file.is_absolute():
        output_file = output_file.resolve()
    if not receptor_file.is_absolute():
        receptor_file = receptor_file.resolve()
    if not output_file.exists():
        raise FileNotFoundError(
            f"Arquivo de saída da pose não encontrado: {output_file}"
        )
    if not receptor_file.exists():
        raise FileNotFoundError(f"Arquivo do receptor não encontrado: {receptor_file}")
    view_dir.mkdir(parents=True, exist_ok=True)
    pose_file = (
        view_dir
        / f"{safe_export_name(row['ligand_name'])}_pose{int(row['mode'])}.pdbqt"
    )
    pose_text = extract_pose_model(output_file, int(row["mode"]), include_model=False)
    if not any(
        line.startswith(("ATOM", "HETATM"))
        for line in clean_pdbqt_text(pose_text).splitlines()
    ):
        raise ValueError(
            "A pose selecionada não contém átomos PDBQT para visualização."
        )
    pose_file.write_text(pose_text, encoding="utf-8")
    receptor_pdb = view_dir / "receptor.pdb"
    pose_pdb = (
        view_dir / f"{safe_export_name(row['ligand_name'])}_pose{int(row['mode'])}.pdb"
    )
    receptor_pdb.write_text(
        pdbqt_text_to_view_pdb(
            receptor_file.read_text(encoding="utf-8", errors="replace"),
            include_conect=False,
        ),
        encoding="utf-8",
    )
    pose_pdb.write_text(
        pdbqt_text_to_view_pdb(pose_text, include_conect=True), encoding="utf-8"
    )
    if not _pdb_file_has_atoms(receptor_pdb) or not _pdb_file_has_atoms(pose_pdb):
        raise ValueError(
            "Erro ao carregar visualização 3D. Verifique os arquivos de entrada."
        )
    return receptor_pdb, pose_pdb


def _pdb_file_has_atoms(path: Path) -> bool:
    """Return True when a display PDB file contains atoms."""
    return any(
        line.startswith(("ATOM", "HETATM"))
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
    )


def pdbqt_text_to_view_pdb(text: str, include_conect: bool) -> str:
    """Convert PDBQT text to viewer-safe PDB, preserving coordinates and adding simple ligand CONECT records."""
    atoms: list[dict] = []
    forced_bonds: set[tuple[int, int]] = set()
    seen_model = False
    for line in clean_pdbqt_text(text).splitlines():
        if line.startswith("MODEL"):
            if seen_model:
                break
            seen_model = True
            continue
        if line.startswith("ENDMDL") and seen_model:
            break
        if line.startswith("BRANCH"):
            bond = _pdbqt_branch_bond(line)
            if bond is not None:
                forced_bonds.add(bond)
            continue
        if not line.startswith(("ATOM", "HETATM")):
            continue
        atom = _pdbqt_atom_record(line)
        if atom:
            atoms.append(atom)
    output_lines = [_format_view_pdb_atom(atom) for atom in atoms]
    if include_conect:
        output_lines.extend(_infer_conect_records(atoms, forced_bonds))
    output_lines.append("END")
    return "\n".join(output_lines) + "\n"


def _pdbqt_branch_bond(line: str) -> tuple[int, int] | None:
    """Parse the covalent edge encoded by a PDBQT BRANCH record."""
    parts = line.split()
    if len(parts) < 3:
        return None
    try:
        return tuple(sorted((int(parts[1]), int(parts[2]))))
    except ValueError:
        return None


def _pdbqt_atom_record(line: str) -> dict | None:
    """Parse one ATOM/HETATM PDBQT line into a normalized PDB atom record."""
    try:
        serial = int(line[6:11])
        name = line[12:16].strip() or "X"
        resname = line[17:20].strip() or "LIG"
        chain = (line[21].strip() if len(line) > 21 else "") or "A"
        resid = int((line[22:26].strip() or "1").split()[0])
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
            resname = parts[3] if len(parts) > 3 else "LIG"
            chain = parts[4] if len(parts) > 4 and not _is_number(parts[4]) else "A"
            resid = int(parts[5] if chain != "A" else parts[4])
            coordinate_offset = 6 if chain != "A" else 5
            x = float(parts[coordinate_offset])
            y = float(parts[coordinate_offset + 1])
            z = float(parts[coordinate_offset + 2])
        except (ValueError, IndexError):
            return None
    atom_type = line.rsplit(maxsplit=1)[-1] if line.split() else ""
    element = _element_from_atom(name, atom_type)
    return {
        "serial": serial,
        "name": name[:4],
        "resname": resname[:3],
        "chain": chain[:1],
        "resid": resid,
        "x": x,
        "y": y,
        "z": z,
        "element": element,
        "record": "HETATM" if line.startswith("HETATM") else "ATOM",
    }


def _format_view_pdb_atom(atom: dict) -> str:
    """Format one atom as a standards-compatible PDB line."""
    return (
        f"{atom['record']:<6}{int(atom['serial']):5d} {atom['name']:<4} {atom['resname']:>3} "
        f"{atom['chain']}{int(atom['resid']):4d}    "
        f"{float(atom['x']):8.3f}{float(atom['y']):8.3f}{float(atom['z']):8.3f}"
        f"  1.00  0.00          {atom['element']:>2}"
    )


def _infer_conect_records(
    atoms: list[dict], forced_bonds: set[tuple[int, int]] | None = None
) -> list[str]:
    """Infer conservative ligand connectivity from distance and covalent radii."""
    records: dict[int, list[int]] = {int(atom["serial"]): [] for atom in atoms}
    forced_bonds = forced_bonds or set()
    for left_serial, right_serial in forced_bonds:
        if left_serial in records and right_serial in records:
            records[left_serial].append(right_serial)
            records[right_serial].append(left_serial)
    for left_index, left_atom in enumerate(atoms):
        for right_atom in atoms[left_index + 1 :]:
            if _atoms_likely_bonded(left_atom, right_atom):
                left_serial = int(left_atom["serial"])
                right_serial = int(right_atom["serial"])
                if right_serial not in records[left_serial]:
                    records[left_serial].append(right_serial)
                if left_serial not in records[right_serial]:
                    records[right_serial].append(left_serial)
    lines: list[str] = []
    for serial, bonded in records.items():
        if bonded:
            lines.append(
                "CONECT"
                + f"{serial:5d}"
                + "".join(f"{target:5d}" for target in sorted(bonded)[:4])
            )
    return lines


def _atoms_likely_bonded(left_atom: dict, right_atom: dict) -> bool:
    """Return True when two atoms are close enough for a covalent bond."""
    if left_atom["element"] == "H" and right_atom["element"] == "H":
        return False
    dx = float(left_atom["x"]) - float(right_atom["x"])
    dy = float(left_atom["y"]) - float(right_atom["y"])
    dz = float(left_atom["z"]) - float(right_atom["z"])
    distance = (dx * dx + dy * dy + dz * dz) ** 0.5
    if distance < 0.35:
        return False
    threshold = (
        _covalent_radius(left_atom["element"])
        + _covalent_radius(right_atom["element"])
        + 0.45
    )
    return distance <= min(threshold, 2.25)


def _covalent_radius(element: str) -> float:
    """Return approximate covalent radius in Angstrom."""
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


def _element_from_atom(atom_name: str, atom_type: str) -> str:
    """Infer a PDB element from AutoDock atom type or atom name."""
    token = "".join(char for char in atom_type.strip() if char.isalpha()).upper()
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
    letters = "".join(char for char in atom_name if char.isalpha()).upper()
    return letters[:1] if letters else "C"


def _is_number(value: str) -> bool:
    """Return True when value can be parsed as a number."""
    try:
        float(value)
    except ValueError:
        return False
    return True


def build_pose_view_html(
    row: dict,
    receptor_pdb: Path,
    pose_pdb: Path,
    highlights: list[dict] | None = None,
    box: dict | None = None,
) -> str:
    """Return a 3Dmol.js HTML document for a receptor-pose complex."""
    receptor_text = receptor_pdb.read_text(encoding="utf-8", errors="replace")
    pose_text = pose_pdb.read_text(encoding="utf-8", errors="replace")
    ligand_name = html.escape(
        f"{row['ligand_name']} | {row.get('scoring_function', '')} | pose {int(row['mode'])}"
    )
    highlight_js = _interaction_highlight_js(highlights or [])
    box_js = _box_preview_js(box)
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <script src="https://cdn.jsdelivr.net/npm/3dmol@2.1.0/build/3Dmol-min.js"></script>
  <style>
    html, body {{ margin: 0; width: 100%; height: 100%; overflow: hidden; background: #0b0d12; color: #edf2ff; }}
    #viewer {{ width: 100vw; height: 100vh; position: relative; }}
    #error {{
      display: none; position: absolute; inset: 0; z-index: 20; align-items: center; justify-content: center;
      padding: 24px; text-align: center; background: #0b0d12; color: #f2dede; font: 14px Segoe UI, sans-serif;
    }}
    #label {{
      position: absolute; top: 12px; left: 12px; z-index: 10; padding: 8px 10px;
      background: rgba(10, 14, 22, 0.78); border: 1px solid rgba(255,255,255,0.14);
      border-radius: 8px; font: 13px Segoe UI, sans-serif;
    }}
    #hint {{
      position: absolute; bottom: 12px; left: 12px; z-index: 10; padding: 7px 9px;
      background: rgba(10, 14, 22, 0.72); border-radius: 8px; font: 12px Segoe UI, sans-serif;
      color: #b9c4d8;
    }}
  </style>
</head>
<body>
  <div id="viewer"></div>
  <div id="error">Erro ao carregar visualização 3D. Verifique os arquivos de entrada.</div>
  <div id="label">{ligand_name}</div>
  <div id="hint">Ligante: bastões ciano | resíduos próximos do receptor: bastões verdes | receptor: cartoon + superfície transparente</div>
  <script>
    const receptorPdb = {json.dumps(receptor_text)};
    const ligandPdb = {json.dumps(pose_text)};
    let viewer = null;
    let ligandModel = null;
    function showViewerError(error) {{
      console.log("Erro na visualização 3D:", error);
      document.getElementById("error").style.display = "flex";
    }}
    function renderComplex() {{
      if (typeof $3Dmol === "undefined") {{
        showViewerError("3Dmol.js indisponível");
        return;
      }}
      try {{
      viewer = $3Dmol.createViewer("viewer", {{backgroundColor: "#0b0d12"}});
      const receptorModel = viewer.addModel(receptorPdb, "pdb");
      ligandModel = viewer.addModel(ligandPdb, "pdb");
      receptorModel.setStyle({{}}, {{cartoon: {{color: "spectrum", opacity: 0.85}}}});
      ligandModel.setStyle({{}}, {{
        stick: {{colorscheme: "cyanCarbon", radius: 0.23}},
        sphere: {{scale: 0.23, colorscheme: "cyanCarbon"}}
      }});
      try {{
        viewer.addStyle({{model: receptorModel, within: {{distance: 4.0, sel: {{model: ligandModel}}}}}}, {{
          stick: {{colorscheme: "greenCarbon", radius: 0.14}}
        }});
        viewer.addSurface($3Dmol.SurfaceType.VDW, {{opacity: 0.16, color: "white"}}, {{
          model: receptorModel, within: {{distance: 6.0, sel: {{model: ligandModel}}}}
        }});
      }} catch (error) {{
        console.log("Interaction overlay skipped:", error);
      }}
      {highlight_js}
      {box_js}
      viewer.zoomTo({{model: ligandModel}});
      viewer.render();
      }} catch (error) {{
        showViewerError(error);
      }}
    }}
    function exportPng(scale) {{
      scale = Math.max(1, Math.min(5, Number(scale || 3)));
      const container = document.getElementById("viewer");
      const oldWidth = container.style.width;
      const oldHeight = container.style.height;
      const width = Math.max(1200, Math.floor(window.innerWidth * scale));
      const height = Math.max(900, Math.floor(window.innerHeight * scale));
      container.style.width = width + "px";
      container.style.height = height + "px";
      viewer.resize();
      viewer.zoomTo();
      viewer.render();
      const png = viewer.pngURI();
      container.style.width = oldWidth || "100vw";
      container.style.height = oldHeight || "100vh";
      viewer.resize();
      viewer.zoomTo({{model: ligandModel}});
      viewer.render();
      return png;
    }}
    window.addEventListener("resize", () => {{ if (viewer) {{ viewer.resize(); viewer.render(); }} }});
    renderComplex();
  </script>
</body>
</html>"""


def build_comparison_html(
    title: str, receptor_pdb: Path, pose_a_pdb: Path, pose_b_pdb: Path
) -> str:
    """Return a 3Dmol.js page comparing two ligand poses against one receptor."""
    receptor_text = receptor_pdb.read_text(encoding="utf-8", errors="replace")
    pose_a_text = pose_a_pdb.read_text(encoding="utf-8", errors="replace")
    pose_b_text = pose_b_pdb.read_text(encoding="utf-8", errors="replace")
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <script src="https://cdn.jsdelivr.net/npm/3dmol@2.1.0/build/3Dmol-min.js"></script>
  <style>
    html, body {{ margin: 0; width: 100%; height: 100%; overflow: hidden; background: #0b0d12; color: #edf2ff; }}
    #viewer {{ width: 100vw; height: 100vh; }}
    #label {{ position:absolute; top:12px; left:12px; z-index:10; padding:8px 10px; background:rgba(10,14,22,.78); border-radius:8px; font:13px Segoe UI,sans-serif; }}
  </style>
</head>
<body>
  <div id="viewer"></div>
  <div id="label">{html.escape(title)} | verde = A / dockada, magenta = B / referência</div>
  <script>
    const receptorPdb = {json.dumps(receptor_text)};
    const poseA = {json.dumps(pose_a_text)};
    const poseB = {json.dumps(pose_b_text)};
    const viewer = $3Dmol.createViewer("viewer", {{backgroundColor: "#0b0d12"}});
    const receptor = viewer.addModel(receptorPdb, "pdb");
    const modelA = viewer.addModel(poseA, "pdb");
    const modelB = viewer.addModel(poseB, "pdb");
    receptor.setStyle({{}}, {{cartoon: {{color: "spectrum", opacity: 0.75}}}});
    modelA.setStyle({{}}, {{stick: {{color: "limegreen", radius: 0.24}}, sphere: {{scale: 0.22, color: "limegreen"}}}});
    modelB.setStyle({{}}, {{stick: {{color: "magenta", radius: 0.24}}, sphere: {{scale: 0.22, color: "magenta"}}}});
    viewer.zoomTo({{model: modelA}});
    viewer.render();
    window.addEventListener("resize", () => {{ viewer.resize(); viewer.render(); }});
  </script>
</body>
</html>"""


def _interaction_highlight_js(highlights: list[dict]) -> str:
    """Return JavaScript statements that color highlighted receptor residues."""
    statements: list[str] = []
    color_by_type = {
        "H-bond": "dodgerblue",
        "Hydrophobic": "orange",
        "Contact": "lightgray",
    }
    for item in highlights:
        resi = str(item.get("residue_number", "")).strip()
        if not resi:
            continue
        color = color_by_type.get(str(item.get("interaction_type", "")), "lightgray")
        statements.append(
            "viewer.addStyle({model: receptorModel, resi: "
            f"{json.dumps(resi)}"
            f"}}, {{stick: {{color: {json.dumps(color)}, radius: 0.20}}}});"
        )
    return "\n      ".join(statements)


def _box_preview_js(box: dict | None) -> str:
    """Return 3Dmol.js statements for a search-box wireframe."""
    if not box:
        return ""
    center = {
        "x": float(box.get("center_x", 0.0)),
        "y": float(box.get("center_y", 0.0)),
        "z": float(box.get("center_z", 0.0)),
    }
    dimensions = {
        "w": float(box.get("size_x", 20.0)),
        "h": float(box.get("size_y", 20.0)),
        "d": float(box.get("size_z", 20.0)),
    }
    return (
        "viewer.addBox({"
        f"center: {json.dumps(center)}, "
        f"dimensions: {json.dumps(dimensions)}, "
        'color: "#C8922A", opacity: 0.95, wireframe: true'
        "});\n"
        f"viewer.addSphere({{center: {json.dumps(center)}, radius: 0.35, color: '#C8922A'}});"
    )
