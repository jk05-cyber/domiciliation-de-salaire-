from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd

from .config import EXPECTED_FILES, OUTPUT_DIR, REQUIRED_COLUMNS
from .preprocessing import canonicalize_column_name

LOGGER = logging.getLogger(__name__)


class PipelineInputError(FileNotFoundError):
    """Raised when one or more expected input files are missing."""


def ensure_output_dir() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _score_dataframe_columns(df: pd.DataFrame) -> int:
    normalized = {canonicalize_column_name(column) for column in df.columns}
    expected = {canonicalize_column_name(column) for column in REQUIRED_COLUMNS}
    return len(normalized & expected)


def read_csv_with_auto_separator(file_path: Path) -> pd.DataFrame:
    if not file_path.exists():
        raise PipelineInputError(f"Fichier introuvable: {file_path}")

    best_df: pd.DataFrame | None = None
    best_score = -1
    best_sep = None

    for sep in (";", ","):
        try:
            df = pd.read_csv(file_path, sep=sep, dtype=str, encoding="utf-8-sig")
        except UnicodeDecodeError:
            df = pd.read_csv(file_path, sep=sep, dtype=str, encoding="latin-1")
        except Exception as exc:
            LOGGER.warning("Lecture impossible pour %s avec sep='%s': %s", file_path.name, sep, exc)
            continue

        score = _score_dataframe_columns(df)
        if score > best_score or (score == best_score and best_df is not None and df.shape[1] > best_df.shape[1]):
            best_df = df
            best_score = score
            best_sep = sep

    if best_df is None:
        raise ValueError(f"Impossible de lire le fichier CSV: {file_path}")

    LOGGER.info("Fichier %s charge avec le separateur '%s'", file_path.name, best_sep)
    return best_df


def load_monthly_inputs() -> tuple[pd.DataFrame, int]:
    dataframes: list[pd.DataFrame] = []
    loaded_files = 0

    for month_name, file_path in EXPECTED_FILES.items():
        LOGGER.info("Chargement du fichier %s", file_path.name)
        df = read_csv_with_auto_separator(file_path)
        df["mois_source"] = month_name
        dataframes.append(df)
        loaded_files += 1

    concatenated = pd.concat(dataframes, ignore_index=True) if dataframes else pd.DataFrame()
    return concatenated, loaded_files


def export_dataframe(df: pd.DataFrame, path: Path) -> None:
    ensure_output_dir()
    df.to_csv(path, index=False, encoding="utf-8")
    LOGGER.info("Fichier exporte: %s", path)


def export_summary(summary: dict, path: Path) -> None:
    ensure_output_dir()
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    LOGGER.info("Synthese exportee: %s", path)

