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
- Core reloads and transforms the raw CSV; it does not read staging. Staging
  retains raw observations, while core keeps deduplicated products by SKU.
- Default local tests mock external services or skip tests that need Airflow,
  a live database, or E2E. CI runs those checks against a disposable stack.
  Linux image dependencies are locked in the `airflow` group.
- Preserve raw staging data, the Celery compatibility bound, and the security
  gate. The pip VEX statement requires its runtime verification step.
- Keep secrets in local `.env`; CI generates disposable credentials. Changes to
  image dependencies or copied code require rebuilding.
- CI publishes the validated runtime image only on successful version-tag runs;
  it does not deploy. The reported passing CI run is dated 2026-11-17, and
  release publishing was not separately confirmed. Check the relevant Actions
  run for current results.

See [development and testing](development.md), [architecture](architecture.md),
[data quality](data-quality.md), and [CI and releases](ci-cd.md) for details.
