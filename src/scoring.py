from __future__ import annotations

import logging

import pandas as pd

from .config import (
    CONFIDENCE_FORTE_MIN,
    CONFIDENCE_MOYENNE_MIN,
    STATUS_REVENU_PROBABLE_MIN,
    STATUS_SALARY_PROBABLE_MIN,
)

LOGGER = logging.getLogger(__name__)


def compute_candidate_score(row: pd.Series) -> int:
    score = 0

    if row["nb_mois_detectes"] >= 3:
        score += 40
    elif row["nb_mois_detectes"] == 2:
        score += 25

    if row["montant_stable_fort"]:
        score += 20
    elif row["montant_stable_moyen"]:
        score += 10

    if row["jour_coherent"]:
        score += 10

    if row["label_has_positive_keyword"]:
        score += 30

    if row["label_has_negative_keyword"]:
        score -= 30

    if row["label_has_cash_keyword"]:
        score -= 25

    if row["probable_particulier"]:
        score -= 20

    if row["montant_irregulier"]:
        score -= 15

    return score


def derive_status(score: float) -> str:
    if score >= STATUS_SALARY_PROBABLE_MIN:
        return "SALAIRE_PROBABLE"
    if score >= STATUS_REVENU_PROBABLE_MIN:
        return "REVENU_PROBABLE"
    return "NON_DETERMINE"


def derive_confidence(score: float) -> str:
    if score >= CONFIDENCE_FORTE_MIN:
        return "FORTE"
    if score >= CONFIDENCE_MOYENNE_MIN:
        return "MOYENNE"
    return "FAIBLE"


def score_candidates(features: pd.DataFrame) -> pd.DataFrame:
    LOGGER.info("Application du scoring metier")
    if features.empty:
        return features.copy()

    scored = features.copy()
    scored["score"] = scored.apply(compute_candidate_score, axis=1)
    scored["statut"] = scored["score"].map(derive_status)
    scored["confiance"] = scored["score"].map(derive_confidence)
    scored["salaire_estime"] = scored["montant_median"]
    return scored

