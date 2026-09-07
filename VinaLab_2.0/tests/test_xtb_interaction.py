import math
from pathlib import Path

import pytest

from vinalab_core.scoring.xtb_scorer import XtbScorer
from vinalab_core.scoring.xyz import read_xyz, validate_fragments


def waters(tmp_path):
    a = "O 0 0 0\nH .9572 0 0\nH -.239 .927 0\n"
    b = "O 0 0 3\nH .9572 0 3\nH -.239 .927 3\n"
    paths = tuple(tmp_path / f"{name}.xyz" for name in ("complex", "receptor", "ligand"))
    for path, count, body in zip(paths, (6, 3, 3), (a+b, a, b)):
        path.write_text(f"{count}\nprepared water\n{body}")
    return paths


def test_xyz_fragment_validation(tmp_path):
    c, r, l = waters(tmp_path)
    validate_fragments(read_xyz(c), read_xyz(r), read_xyz(l))
    l.write_text(l.read_text().replace("0 0 3", "0 0 4"))
    with pytest.raises(ValueError, match="coordinates"):
        validate_fragments(read_xyz(c), read_xyz(r), read_xyz(l))


@pytest.mark.parametrize("body", ["1\nx\nH nan 0 0\n", "2\nx\nH 0 0 0\n", "1\nx\nQq 0 0 0\n"])
def test_invalid_xyz(tmp_path, body):
    p = tmp_path / "bad.xyz"
    p.write_text(body)
    with pytest.raises(ValueError):
        read_xyz(p)


@pytest.mark.parametrize("method", ["gfn2", "gfnff"])
def test_real_xtb_frozen_water_interaction(tmp_path, method):
    root = Path(__file__).resolve().parents[1]
    scorer = XtbScorer(root)
    if not scorer.is_available()[0]:
        pytest.skip("xTB not installed")
    _c, r, l = waters(tmp_path)
    result = scorer.score_interaction(r, l, charge_receptor=0,
        charge_ligand=0, uhf_complex=0, uhf_receptor=0, uhf_ligand=0,
        hydrogen_complete=True, cpu_threads=1, timeout_seconds=90, method=method)
    assert math.isfinite(result.interaction_kcal_per_mol)
    assert result.interaction_hartree == pytest.approx(
        result.complex_energy.hartree-result.receptor_energy.hartree-result.ligand_energy.hartree)
    assert "affinity" in result.interpretation
    assert "TOTAL ENERGY" in result.complex_energy.stdout.upper()
    assert result.complex_energy.command


def test_nonconvergence_even_with_zero_exit_status(tmp_path):
    from vinalab_core.docking.vina_runner import VinaProcessResult
    class Runner:
        def execute(self, command, **kwargs):
            return VinaProcessResult(tuple(command), 0, "total energy -1 Eh\nSCC not converged", "")
    _, r, _ = waters(tmp_path)
    scorer = XtbScorer(Path(__file__).resolve().parents[1], runner=Runner())
    with pytest.raises(RuntimeError, match="converge"):
        scorer.score_single_point(r, charge=0, uhf=0, cpu_threads=1)


@pytest.mark.parametrize("updates", [{"hydrogen_complete": False}, {"charge_receptor": .5},
    {"uhf_ligand": 1}, {"uhf_complex": -1}, {"method": "unsupported"}])
def test_invalid_interaction_request(tmp_path, updates):
    _, r, l = waters(tmp_path)
    request = {"charge_receptor": 0, "charge_ligand": 0, "uhf_receptor": 0, "uhf_ligand": 0,
        "uhf_complex": 0, "hydrogen_complete": True}
    request = {**request, **updates}
    with pytest.raises(ValueError):
        XtbScorer(Path(__file__).resolve().parents[1]).score_interaction(r, l, **request)
