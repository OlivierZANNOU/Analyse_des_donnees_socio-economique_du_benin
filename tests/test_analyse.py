import sys
import unittest

from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from analyse import clean, load_raw, trends  # noqa: E402


class TestAnalyse(unittest.TestCase):
    def setUp(self):
        self.raw, self.meta = load_raw()
        self.wide = clean(self.raw, self.meta)

    def test_grille_complete(self):
        self.assertEqual(self.wide.shape, (7 * 25, 15))

    def test_valeurs_non_modifiees(self):
        expected = self.raw.query("code_pays == 'BEN' and code_indicateur == 'SP.POP.TOTL' and annee == 2024")
        self.assertEqual(self.wide.loc[("Bénin", 2024), "population"], expected.valeur.iloc[0])

    def test_pas_d_imputation(self):
        n = self.raw.annee.between(2000, 2024).sum()
        self.assertEqual(self.wide.notna().sum().sum(), n)

    def test_doublons_refuses(self):
        with self.assertRaises(ValueError):
            clean(pd.concat([self.raw, self.raw.head(1)]), self.meta)

    def test_tendance_serie_courte(self):
        result = trends(self.wide.loc["Bénin"][["alphabetisation"]].head(25), min_points=50)
        self.assertTrue(result.pente_par_an.isna().all())


if __name__ == "__main__":
    unittest.main()
