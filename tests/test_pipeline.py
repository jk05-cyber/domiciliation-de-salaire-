from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src import io_utils, pipeline
from src.feature_engineering import build_candidate_features
from src.preprocessing import normalize_amount, normalize_label, preprocess_transactions
from src.scoring import score_candidates


REQUIRED_HEADER = (
    "Identifiant SAB,Libelle Court Segment,ID Mouvement,Libelle Mouvement,Code Siege,Date Operation,"
    "Montant Devise Local\n"
)


class SalaryPipelineTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="salary_pipeline_test_"))
        self.input_dir = self.temp_dir / "input"
        self.output_dir = self.temp_dir / "output"
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _write_file(self, name: str, content: str) -> Path:
        path = self.input_dir / name
        path.write_text(content, encoding="utf-8")
        return path

    def _write_default_inputs(self) -> None:
        decembre = """Identifiant SAB,Libelle Court Segment,ID Mouvement,Libelle Mouvement,Code Siege,Date Operation,Montant Devise Local
1001,PARTICULIER,1,SALAIRE ACME SA,001,28/12/2025,5000.00
1002,PARTICULIER,2,ACHAT CB,001,12/12/2025,-250.50
"""
        janvier = """Identifiant SAB;Libelle Court Segment;ID Mouvement;Libelle Mouvement;Code Siege;Date Operation;Montant Devise Local
1001;PARTICULIER;3;SALAIRE ACME SA;001;28/01/2026;5050,00
1003;PRO;4;VERSEMENT ESPECES;001;10/01/2026;3000,00
"""
        fevrier = """Identifiant SAB;Libelle Court Segment;ID Mouvement;Libelle Mouvement;Code Siege;Date Operation;Montant Devise Local
1001;PARTICULIER;5;SALAIRE ACME SA;001;03/02/2026;4980,00
1002;PARTICULIER;6;LOYER;001;05/02/2026;-900,00
"""
        self._write_file("decembre.csv", decembre)
        self._write_file("janvier.csv", janvier)
        self._write_file("fevrier.csv", fevrier)

    def test_read_csv_with_semicolon_separator(self) -> None:
        path = self._write_file("janvier.csv", "Identifiant SAB;Date Operation\n1;01/01/2025\n")
        df = io_utils.read_csv_with_auto_separator(path)
        self.assertIn("Identifiant SAB", df.columns)

    def test_read_csv_with_comma_separator(self) -> None:
        path = self._write_file("decembre.csv", "Identifiant SAB,Date Operation\n1,01/01/2025\n")
        df = io_utils.read_csv_with_auto_separator(path)
        self.assertIn("Identifiant SAB", df.columns)

    def test_normalize_amount_handles_decimal_comma(self) -> None:
        series = pd.Series(["1 234,56"])
        amount = normalize_amount(series).iloc[0]
        self.assertAlmostEqual(amount, 1234.56, places=2)

    def test_preprocess_parses_dates_and_filters_credits(self) -> None:
        raw = pd.DataFrame(
            {
                " Identifiant SAB ": ["1001", "1001"],
                "Libelle Court Segment": ["PART", "PART"],
                "ID Mouvement": ["1", "2"],
                "Libelle Mouvement": ["SALAIRE ACME", "PAIEMENT"],
                "Code Siege": ["001", "001"],
                "Date Operation": ["28/11/2025", "29/11/2025"],
                "Montant Devise Local": ["5000,00", "-100,00"],
                "mois_source": ["decembre", "decembre"],
            }
        )
        credits, all_clients = preprocess_transactions(raw)
        self.assertEqual(len(credits), 1)
        self.assertEqual(len(all_clients), 1)
        self.assertEqual(credits["Date Operation"].dt.day.iloc[0], 28)

    def test_normalize_label_builds_emetteur_normalise(self) -> None:
        normalized = normalize_label("VIR RECU SALAIRE ACME SA 12345")
        self.assertEqual(normalized, "SALAIRE ACME SA")

    def test_scoring_positive_recurrent_salary_case(self) -> None:
        credits = pd.DataFrame(
            {
                "Identifiant SAB": ["1001", "1001", "1001"],
                "Libelle Court Segment": ["PART", "PART", "PART"],
                "ID Mouvement": ["1", "2", "3"],
                "Libelle Mouvement": ["SALAIRE ACME SA"] * 3,
                "Code Siege": ["001"] * 3,
                "Date Operation": pd.to_datetime(["2025-12-28", "2026-01-28", "2026-02-03"]),
                "Montant Devise Local": [5000.0, 5050.0, 4980.0],
                "mois_source": ["decembre", "janvier", "fevrier"],
                "emetteur_normalise": ["SALAIRE ACME SA"] * 3,
                "jour_operation": [28, 28, 3],
            }
        )
        features = build_candidate_features(credits)
        scored = score_candidates(features)
        self.assertEqual(scored["statut"].iloc[0], "SALAIRE_PROBABLE")
        self.assertGreaterEqual(scored["score"].iloc[0], 50)

    def test_scoring_penalizes_cash_deposit(self) -> None:
        credits = pd.DataFrame(
            {
                "Identifiant SAB": ["1003", "1003"],
                "Libelle Court Segment": ["PART", "PART"],
                "ID Mouvement": ["1", "2"],
                "Libelle Mouvement": ["VERSEMENT ESPECES", "VERSEMENT ESPECES"],
                "Code Siege": ["001", "001"],
                "Date Operation": pd.to_datetime(["2025-12-10", "2026-01-10"]),
                "Montant Devise Local": [3000.0, 3100.0],
                "mois_source": ["decembre", "janvier"],
                "emetteur_normalise": ["VERSEMENT ESPECES", "VERSEMENT ESPECES"],
                "jour_operation": [10, 10],
            }
        )
        features = build_candidate_features(credits)
        scored = score_candidates(features)
        self.assertLess(scored["score"].iloc[0], 30)
        self.assertEqual(scored["statut"].iloc[0], "NON_DETERMINE")

    def test_pipeline_selects_best_candidate_and_keeps_undetermined_clients(self) -> None:
        self._write_default_inputs()

        with patch.dict(
                "src.io_utils.EXPECTED_FILES",
                {
                    "decembre": self.input_dir / "decembre.csv",
                    "janvier": self.input_dir / "janvier.csv",
                    "fevrier": self.input_dir / "fevrier.csv",
                },
                clear=True,
            ), patch("src.io_utils.OUTPUT_DIR", self.output_dir), patch(
                "src.pipeline.OUTPUT_DIR", self.output_dir
            ):
            final_df, candidates_df, summary = pipeline.run_pipeline()

        self.assertEqual(summary["nombre_fichiers_charges"], 3)
        self.assertEqual(len(final_df), 3)

        client_1001 = final_df.loc[final_df["Identifiant SAB"] == "1001"].iloc[0]
        client_1002 = final_df.loc[final_df["Identifiant SAB"] == "1002"].iloc[0]

        self.assertEqual(client_1001["statut"], "SALAIRE_PROBABLE")
        self.assertEqual(client_1001["emetteur_salaire_probable"], "SALAIRE ACME SA")
        self.assertEqual(client_1002["statut"], "NON_DETERMINE")

        summary_path = self.output_dir / "summary.json"
        self.assertTrue(summary_path.exists())
        loaded_summary = json.loads(summary_path.read_text(encoding="utf-8"))
        self.assertEqual(loaded_summary["nombre_clients"], 3)
        self.assertFalse(candidates_df.empty)


if __name__ == "__main__":
    unittest.main()
