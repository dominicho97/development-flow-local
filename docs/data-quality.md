# PostgreSQL data quality checks

Soda Core Postgres is pinned to `3.3.14` in `pyproject.toml`, with resolved
dependencies in `uv.lock`. The Docker image is `dominicho97/products_elt:1.0.2`.
The `products_elt` DAG runs scans against both `staging.products` and
`core.products`. Each scan is also available as a manual command.

## Airflow quality gates

The full CI E2E run, including both quality tasks, was confirmed passing on
2026-11-17. The earlier failures below are historical examples of the gates
catching data issues, not the expected result of the current pipeline.

The task sequence is `extract -> update_staging -> check_staging_quality ->
transform -> load -> update_core -> check_core_quality`.
`dags/dataquality/soda.py` runs the isolated Soda executable as a subprocess,
streams its output to task logs, and propagates nonzero exit codes to Airflow.
A failed staging scan blocks downstream processing; a failed core scan marks
the run unsuccessful after the core load has committed. Scans do not roll back
loaded data. Blank names are now excluded from core and negative prices become
SQL NULL; raw observations remain in staging. These rules preserve the checks
and were validated by the passing E2E run.

Staging uses `postgres_staging` and `include/soda/checks_staging.yml` for seven
checks: expected columns and raw text types, a nonempty table, present/unique/
positive warehouse record IDs, and present/unique source observation keys.
Raw SKU duplicates, blank names, and unclean prices remain allowed in staging.
Core uses the existing 11 checks in `checks.yml`.

Both `dags/` and `include/` are mounted, so these task and YAML changes need no
image rebuild when the image already contains the working Soda environment.
Trigger a new `products_elt` run to execute the new tasks.

## Runtime and installation

Airflow 3.4.0 and Soda 3.3.14 require incompatible OpenTelemetry versions.
The Dockerfile installs Soda in `/home/airflow/soda-venv` and keeps its
dependencies separate from Airflow's Python environment. Airflow scan
tasks invoke Soda through a subprocess using its full executable path.
`SODA_PYTHON` points to that environment's Python interpreter.

The Dockerfile creates `/tmp/.cache/uv` as root and assigns ownership to
`airflow:root` before creating the environment. The project also includes
`setuptools`, which provides the `distutils.util` module imported by this
Soda version on Python 3.12. Image build checks run `soda --version` and
inspect the installed package.

After dependency or Dockerfile changes, rebuild and recreate containers:

```powershell
docker build -t dominicho97/products_elt:1.0.2 .
docker compose up -d --force-recreate
docker exec airflow-worker /home/airflow/soda-venv/bin/soda --version
docker exec airflow-worker uv pip show --python /home/airflow/soda-venv/bin/python soda-core-postgres
```

## Configuration and scan command

- `include/soda/configuration.yml` defines `postgres_staging` for the `staging`
  schema and `postgres_core` for the `core` schema, using `POSTGRES_CONN_HOST`, `POSTGRES_CONN_PORT`,
  `ELT_DATABASE_NAME`, `ELT_DATABASE_USERNAME`, and `ELT_DATABASE_PASSWORD`
  environment variables passed to the worker by Compose. Credentials are not
  stored in the YAML file.
- `include/soda/checks.yml` defines core checks, while
  `include/soda/checks_staging.yml` defines staging checks.
- Compose mounts `./include` at `/opt/airflow/include`. Changes to these YAML
  files are available immediately and require no image rebuild.

Run the warehouse loading tasks first to populate the tables, then execute
from PowerShell at the repository root:

```powershell
docker exec airflow-worker /home/airflow/soda-venv/bin/soda scan -d postgres_core -c /opt/airflow/include/soda/configuration.yml /opt/airflow/include/soda/checks.yml
```

To scan staging manually:

```powershell
docker exec airflow-worker /home/airflow/soda-venv/bin/soda scan -d postgres_staging -c /opt/airflow/include/soda/configuration.yml /opt/airflow/include/soda/checks_staging.yml
```

## Current checks

The file defines 11 checks. The schema check groups several validations into
one result.

