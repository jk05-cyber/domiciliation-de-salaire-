from __future__ import annotations

import logging
import re
import string
import unicodedata

import numpy as np
import pandas as pd

from .config import COLUMN_ALIASES, GENERIC_TECHNICAL_WORDS, REQUIRED_COLUMNS

LOGGER = logging.getLogger(__name__)


def canonicalize_column_name(column_name: str) -> str:
    normalized = re.sub(r"\s+", " ", str(column_name).strip())
    return normalized.upper()


def standardize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    renamed_columns = {}
    for column in df.columns:
        canonical = canonicalize_column_name(column)
        renamed_columns[column] = COLUMN_ALIASES.get(canonical, re.sub(r"\s+", " ", str(column).strip()))

    standardized = df.rename(columns=renamed_columns).copy()
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in standardized.columns]
    if missing_columns:
        raise ValueError(f"Colonnes obligatoires manquantes: {missing_columns}")

    return standardized


def normalize_amount(series: pd.Series) -> pd.Series:
    cleaned = (
        series.fillna("")
        .astype(str)
        .str.replace(r"\s+", "", regex=True)
        .str.replace(",", ".", regex=False)
    )
    return pd.to_numeric(cleaned, errors="coerce")


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def normalize_label(value: str) -> str:
    value = strip_accents(str(value).upper())
    value = re.sub(r"\d+", " ", value)
    value = value.translate(str.maketrans({char: " " for char in string.punctuation}))
    tokens = [token for token in value.split() if token and token not in GENERIC_TECHNICAL_WORDS]
    normalized = " ".join(tokens)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def preprocess_transactions(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    LOGGER.info("Debut du pretraitement des transactions")
    standardized = standardize_column_names(df)

    standardized["Identifiant SAB"] = standardized["Identifiant SAB"].astype(str).str.strip()
    standardized["Libelle Court Segment"] = standardized["Libelle Court Segment"].fillna("").astype(str).str.strip()
    standardized["Libelle Mouvement"] = standardized["Libelle Mouvement"].fillna("").astype(str).str.strip()
    standardized["Montant Devise Local"] = normalize_amount(standardized["Montant Devise Local"])
    standardized["Date Operation"] = pd.to_datetime(
        standardized["Date Operation"],
        errors="coerce",
        dayfirst=True,
    )

    all_clients = (
        standardized[["Identifiant SAB", "Libelle Court Segment"]]
        .dropna(subset=["Identifiant SAB"])
        .drop_duplicates(subset=["Identifiant SAB"])
        .rename(columns={"Libelle Court Segment": "segment_client"})
    )

    standardized = standardized.dropna(
        subset=["Identifiant SAB", "Date Operation", "Montant Devise Local", "Libelle Mouvement"]
    ).copy()
    standardized = standardized[standardized["Identifiant SAB"] != ""].copy()

    standardized["emetteur_normalise"] = standardized["Libelle Mouvement"].map(normalize_label)
    standardized["jour_operation"] = standardized["Date Operation"].dt.day
    standardized["mois_operation"] = standardized["Date Operation"].dt.month
    standardized["annee_mois"] = standardized["Date Operation"].dt.strftime("%Y-%m")

    credits = standardized[standardized["Montant Devise Local"] > 0].copy()
    credits = credits[credits["emetteur_normalise"] != ""].copy()

    credits["montant_abs"] = credits["Montant Devise Local"].abs()

    LOGGER.info(
        "Pretraitement termine: %s lignes initiales, %s lignes crediteurs retenues",
        len(df),
        len(credits),
    )
    return credits, all_clients


def empty_main_output_from_clients(all_clients: pd.DataFrame) -> pd.DataFrame:
    empty = all_clients.copy()
    empty["emetteur_salaire_probable"] = pd.NA
    empty["nb_occurrences"] = 0
    empty["nb_mois_detectes"] = 0
    empty["mois_detectes"] = ""
    empty["montant_median"] = np.nan
    empty["montant_min"] = np.nan
    empty["montant_max"] = np.nan
    empty["montant_moyen"] = np.nan
    empty["ecart_type"] = np.nan
    empty["coefficient_variation"] = np.nan
    empty["jour_operation_median"] = np.nan
    empty["score"] = 0
    empty["statut"] = "NON_DETERMINE"
    empty["salaire_estime"] = np.nan
    empty["confiance"] = "FAIBLE"
    empty["libelle_source_exemple"] = ""
    return empty

