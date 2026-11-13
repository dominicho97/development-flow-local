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
deduplication helpers, and verifies the processed output files.

### `.github/workflows/ci.yml`

The CI workflow runs on pull requests targeting `main`. It installs Python 3.12
and locked uv dependencies, then runs pytest and Ruff.

## Current boundaries

Validation-issue reporting, database loading, and production scheduling remain
future work.
