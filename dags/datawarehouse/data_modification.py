"""Insert or update raw staging rows and cleaned core products."""

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
        values = (row["record_id"], *values)
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
    if data[key].duplicated().any():
        raise ValueError(f"Warehouse key {key} must be unique within a batch.")

    # PostgreSQL needs None for SQL NULL, rather than pandas NaN or NA.
    products = data.astype(object).where(pd.notna(data), None)

    with closing(get_db_connection()) as conn:  # noqa: SIM117 -- show each lifecycle step
        # Commit on success; roll back the whole batch if any row fails.
        with conn:
            with conn.cursor() as cursor:
                create_table(cursor, schema)
                for _, row in products.iterrows():
                    insert_rows(cursor, schema, row)

    return len(products)
