"""Normalize PDB columns for receptor preparation without changing coordinates."""

import re

from core.file_utils import RESIDUE_ONE_LETTER


def normalize_receptor_pdb(text: str) -> tuple[str, int]:
    records = []
    count = 0
    for line in text.splitlines():
        if not line.startswith(("ATOM  ", "HETATM")):
            records.append(line)
            continue
        # Some writers print negative zero occupancy with an extra column,
        # shifting B-factor and element. Coordinates remain fixed-width.
        tail = line[54:].split()
        shifted = False
        try:
            occupancy = float(line[54:60].strip() or "1")
            temperature = float(line[60:66].strip() or "0")
        except ValueError:
            occupancy = float(tail[0])
            temperature = float(tail[1])
            shifted = True
        element = line[76:78].strip() if len(line) >= 78 else ""
        charge = line[78:80].strip() if len(line) >= 80 else ""
        if shifted or not element or not re.fullmatch(r"[A-Za-z]{1,2}", element) or not re.fullmatch(r"(?:[0-9][+-])?", charge):
            match = re.fullmatch(r"([A-Za-z]{1,2})([0-9][+-])?", tail[-1]) if len(tail) > 2 else None
            if match:
                element, charge = match.group(1), match.group(2) or ""
            else:
                name = line[12:16]
                letters = re.sub(r"[^A-Za-z]", "", name)
                if not letters:
                    raise ValueError("Elemento químico ausente e nome atômico inválido.")
                element = letters[0] if name.startswith(" ") or line[17:20] in RESIDUE_ONE_LETTER else letters[:2].title()
                if not re.fullmatch(r"(?:[0-9][+-])?", charge):
                    raise ValueError("Carga formal inválida no registro PDB.")
        repaired = f"{line[:54]}{occupancy:6.2f}{temperature:6.2f}{'':10}{element:>2}{charge:>2}"
        count += repaired.rstrip() != line.rstrip()
        records.append(repaired)
    return "\n".join(records) + "\n", count
