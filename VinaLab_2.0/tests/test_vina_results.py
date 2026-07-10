from __future__ import annotations

import importlib


def _parser_type():
    try:
        module = importlib.import_module("vinalab_core.docking.vina_results")
    except ModuleNotFoundError:
        return None
    return getattr(module, "VinaResultsParser", None)


def test_vina_results_parser_is_available_for_docking_output() -> None:
    assert _parser_type() is not None


def test_vina_results_parser_reads_rank_affinity_and_rmsd_columns() -> None:
    parser_type = _parser_type()
    assert parser_type is not None
    output = """
mode |   affinity | dist from best mode
     | (kcal/mol) | rmsd l.b.| rmsd u.b.
-----+------------+----------+----------
   1       -8.4          0          0
   2       -7.9      1.234      2.876
Writing output ... done.
"""

    poses = parser_type().parse(output)

    assert [(pose.mode, pose.affinity, pose.rmsd_lb, pose.rmsd_ub) for pose in poses] == [
        (1, -8.4, 0.0, 0.0),
        (2, -7.9, 1.234, 2.876),
    ]
