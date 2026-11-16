"""Coordinate CSV loading into staging and core product tables."""

from pathlib import Path

from .data_loading import load_data
from .data_modification import populate_table
from .data_transformation import transform_data


def staging_table(
    config_path: str | Path = "config.json", *, csv_path: str | Path | None = None
) -> int:
    """Upsert raw observations by source record ID; return the row count."""
    schema = "staging"
    if csv_path is None:
        products_data = load_data(config_path)
    else:
        products_data = load_data(csv_path=csv_path)
    row_count = populate_table(products_data, schema)
    return row_count


def core_table(
    config_path: str | Path = "config.json", *, csv_path: str | Path | None = None
) -> int:
    """Upsert cleaned, deduplicated products by SKU; return the row count."""
    schema = "core"
    if csv_path is None:
        products_data = load_data(config_path)
    else:
        products_data = load_data(csv_path=csv_path)
    cleaned_products = transform_data(products_data)
    row_count = populate_table(cleaned_products, schema)
    return row_count
