# development-flow-local

A small Python data-engineering project for loading and cleaning a raw product
CSV. The current implementation provides reusable pandas functions and a
command-line preview for ingestion; it does not yet write a cleaned dataset.

## Current capabilities

- Load UTF-8 CSV files as strings and validate required ingestion columns.
- Preview the default product dataset from the command line.
- Normalize product text, categories, prices, stock, dates, countries,
  currencies, and active-status values.
- Select the latest observation for duplicate SKUs while returning duplicate
  rows for audit.
- Run automated tests and Ruff checks in GitHub Actions for pull requests to
  `main`.

## Requirements

- Python 3.12
- [uv](https://docs.astral.sh/uv/)

## Setup

From the repository root:

```powershell
uv python install 3.12
uv sync
```

The project uses `.python-version`, `pyproject.toml`, and `uv.lock` to keep the
Python version and dependencies reproducible.

## Quick start

Preview the default dataset:

```powershell
uv run python src\ingestion.py
```

Preview another CSV:

```powershell
uv run python src\ingestion.py path\to\products.csv
```

Use the cleaning functions from Python:

```python
from src.ingestion import load_products
from src.transformation import clean_products, deduplicate_products

raw = load_products("dataset/raw/products.csv")
cleaned = clean_products(raw)
latest, duplicates = deduplicate_products(cleaned)
```

`clean_products()` returns a new dataframe. The functions do not persist output
files; `duplicates` is returned separately so duplicate observations are not
silently discarded.

## Documentation

- [Architecture](docs/architecture.md) — implemented pipeline and module roles
- [Data cleaning](docs/data-cleaning.md) — transformation rules and limitations
- [Development](docs/development.md) — workflow, checks, and CI

## Project status

The implemented work covers ingestion, dataframe cleaning, duplicate-SKU
selection, and automated checks. A complete persisted pipeline, validation
issue report, and output-writing CLI are future work.
