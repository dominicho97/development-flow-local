# Agent handover

Read [AGENTS.md](../AGENTS.md) first. Use `uv` for Python operations and keep
`pyproject.toml` and `uv.lock` synchronized.

| Area | Stack / entry points |
| --- | --- |
| Runtime | Python 3.12, pandas, Airflow 3.4.0, Celery 5.6.x, Redis, PostgreSQL |
| Quality | Soda Core Postgres 3.5.6 in its own environment; 7 staging and 11 core checks |
| Code | `src/` for cleaning; `dags/` for orchestration and warehouse helpers; `include/soda/` for checks |
| Delivery | Docker Compose, GitHub Actions, Trivy, and version-tag publishing to GHCR |

- `products_pipeline` triggers `products_elt` and propagates failures. Keep
  both DAGs unpaused; their task-count contracts are in `tests/unit_test.py`.
- Local tests mock external services. CI also runs real Airflow, database, and
  end-to-end checks. Linux image dependencies are locked in the `airflow` group.
- Preserve raw staging data, the Celery compatibility bound, and the security
  gate. The pip VEX statement requires its runtime verification step.
- Keep secrets in local `.env`; CI generates disposable credentials. Changes to
  image dependencies or copied code require rebuilding.

See [development and testing](development.md), [architecture](architecture.md),
[data quality](data-quality.md), and [CI and releases](ci-cd.md) for details.
