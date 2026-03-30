from __future__ import annotations

import logging
import re

import numpy as np
import pandas as pd

LOGGER = logging.getLogger(__name__)

POSITIVE_KEYWORDS = ("SALAIRE", "PAIE", "PAYROLL", "REMUNERATION")
NEGATIVE_KEYWORDS = ("CNSS", "ASSURANCE", "SANLAM", "AXA", "MUTUELLE")
CASH_KEYWORDS = ("VERSEMENT ESPECES", "VERSEMENT ESPECE")
COMPANY_HINTS = (
    "SARL",
    "SA",
    "SAS",
    "LTD",
    "LLC",
    "GROUPE",
    "HOLDING",
    "INDUSTRIE",
    "BANQUE",
    "STE",
    "COMPAGNIE",
    "PAYROLL",
    "SALAIRE",
    "PAIE",
    "REMUNERATION",
)


def contains_any_keyword(value: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in value for keyword in keywords)


def is_probable_individual_transfer(value: str) -> bool:
    tokens = value.split()
    if not 2 <= len(tokens) <= 3:
        return False
    if contains_any_keyword(value, POSITIVE_KEYWORDS + COMPANY_HINTS):
        return False
    if not all(token.isalpha() and len(token) >= 2 for token in tokens):
        return False
    return True


def build_candidate_features(credits: pd.DataFrame) -> pd.DataFrame:
    LOGGER.info("Construction des features candidats")
    if credits.empty:
        return pd.DataFrame()

    sorted_credits = credits.sort_values(["Identifiant SAB", "emetteur_normalise", "Date Operation"]).copy()

    def aggregate_candidate(group: pd.DataFrame) -> pd.Series:
        months = list(dict.fromkeys(group["mois_source"].astype(str).tolist()))
        mean_amount = float(group["Montant Devise Local"].mean())
        std_amount = float(group["Montant Devise Local"].std(ddof=0))
        cv = np.nan if mean_amount == 0 else std_amount / mean_amount
        normalized_label = str(group.name[1])
        sample_label = next((label for label in group["Libelle Mouvement"] if str(label).strip()), "")

        return pd.Series(
            {
                "segment_client": group["Libelle Court Segment"].dropna().iloc[0]
                if not group["Libelle Court Segment"].dropna().empty
                else "",
                "nb_occurrences": int(len(group)),
                "nb_mois_detectes": int(group["mois_source"].nunique()),
                "mois_detectes": ",".join(months),
                "montant_median": float(group["Montant Devise Local"].median()),
                "montant_min": float(group["Montant Devise Local"].min()),
                "montant_max": float(group["Montant Devise Local"].max()),
                "montant_moyen": mean_amount,
                "ecart_type": std_amount,
                "coefficient_variation": float(cv) if not np.isnan(cv) else np.nan,
                "jour_operation_median": float(group["jour_operation"].median()),
                "libelle_source_exemple": sample_label,
                "label_has_positive_keyword": contains_any_keyword(normalized_label, POSITIVE_KEYWORDS),
                "label_has_negative_keyword": contains_any_keyword(normalized_label, NEGATIVE_KEYWORDS),
                "label_has_cash_keyword": contains_any_keyword(normalized_label, CASH_KEYWORDS),
                "probable_particulier": is_probable_individual_transfer(normalized_label),
                "montant_stable_fort": bool(not np.isnan(cv) and cv < 0.15),
                "montant_stable_moyen": bool(not np.isnan(cv) and cv < 0.30),
                "montant_irregulier": bool(np.isnan(cv) or cv >= 0.30),
                "jour_coherent": bool(
                    25 <= group["jour_operation"].median() <= 31 or 1 <= group["jour_operation"].median() <= 5
                ),
            }
        )

    features = (
        sorted_credits.groupby(["Identifiant SAB", "emetteur_normalise"], dropna=False)
        .apply(aggregate_candidate, include_groups=False)
        .reset_index()
    )

    LOGGER.info("Features construites pour %s couples client-emetteur", len(features))
    return features

