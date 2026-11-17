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
- Run Soda quality gates after staging and core loads: seven staging checks
  and 11 core checks covering schema, completeness, uniqueness, and validity.
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

Use the cleaning functions from a Python session. Start the uv-managed Python
REPL first:

```powershell
uv run python
```

Then paste this Python code at the `>>>` prompt:

```python
from src.ingestion import load_products
from src.transformation import clean_products, deduplicate_products

raw = load_products("dataset/raw/products.csv")
cleaned = clean_products(raw)
latest, duplicates = deduplicate_products(cleaned)
print(f"Loaded: {len(raw)}; latest: {len(latest)}; duplicates: {len(duplicates)}")
```

Do not paste the Python block directly into PowerShell. To run it as a script,
save it as a `.py` file in the repository and execute it with `uv run python
path\to\your_script.py`.

`clean_products()` returns a new dataframe. The functions do not persist output
files; `duplicates` is returned separately so duplicate observations are not
silently discarded.

## Docker and Airflow

Follow the [Airflow setup and DAG verification guide](docs/development.md#docker-and-airflow)
to configure the required `AIRFLOW_JWT_SECRET` in `.env` before startup and
verify a successful `products_elt` run.

Docker Desktop is required. Build the image and start the stack:

```powershell
docker build -t dominicho97/products_elt:1.0.2 .
docker compose up -d
docker compose ps
```

Airflow is available at `http://localhost:8080`. The `dataset/` directory is
mounted at `/opt/airflow/dataset`.

Authentication uses the FAB auth manager configured in `docker-compose.yml`.
Initial administrator credentials are configured in `.env` with
`AIRFLOW_WWW_USER_USERNAME` and `AIRFLOW_WWW_USER_PASSWORD`. See
[login and authentication recovery](docs/development.md#login-and-authentication-recovery)
for HTTP 401 errors, password resets, and authentication-manager checks.

Stop the stack with:

```powershell
docker compose down
```

PostgreSQL initialization is handled by
`docker/postgres/init-multiple-databases.sh`. Use `docker compose down -v` only
if you intentionally want to delete the database volume.

## Documentation

- [Architecture](docs/architecture.md) — implemented pipeline and module roles
- [Data cleaning](docs/data-cleaning.md) — transformation rules and limitations
- [Data quality](docs/data-quality.md) — Soda setup, scan commands, checks, and known failures
- [Development](docs/development.md) — workflow, checks, and CI

The [test guide](docs/development.md#using-conftestpy-and-unit_testpy) explains
shared fixtures, the mocked connection test, and optional DagBag validation.
The DAG integrity test requires no import errors, exactly the `products_elt`
DAG, and seven tasks. It skips locally when Airflow is unavailable.
The PostgreSQL connection integration test is opt-in with `--run-integration`
and closes its cursor and connection after use. It requires an Airflow-capable
environment and a reachable warehouse database; ordinary local and CI runs
skip it.

An opt-in [end-to-end test](docs/development.md#end-to-end-airflow-test) can
trigger `products_elt` on the live Docker Compose stack and verify all seven
tasks, both Soda scans, and processed output files. Run it from the host with
`uv run pytest tests/test_airflow_e2e.py --run-e2e -v -s`.

## Project status

The implemented work covers ingestion, dataframe cleaning, duplicate-SKU
selection, an Airflow DAG with persisted outputs, and automated checks.
The DAG includes staging and core PostgreSQL loading tasks. A full local run
was confirmed successful before quality gates were added on 2026-11-16.
The subsequent automated quality-gated run passed staging and failed only
`check_core_quality`, confirming that Soda failures propagate to Airflow.
The core scan reported 9 of
11 checks passing, with one blank product name and one negative price requiring
investigation. Soda now runs automatically after each warehouse layer loads;
validation-issue reporting remains future work.
