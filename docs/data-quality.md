# PostgreSQL data quality checks

Soda Core Postgres is pinned to `3.3.14` in `pyproject.toml`, with resolved
dependencies in `uv.lock`. The Docker image is `dominicho97/products_elt:1.0.2`.
Scans currently run manually against `core.products`; the `products_elt` DAG
does not yet invoke Soda or fail automatically when a quality check fails.

## Runtime and installation

Airflow 3.4.0 and Soda 3.3.14 require incompatible OpenTelemetry versions.
The Dockerfile installs Soda in `/home/airflow/soda-venv` and keeps its
dependencies separate from Airflow's Python environment. Future Airflow scan
tasks should invoke Soda through a subprocess using its full executable path.
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

- `include/soda/configuration.yml` defines data source `postgres_core`, using
  the `core` schema and the existing `POSTGRES_CONN_HOST`, `POSTGRES_CONN_PORT`,
  `ELT_DATABASE_NAME`, `ELT_DATABASE_USERNAME`, and `ELT_DATABASE_PASSWORD`
  environment variables passed to the worker by Compose. Credentials are not
  stored in the YAML file.
- `include/soda/checks.yml` defines the checks for `products` in that schema.
- Compose mounts `./include` at `/opt/airflow/include`. Changes to these YAML
  files are available immediately and require no image rebuild.

Run `products_elt` successfully first to populate the warehouse, then execute
from PowerShell at the repository root:

```powershell
docker exec airflow-worker /home/airflow/soda-venv/bin/soda scan -d postgres_core -c /opt/airflow/include/soda/configuration.yml /opt/airflow/include/soda/checks.yml
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

## Latest observed scan and investigation

The initial four checks passed. After expanding to 11 checks, the local scan
on 2026-11-16 reported **9 passed, 2 failed, 0 warnings, and 0 errors**:

- `missing_count(product_name) = 0` found one missing or blank name.
- `invalid_count(listed_price) = 0` found one negative price.

These are data quality failures, rather than installation or connection
errors. They remain unresolved; no cleanup or quarantine behavior has been
implemented for these records. Investigate in the ELT database with a SQL client:

```sql
SELECT record_id, sku, product_name, listed_price
FROM core.products
WHERE product_name IS NULL
   OR product_name ~ '^\s*$'
   OR listed_price < 0;
```

Decide the intended handling before changing data or transformation rules.
The current price cleaner accepts parseable negative numbers, and blank
product names can remain empty strings. PostgreSQL `NOT NULL` does not reject
an empty string. Warehouse upserts also retain products absent from later
inputs, so a later load alone does not guarantee removal of an affected row.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| Dependency resolution fails on OpenTelemetry | Preserve the separate Soda environment; do not install Soda into Airflow's Python. |
| `soda` is missing from `PATH` | Use the full executable path above. Rebuild and recreate containers to pick up the Dockerfile's CLI symlink. |
| Plain `pip show soda-core-postgres` reports no package | Inspect Soda with `uv pip show --python /home/airflow/soda-venv/bin/python soda-core-postgres`. Plain `pip` inspects Airflow's environment. |
| `ModuleNotFoundError: No module named 'distutils'` | Rebuild with the updated `pyproject.toml` and `uv.lock`, which include `setuptools`, then recreate containers. |
| uv cache permission error while building | Ensure `/tmp/.cache/uv` is created and owned by `airflow:root` before `uv venv` runs as `airflow`. |
| Checks fail with measured values | Investigate the affected records and business rules; a completed scan can still report failing data. |
