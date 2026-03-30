from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"

EXPECTED_FILES = {
    "decembre": INPUT_DIR / "decembre.csv",
    "janvier": INPUT_DIR / "janvier.csv",
    "fevrier": INPUT_DIR / "fevrier.csv",
}

REQUIRED_COLUMNS = [
    "Identifiant SAB",
    "Libelle Court Segment",
    "ID Mouvement",
    "Libelle Mouvement",
    "Code Siege",
    "Date Operation",
    "Montant Devise Local",
]

COLUMN_ALIASES = {
    "IDENTIFIANT SAB": "Identifiant SAB",
    "LIBELLE COURT SEGMENT": "Libelle Court Segment",
    "ID MOUVEMENT": "ID Mouvement",
    "LIBELLE MOUVEMENT": "Libelle Mouvement",
    "CODE SIEGE": "Code Siege",
    "DATE OPERATION": "Date Operation",
    "MONTANT DEVISE LOCAL": "Montant Devise Local",
}

GENERIC_TECHNICAL_WORDS = {
    "VIR",
    "VIRT",
    "RECU",
    "INST",
    "OP",
    "APP",
    "COM",
}

MAIN_OUTPUT_COLUMNS = [
    "Identifiant SAB",
    "segment_client",
    "emetteur_salaire_probable",
    "nb_occurrences",
    "nb_mois_detectes",
    "mois_detectes",
    "montant_median",
    "montant_min",
    "montant_max",
    "montant_moyen",
    "ecart_type",
    "coefficient_variation",
    "jour_operation_median",
    "score",
    "statut",
    "salaire_estime",
    "confiance",
    "libelle_source_exemple",
]

STATUS_SALARY_PROBABLE_MIN = 50
STATUS_REVENU_PROBABLE_MIN = 30

CONFIDENCE_FORTE_MIN = 60
CONFIDENCE_MOYENNE_MIN = 45

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
