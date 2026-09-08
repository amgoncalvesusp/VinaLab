"""Regression checks for Portuguese labels and translation format contracts."""

from collections import Counter
import string
import unittest

from core.i18n import I18n


class PortugueseLabelTests(unittest.TestCase):
    def test_reference_labels_are_accented(self):
        keys = (
            "reference_rmsd", "reference_validation", "score_vs_reference_rmsd",
            "reference_ligand", "tip_reference_ligand", "reference_padding",
            "tip_reference_padding", "reference_rmsd_cutoff",
            "tip_reference_rmsd_cutoff",
        )
        for key in keys:
            with self.subTest(key=key):
                self.assertIn("refer\u00eancia", I18n.get(key, "pt"))
        self.assertEqual(
            I18n.get("reference_validation", "pt"), "Valida\u00e7\u00e3o da refer\u00eancia"
        )

    def test_prepare_protein_tab_is_optional_in_both_languages(self):
        self.assertEqual(
            I18n.get("tab_prepare_protein", "pt"),
            "Preparar Prote\u00edna (opcional)",
        )
        self.assertEqual(
            I18n.get("tab_prepare_protein", "en"), "Prepare Protein (optional)"
        )

    def test_format_fields_specs_conversions_and_counts_match(self):
        formatter = string.Formatter()
        for key, translations in I18n.STRINGS.items():
            with self.subTest(key=key):
                fields = {
                    lang: Counter(
                        (name, spec, conversion)
                        for _, name, spec, conversion in formatter.parse(translations[lang])
                        if name is not None
                    )
                    for lang in ("pt", "en")
                }
                self.assertEqual(fields["pt"], fields["en"])
