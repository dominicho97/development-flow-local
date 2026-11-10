# Development Flow — From Code to Production

**A hands-on project exploring professional software development practices through an end-to-end Python data engineering pipeline.**

Writing working code is only one part of software engineering. Building reliable, maintainable and production-ready systems also requires version control, automated testing, code reviews, CI/CD, containerization and deployment practices.

This project puts those practices into action by developing a realistic data pipeline incrementally, following a professional development workflow:

**GitHub Issue → Feature Branch → Implementation → Testing → Pull Request → CI → Code Review → Merge**

## What This Project Demonstrates

- **Software Development:** Modular Python code, Git workflows, feature branches, meaningful commits and Pull Requests.
- **Quality Engineering:** Unit testing with pytest, code quality enforcement with Ruff and automated CI using GitHub Actions.
- **Data Engineering:** CSV ingestion, data cleaning, transformation and validation using pandas.
- **AI-Assisted Development:** Using coding agents to implement scoped tasks while maintaining human review and verification.
- **Production Engineering (Roadmap):** PostgreSQL, Docker, Airflow, integration testing and deployment automation.

## Project Philosophy

The goal isn't simply to build a working ETL pipeline. It's to understand **how software evolves from a local implementation into a reliable, testable and maintainable system**.

Each feature is developed through a dedicated issue and branch, validated with automated tests, reviewed through a Pull Request and integrated into the main codebase.

The repository documents both the technical implementation and the engineering practices used throughout the development process.

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
