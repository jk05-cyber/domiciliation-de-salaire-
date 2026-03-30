from __future__ import annotations

import logging
import sys

from .config import LOG_FORMAT
from .io_utils import PipelineInputError
from .pipeline import run_pipeline


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)


def main() -> int:
    configure_logging()

    try:
        run_pipeline()
    except PipelineInputError as exc:
        logging.getLogger(__name__).error("Erreur de fichier d'entree: %s", exc)
        return 1
    except Exception as exc:
        logging.getLogger(__name__).exception("Erreur inattendue: %s", exc)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

