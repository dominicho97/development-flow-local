# Retail Data Pipeline

A **production-oriented, end-to-end retail data pipeline** built with Python, Apache Airflow, PostgreSQL, and Docker, featuring automated data quality controls and CI/CD validation.

## Executive Summary
<img width="599" height="334" alt="image" src="https://github.com/user-attachments/assets/702b90c0-7884-4b85-9c90-d025602460c4" />

## Overview
This project demonstrates how raw, inconsistent retail product data can be transformed into reliable, analytics-ready datasets through an automated data engineering workflow.
It combines data ingestion, transformation, orchestration, quality assurance, and software delivery practices in a reproducible environment.


## Technical summary
<img width="600" height="332" alt="image" src="https://github.com/user-attachments/assets/538f3064-5e48-404c-a1ce-a84e599cb8e1" />


## Key Features

- **Automated Data Pipeline:** Orchestrates ingestion, transformation, and database loading using Apache Airflow.
- **Data Transformation:** Standardizes product attributes and resolves duplicate SKUs while retaining audit records.
- **Data Quality Assurance:** Implements 18 Soda checks across PostgreSQL staging and core layers.
- **Automated Testing:** Validates Python logic, database integration, and end-to-end pipeline execution.
- **CI/CD & Security:** Uses GitHub Actions for automated validation, container builds, vulnerability scanning, and versioned image publishing workflows.
- **Containerization:** Runs the pipeline with Docker Compose for reproducible local development.

## Technologies Used

| Component | Technologies |
|---|---|
| Programming & Transformation | Python, pandas |
| Orchestration | Apache Airflow |
| Data Storage | PostgreSQL |
| Data Quality | Soda |
| Containerization | Docker, Docker Compose |
| Testing | pytest |
| CI/CD & Security | GitHub Actions, Ruff, Trivy |
| Dependency Management | uv |




## workflow
**Issue → Branch → Implementation → Tests → Pull Request → CI → Review → Merge**

The pipeline ingests a product CSV, preserves raw observations in PostgreSQL
staging, and loads cleaned, deduplicated products into core. Airflow coordinates
the work; Soda validates both database layers.

### Project status

The CI validation pipeline has passed, including the end-to-end run and image
security gate. Versioned image publishing is configured; deployment is outside
the current scope. See [CI and releases](docs/ci-cd.md) for verification details.

### Development and release cycle

```mermaid
flowchart LR
    A[Issue] --> B[Branch and implement]
    B --> C[Local tests]
    C --> D[Pull request]
    D --> E[CI validation]
    E --> F[Review and merge]
    F --> G[Version tag]
    G --> H[Validate tagged commit]
    H --> I[Publish image to GHCR]
    E -- Failure --> B
    H -- Failure --> B
```

CI checks tests and lint, builds the runtime image, validates Airflow and
PostgreSQL, runs the pipeline end to end, and scans the image for security
findings. Publishing uses the validated image after a successful version-tag
run. See the [pipeline guide](docs/ci-cd.md) for the gates and release steps.

## What we learned

- Working code is only the start: reproducible environments, review, testing,
  and container builds make changes dependable.
- Unit tests, real service integration, and end-to-end runs catch different
  problems. A passing unit suite alone cannot validate an Airflow deployment.
- Data quality rules need explicit business decisions. Preserve raw evidence,
  handle invalid records deliberately, and fail the pipeline on violated rules.
- Dependency resolution does not guarantee runtime compatibility. Test the
  imports and execution paths the application actually uses.
- Security findings need investigation: update real vulnerable dependencies,
  reconcile stale inventories, and document narrowly verified exceptions.

## Current capabilities

- Load UTF-8 CSV files as strings and validate required ingestion columns.
- Preview the default product dataset from the command line.
- Normalize product text, categories, prices, stock, dates, countries,
  currencies, and active-status values.
- Select the latest observation for duplicate SKUs while returning duplicate
  rows for audit.
- Run Soda quality gates after staging and core loads: seven staging checks
  and 11 core checks covering schema, completeness, uniqueness, and validity.
- Validate code, Docker builds, Airflow DAGs, PostgreSQL, and full pipeline runs
  in GitHub Actions, with image vulnerability gates and version-tag publishing.

## Requirements

- Python 3.12
- [uv](https://docs.astral.sh/uv/)

## Setup

From the repository root:
=======
Use Python 3.12 and [uv](https://docs.astral.sh/uv/):
>>>>>>> Stashed changes

```powershell
uv sync --locked
uv run pytest -q
```

For the local Airflow stack, follow the [setup guide](docs/development.md#docker-and-airflow).
Once running, open `http://localhost:8080`, unpause both product DAGs, and
trigger **`products_pipeline`**.

## Agent handover

Read [AGENTS.md](AGENTS.md) first. Use `uv` for Python operations and keep
`pyproject.toml` and `uv.lock` synchronized.

| Area | Stack / entry points |
| --- | --- |
| Runtime | Python 3.12, pandas, Airflow 3.4.0, Celery 5.6.x, Redis, PostgreSQL |
| Quality | Soda Core Postgres 3.5.6 in its own environment; 7 staging and 11 core checks |
| Code | `src/` for cleaning; `dags/` for orchestration and warehouse helpers; `include/soda/` for checks |
| Delivery | Docker Compose, GitHub Actions, Trivy, and version-tag publishing to GHCR |

- `products_pipeline` triggers `products_elt` and propagates failures. Keep
  both DAGs unpaused; their task-count contracts are in `tests/unit_test.py`.
- Local tests mock external services. CI also runs real Airflow/database/E2E
  checks. Linux image dependencies are locked in the `airflow` dependency group.
- Preserve raw staging data, the Celery compatibility bound, and the security
  gate. The pip VEX statement requires its runtime verification step.
- Keep secrets in local `.env`; CI generates disposable credentials. Changes to
  image dependencies or copied code require rebuilding.

## Details

<<<<<<< Updated upstream
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
- [CI and releases](docs/ci-cd.md) — full Airflow validation, security gates, and versioned image publishing


