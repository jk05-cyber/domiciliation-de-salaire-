from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from .config import MAIN_OUTPUT_COLUMNS, OUTPUT_DIR
from .feature_engineering import build_candidate_features
from .io_utils import ensure_output_dir, export_dataframe, export_summary, load_monthly_inputs
from .preprocessing import empty_main_output_from_clients, preprocess_transactions
from .scoring import score_candidates

LOGGER = logging.getLogger(__name__)


def _select_best_candidate(scored_candidates: pd.DataFrame) -> pd.DataFrame:
    if scored_candidates.empty:
        return pd.DataFrame(columns=MAIN_OUTPUT_COLUMNS)

    ranked = scored_candidates.sort_values(
        by=["Identifiant SAB", "score", "nb_mois_detectes", "montant_median"],
        ascending=[True, False, False, False],
    ).copy()

    best = ranked.drop_duplicates(subset=["Identifiant SAB"], keep="first").copy()
    best = best.rename(columns={"emetteur_normalise": "emetteur_salaire_probable"})
    return best


def _merge_with_all_clients(all_clients: pd.DataFrame, best_candidates: pd.DataFrame) -> pd.DataFrame:
    if best_candidates.empty:
        final_df = empty_main_output_from_clients(all_clients)
        return final_df[MAIN_OUTPUT_COLUMNS]

    merged = all_clients.merge(best_candidates, on=["Identifiant SAB", "segment_client"], how="left")
    merged["nb_occurrences"] = merged["nb_occurrences"].fillna(0).astype(int)
    merged["nb_mois_detectes"] = merged["nb_mois_detectes"].fillna(0).astype(int)
    merged["mois_detectes"] = merged["mois_detectes"].fillna("")
    merged["score"] = merged["score"].fillna(0).astype(int)
    merged["statut"] = merged["statut"].fillna("NON_DETERMINE")
    merged["confiance"] = merged["confiance"].fillna("FAIBLE")
    merged["libelle_source_exemple"] = merged["libelle_source_exemple"].fillna("")
    return merged[MAIN_OUTPUT_COLUMNS]


def _build_summary(loaded_files: int, total_rows: int, final_df: pd.DataFrame) -> dict:
    return {
        "nombre_fichiers_charges": loaded_files,
        "nombre_total_lignes": int(total_rows),
        "nombre_clients": int(final_df["Identifiant SAB"].nunique()),
        "nombre_clients_salaire_probable": int((final_df["statut"] == "SALAIRE_PROBABLE").sum()),
        "nombre_clients_revenu_probable": int((final_df["statut"] == "REVENU_PROBABLE").sum()),
        "nombre_clients_non_determine": int((final_df["statut"] == "NON_DETERMINE").sum()),
    }


def run_pipeline() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    LOGGER.info("Demarrage du pipeline de detection de salaire")
    ensure_output_dir()

    raw_df, loaded_files = load_monthly_inputs()
    total_rows = len(raw_df)

    credits, all_clients = preprocess_transactions(raw_df)
    candidate_features = build_candidate_features(credits)
    scored_candidates = score_candidates(candidate_features)
    best_candidates = _select_best_candidate(scored_candidates)
    final_df = _merge_with_all_clients(all_clients, best_candidates)

    export_dataframe(final_df, OUTPUT_DIR / "salaires_estimes.csv")
    export_dataframe(scored_candidates, OUTPUT_DIR / "candidats_salaires.csv")

    summary = _build_summary(loaded_files, total_rows, final_df)
    export_summary(summary, OUTPUT_DIR / "summary.json")

    LOGGER.info("Pipeline termine avec succes")
    return final_df, scored_candidates, summary

