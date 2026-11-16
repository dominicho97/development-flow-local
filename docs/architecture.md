# Architecture

## Scope

The repository currently implements a small, function-oriented pipeline:

```text
dataset/raw/products.csv
        |
        v
   load_products()
        |
        v
   clean_products()
        |
        v
deduplicate_products()
        |
        +--> latest observations
        +--> duplicate audit rows
```

The Airflow DAG in `dags/products_elt_dag.py` orchestrates these stages and
writes the cleaned data and duplicate audit to `dataset/processed/`.
It also populates PostgreSQL warehouse tables in this task order:

```text
extract → update_staging → transform → load → update_core
```

The stages are separate calls. `clean_products()` does not automatically call
`deduplicate_products()`.

## Modules

### `src/ingestion.py`

- Defines the required ingestion columns: `record_id`, `sku`,
  `product_name`, and `listed_price`.
- Loads CSV data with UTF-8 BOM support, string values, and empty strings kept
  as empty strings.
- Raises `FileNotFoundError` for a missing path and `ValueError` for malformed
  CSV content or missing required columns.
- Provides the `src\ingestion.py` command-line entry point, which previews the
  first rows of the loaded dataframe.

### `src/transformation.py`

- `clean_products(df)` copies the input dataframe and applies the available
  field-level transformations.
- `deduplicate_products(df)` selects the latest row for each non-empty SKU and
  returns all duplicate rows separately with `selected_as_latest` metadata.
- Helper functions keep individual cleaning rules testable: `clean_price`,
  `clean_stock`, `clean_date`, `clean_category`, `clean_country`,
  `clean_currency`, and `clean_active`.

### `dataset/raw/products.csv`

The sample raw input contains deliberately inconsistent product values used to
exercise ingestion and transformation behavior.

### `tests/`

The test suite covers ingestion failures, field-level transformations,
invalid-value handling, date parsing, and duplicate-SKU selection.

### `dags/products_elt_dag.py`

The Airflow TaskFlow DAG validates the raw CSV, runs the cleaning and
deduplication helpers, verifies the processed output files, and invokes the
warehouse loaders. It imports `dag` and `task` from the Airflow 3 public
interface, `airflow.sdk`.

### `dags/datawarehouse/data_loading.py`

Provides a configuration-driven CSV loader without importing Airflow:

- `load_path(config_path="config.json")` reads a UTF-8 JSON object and requires
  a non-empty string named `raw_product_csv_path`. Relative CSV paths are
  resolved against the configuration file's directory.
- `load_data(config_path="config.json")` calls `load_path()` and reuses
  `src.ingestion.load_products()` to return a validated pandas dataframe.
- Loading preserves the ingestion rules above; it does not clean, deduplicate,
  write output files, or insert records into PostgreSQL.

`load_data(csv_path=...)` also accepts a CSV path directly. The warehouse tasks
use this option with the container dataset path, so the DAG needs no JSON
configuration. Business logic in `src/` remains separate from scheduling and
task dependencies.

### Warehouse helpers

- `dwh.py` coordinates the other warehouse modules through `staging_table()`
  and `core_table()`. Both return the number of processed rows.
- `data_transformation.py` calls the existing cleaning and deduplication
  functions from `src/transformation.py`.
- `data_utils.py` connects through Airflow's `postgres_db_yt_elt` connection
  (configured by Compose) and creates schemas and product tables.
- `data_modification.py` validates warehouse keys and uses explicit staging
  and core SQL to insert or update rows. Each batch commits as one transaction;
  failures propagate and roll back. Missing pandas values become SQL NULL.

`staging.products` stores raw observations, identified by a unique
`source_record_id` copied from the CSV's `record_id`. Duplicate SKUs can have
separate staging observations. Price and stock remain text.

`core.products` stores cleaned, deduplicated products, identified by unique
SKU, with numeric prices and integer stock. Both tables have a generated
database `record_id`. Repeat loads update matching keys; rows absent from the
input remain in the database.

Core currently reloads and transforms the raw CSV; it does not read staging
or the processed CSV. The task dependency ensures staging finishes first.
Only SKU, name, category, price, and stock are stored as product fields.

### `.github/workflows/ci.yml`

The CI workflow runs on pull requests targeting `main`. It installs Python 3.12
and locked uv dependencies, then runs pytest and Ruff.

## Current boundaries

Validation-issue reporting and production scheduling remain future work.
Warehouse code is covered by unit tests, but live PostgreSQL loading still
requires verification. Existing tables created by the earlier helper schema
need a migration: `CREATE TABLE IF NOT EXISTS` does not alter their columns
or add the new unique constraints.
