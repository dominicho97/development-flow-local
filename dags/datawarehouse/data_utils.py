"""PostgreSQL connections and warehouse table setup."""


def get_db_connection():
    """Use the warehouse connection configured by Docker Compose."""
    from airflow.providers.postgres.hooks.postgres import PostgresHook

    return PostgresHook(postgres_conn_id="postgres_db_yt_elt").get_conn()


def create_table(cursor, schema: str) -> None:
    """Create products in the requested schema using the caller's transaction."""
    if schema not in {"staging", "core"}:
        raise ValueError("Expected staging or core schema.")
    staging = schema == "staging"
    price_type = "TEXT" if staging else "NUMERIC"
    stock_type = "TEXT" if staging else "INTEGER"
    source_column = "source_record_id TEXT NOT NULL UNIQUE," if staging else ""
    sku_constraint = "" if staging else "UNIQUE"
    # SQL identifiers and types are internal constants, never caller-provided SQL.
    cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {schema}.products (
            record_id BIGSERIAL PRIMARY KEY,
            {source_column}
            sku TEXT NOT NULL {sku_constraint},
            product_name TEXT NOT NULL,
            category TEXT,
            listed_price {price_type},
            stock_qty {stock_type}
        )
    """)
