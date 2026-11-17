"""Prepare core products using the shared cleaning rules."""

import logging

import pandas as pd

from src.transformation import clean_products, deduplicate_products

logger = logging.getLogger(__name__)


def transform_data(data: pd.DataFrame) -> pd.DataFrame:
    """Return the latest cleaned observation per non-empty SKU for core."""
    latest, _duplicates = deduplicate_products(clean_products(data))
    valid_sku = latest["sku"].notna() & latest["sku"].astype(str).str.strip().ne("")
    skipped_count = int((~valid_sku).sum())
    if skipped_count:
        logger.warning(
            "Skipping %s products without a SKU in core; raw rows remain in staging.",
            skipped_count,
        )
    valid_name = latest["product_name"].notna() & (
        latest["product_name"].astype(str).str.strip().ne("")
    )
    missing_name_count = int((valid_sku & ~valid_name).sum())
    if missing_name_count:
        logger.warning(
            "Skipping %s products without a name in core; raw rows remain in staging.",
            missing_name_count,
        )
    return latest.loc[valid_sku & valid_name].copy()
