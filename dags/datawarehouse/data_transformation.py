"""Prepare core products using the shared cleaning rules."""

import pandas as pd

from src.transformation import clean_products, deduplicate_products


def transform_data(data: pd.DataFrame) -> pd.DataFrame:
    """Return the latest cleaned observation per SKU."""
    latest, _duplicates = deduplicate_products(clean_products(data))
    return latest
