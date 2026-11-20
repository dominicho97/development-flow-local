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
- **CSV ingestion:** Validates required columns and provides a command-line preview of the default dataset.

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




## Data flow

```mermaid
flowchart LR
    A[Raw product CSV] --> B[PostgreSQL staging]
    B --> C[Staging quality checks]
    C -- gates --> D[Python transformation]
    A --> D
    D --> E[PostgreSQL core]
    E --> F[Core quality checks]
```

Airflow coordinates the flow and Soda checks both database layers. Staging
preserves raw observations; transformation reads the CSV, cleans and
deduplicates it, then loads core after the staging checks pass.

## Project status

The CI validation pipeline has passed, including the end-to-end run and image
security gate. Versioned image publishing is configured; deployment is outside
the current scope. See [CI and releases](docs/ci-cd.md) for verification details.

## Requirements

- Python 3.12
- [uv](https://docs.astral.sh/uv/)

## Setup

From the repository root:

```powershell
uv sync --locked
uv run pytest -q
```

For the local Airflow stack, follow the [Docker and Airflow guide](docs/development.md#docker-and-airflow).
Once running, open `http://localhost:8080`, unpause both product DAGs, and
trigger **`products_pipeline`**.

## Documentation

- [Architecture](docs/architecture.md) — pipeline and module roles
- [Data cleaning](docs/data-cleaning.md) and [data quality](docs/data-quality.md)
- [Development and testing](docs/development.md) — Python usage, Docker, Airflow, and tests
- [CI and releases](docs/ci-cd.md) — validation, security gates, and publishing
- [Security review](docs/security-review.md)
- [Agent handover](docs/agent-handover.md)
