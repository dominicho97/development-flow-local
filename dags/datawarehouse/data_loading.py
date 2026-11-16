import json
import logging
from pathlib import Path

import pandas as pd

from src.ingestion import load_products

logger = logging.getLogger(__name__)


def load_path(config_path: str | Path = "config.json") -> str:
    """Load the path to the raw product CSV from a JSON file."""
    try:
        with Path(config_path).open(encoding="utf-8") as f:
            config = json.load(f)
    except FileNotFoundError:
        logger.error("config.json file not found.")
        raise
    except json.JSONDecodeError:
        logger.error("Error decoding JSON from config.json.")
        raise

    if not isinstance(config, dict):
        raise TypeError("Configuration must be a JSON object.")
    raw_path = config.get("raw_product_csv_path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ValueError("raw_product_csv_path must be a non-empty string.")
    path = Path(raw_path)
    if not path.is_absolute():
        path = Path(config_path).parent / path
    return str(path.resolve())


def load_data(
    config_path: str | Path = "config.json", *, csv_path: str | Path | None = None
) -> pd.DataFrame:
    """Load and validate the product CSV specified by the configuration."""
    if csv_path is not None:
        return load_products(csv_path)
    return load_products(load_path(config_path))