| Area | Expected behavior |
| --- | --- |
| Schema | `record_id` is bigint; `sku`, `product_name`, and `category` are text; `listed_price` is numeric; `stock_qty` is integer. All six columns must exist. |
| Availability | The table contains at least one row. |
| Record IDs | IDs are present, unique, and at least 1 (three checks). |
| SKUs | SKUs are present, not empty or whitespace-only, and unique (two checks). |
| Product names | Names are present and not empty or whitespace-only. |
| Prices | Present prices are at least zero. |
| Stock | Present quantities are at least zero. |
| Text cleaning | SKUs and names have no leading or trailing spaces; present categories are nonempty and have no leading or trailing spaces, using PostgreSQL `BTRIM`. |

Missing prices, stock quantities, and categories remain allowed by the current
warehouse rules. The validity checks do not impose completeness requirements
on these nullable fields. Checks apply to columns actually stored in core;
CSV-only fields such as `last_seen` and `currency` are not scanned.

The checks use Soda's documented [schema checks](https://docs.soda.io/soda-documentation/soda-v3/sodacl-reference/schema),
[missing metrics](https://docs.soda.io/soda-documentation/soda-v3/sodacl-reference/missing-metrics),
and [validity metrics](https://docs.soda.io/soda-documentation/soda-v3/sodacl-reference/validity-metrics).

## Earlier scan failures and their resolution

On 2026-11-17 the E2E run reached core quality and reported 10/11 checks
passing: price validity passed, but one blank product name remained. The
current code now filters missing/blank names after deduplication, logs skipped
products, and rejects blank names at the core writer boundary. Each core load
also removes existing null or whitespace-only names in the upsert transaction;
raw staging rows are preserved. Subsequent full CI E2E runs passed, confirming
both scan layers after the repairs. Rerunning only a scan never changes stored data.

The initial four checks passed. After expanding to 11 checks, the local scan
on 2026-11-16 reported **9 passed, 2 failed, 0 warnings, and 0 errors**:

- `missing_count(product_name) = 0` found one missing or blank name.
- `invalid_count(listed_price) = 0` found one negative price.

The automated Airflow run was also verified on 2026-11-16. All tasks before
`check_core_quality`, including `check_staging_quality`, succeeded. At 15:58
local time, the core task logged the same 9 passing and 2 failing checks and
raised `CalledProcessError` for Soda exit status 2. Only the core quality task
failed. This confirms that both scans execute from the DAG and that a quality
failure propagates to Airflow. Later repairs resolved those failures without
weakening the quality checks.

Tests cover scan routing, nonzero exit propagation, unsupported-layer validation,
and missing-configuration handling. See [CI status](ci-cd.md#verification-status)
for the current verification record.

These are data quality failures, rather than installation or connection
errors. The implemented handling skips and logs blank-name products and maps
negative prices to missing values. Staging remains available for investigation;
there is no separate quarantine table. Use this query to investigate regressions:

```sql
SELECT record_id, sku, product_name, listed_price
FROM core.products
WHERE product_name IS NULL
   OR product_name ~ '^\s*$'
   OR listed_price < 0;
```

The price cleaner rejects negative numbers; core filtering excludes blank names
after choosing the latest observation per SKU. PostgreSQL `NOT NULL` alone
does not reject empty strings. The core writer explicitly removes existing
blank-name rows in its upsert transaction; ordinary products absent from a
later input otherwise remain in the database.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| Dependency resolution fails on OpenTelemetry | Preserve the separate Soda environment; do not install Soda into Airflow's Python. |
| `soda` is missing from `PATH` | Use the full executable path above. Rebuild and recreate containers to pick up the Dockerfile's CLI symlink. |
| Plain `pip show soda-core-postgres` reports no package | Inspect Soda with `uv pip show --python /home/airflow/soda-venv/bin/python soda-core-postgres`. Plain `pip` inspects Airflow's environment. |
| `ModuleNotFoundError: No module named 'distutils'` | Rebuild with the updated `pyproject.toml` and `uv.lock`, which include `setuptools`, then recreate containers. |
| uv cache permission error while building | Ensure `/tmp/.cache/uv` is created and owned by `airflow:root` before `uv venv` runs as `airflow`. |
| Checks fail with measured values | Investigate the affected records and business rules; a completed scan can still report failing data. |
