"""Insert or update raw staging rows and cleaned core products."""

import json
from contextlib import closing

import pandas as pd

from .data_utils import create_table, get_db_connection


def insert_rows(cursor, schema, row):
    """Insert a product, updating its values when its warehouse key exists."""
    values = (
        row["sku"],
        row["product_name"],
        row["category"],
        row["listed_price"],
        row["stock_qty"],
    )

    if schema == "staging":
        query = """
            INSERT INTO staging.products
                (source_record_id, sku, product_name, category, listed_price, stock_qty)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (source_record_id) DO UPDATE SET
                sku = EXCLUDED.sku,
                product_name = EXCLUDED.product_name,
                category = EXCLUDED.category,
                listed_price = EXCLUDED.listed_price,
                stock_qty = EXCLUDED.stock_qty
        """
        values = (row["source_record_id"], *values)
    elif schema == "core":
        query = """
            INSERT INTO core.products
                (sku, product_name, category, listed_price, stock_qty)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (sku) DO UPDATE SET
                product_name = EXCLUDED.product_name,
                category = EXCLUDED.category,
                listed_price = EXCLUDED.listed_price,
                stock_qty = EXCLUDED.stock_qty
        """
    else:
        raise ValueError("Expected staging or core schema.")

    values = tuple(None if pd.isna(value) else value for value in values)
    cursor.execute(query, values)


def populate_table(data, schema):
    """Save all rows in one transaction and return the number processed."""
    if schema == "staging":
        key = "record_id"
    elif schema == "core":
        key = "sku"
    else:
        raise ValueError("Expected staging or core schema.")

    required_columns = {
        key,
        "sku",
        "product_name",
        "category",
        "listed_price",
        "stock_qty",
    }
    missing_columns = required_columns - set(data.columns)
    if missing_columns:
        raise ValueError(f"Missing warehouse columns: {sorted(missing_columns)}")

    empty_keys = data[key].isna() | data[key].astype(str).str.strip().eq("")
    if empty_keys.any():
        raise ValueError(f"Warehouse key {key} must not be empty.")
    if schema == "core" and data[key].duplicated().any():
        raise ValueError(f"Warehouse key {key} must be unique within a batch.")

    if schema == "core":
        empty_names = data["product_name"].isna() | (
            data["product_name"].astype(str).str.strip().eq("")
        )
        if empty_names.any():
            raise ValueError("Core product names must not be empty.")

    # PostgreSQL needs None for SQL NULL, rather than pandas NaN or NA.
    products = data.astype(object).where(pd.notna(data), None)
    if schema == "staging":
        # Keep every observation, even when the source repeats record IDs.
        # The same file produces the same keys when retried.
        occurrences = products.groupby("record_id", sort=False).cumcount() + 1
        products["source_record_id"] = [
            json.dumps([str(record_id), int(occurrence)])
            for record_id, occurrence in zip(
                products["record_id"], occurrences, strict=True
            )
        ]

    with closing(get_db_connection()) as conn:  # noqa: SIM117 -- show each lifecycle step
        # Commit on success; roll back the whole batch if any row fails.
        with conn:
            with conn.cursor() as cursor:
                create_table(cursor, schema)
                if schema == "core":
                    # Repair old invalid core rows in the same transaction as upserts.
                    # Preserve their original raw observations in staging.
                    cursor.execute(
                        "DELETE FROM core.products "
                        "WHERE product_name IS NULL OR product_name ~ '^\\s*$'"
                    )
                for _, row in products.iterrows():
                    insert_rows(cursor, schema, row)

    return len(products)
