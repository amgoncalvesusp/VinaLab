# -*- coding: utf-8 -*-
"""Guard tests for the bilingual string registry."""

import string
import unittest

from core.i18n import I18n


class I18nParityTests(unittest.TestCase):
    """Every translation key must carry both PT and EN values."""

    def test_every_key_has_pt_and_en(self) -> None:
        missing = [
            key
            for key, value in I18n.STRINGS.items()
            if not value.get("pt") or not value.get("en")
        ]
        self.assertEqual(missing, [], f"Keys missing a pt/en value: {missing}")

    def test_format_placeholders_match_across_languages(self) -> None:
        formatter = string.Formatter()
        mismatched: list[str] = []
        for key, value in I18n.STRINGS.items():
            fields = {
                lang: {
                    name
                    for _text, name, _spec, _conv in formatter.parse(value[lang])
                    if name
                }
                for lang in ("pt", "en")
            }
            if fields["pt"] != fields["en"]:
                mismatched.append(key)
        self.assertEqual(
            mismatched, [], f"Keys with differing format fields pt/en: {mismatched}"
        )

    def test_get_falls_back_and_formats(self) -> None:
        self.assertEqual(I18n.get("warning_title", "en"), "Warning")
        rendered = I18n.get("dt_validation_parsed", "en").format(count=3)
        self.assertIn("3", rendered)


if __name__ == "__main__":
    unittest.main()
