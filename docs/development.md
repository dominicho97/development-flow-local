# Development

## Environment

Use uv for Python, virtual environments, dependencies, and commands. The
project supports Python 3.12 and keeps exact resolved dependencies in
`uv.lock`.

```powershell
uv python install 3.12
uv sync
uv run python --version
```

Do not install project dependencies with `pip`. Add dependencies with:

```powershell
uv add <package>
uv add --dev <package>
```

## Local checks

### Configuration-driven CSV loading

`dags/datawarehouse/data_loading.py` can load the raw CSV using a JSON
configuration. For example, create `config.json` at the repository root:

```json
{
  "raw_product_csv_path": "dataset/raw/products.csv"
}
```

Run from the repository root:

```powershell
uv run python -c "from dags.datawarehouse.data_loading import load_data; print(load_data('config.json').head())"
```

`load_data()` returns a validated pandas dataframe using the existing ingestion
function. The configuration must be a JSON object with a non-empty string
path. Relative CSV paths are resolved beside the configuration file, rather
than against the process's working directory. The configuration path itself
is relative to the working directory unless supplied as an absolute path.

Missing configuration or CSV files raise `FileNotFoundError`; malformed JSON,
invalid path values, and invalid CSV data fail explicitly. No default
`config.json` is supplied. When used inside Docker, the configuration and CSV
must both be accessible inside the container. Alternatively, call
`load_data(csv_path="dataset/raw/products.csv")` to skip JSON configuration.
The DAG's warehouse tasks use this direct-path option.

### Test and lint commands

Run the full test suite:

```powershell
uv run python -m pytest tests -v
```

Run Ruff linting and formatting checks:

```powershell
uv run ruff check .
uv run ruff format --check .
```

The suite covers ingestion, transformation, warehouse writes, and Soda scan
routing and failure propagation. These are unit tests with mocked external
services; live database quality is checked by the Soda tasks in Airflow.
PostgreSQL integration tests are skipped by default and require the explicit
`--run-integration` option. Pytest's `testpaths` limits default discovery to
`tests`, avoiding generated Airflow log directories.

### Using conftest.py and unit_test.py

Keep the existing `test_ingestion.py`, `test_transformation.py`, `test_dwh.py`,
and `test_soda.py`. Pytest discovers both `test_*.py` and `*_test.py`, so
`tests/unit_test.py` is collected alongside them without extra configuration.
New tests belong in the file for the relevant module; no duplicate suite is
needed.

`tests/conftest.py` defines shared pytest fixtures. Pytest loads it automatically:
tests request a fixture by including its name as a function parameter, without
importing `conftest`. The `mock_postgres_hook` fixture temporarily replaces
Airflow's Postgres hook during a test, then `monkeypatch` restores the previous
module state. It requires neither Airflow locally nor a PostgreSQL server.

`tests/unit_test.py` requests that fixture and calls the real
`get_db_connection()` helper. It verifies that the helper uses connection ID
`postgres_db_yt_elt`, calls the hook's `get_conn()` method, and returns that
connection. It does not validate actual credentials or database connectivity.
Compose supplies the real connection with `AIRFLOW_CONN_POSTGRES_DB_YT_ELT`;
`POSTGRES_CONN_URI` is not used by this helper.

Run commands from the repository root:

```powershell
# Run only the new test file.
uv run python -m pytest tests/unit_test.py -v

# Run one test explicitly.
uv run python -m pytest tests/unit_test.py::test_postgres_connection_uses_warehouse_hook -v

# Show available fixtures and inspect test discovery.
uv run python -m pytest --fixtures tests/unit_test.py
uv run python -m pytest tests --collect-only -q

# Run the local suite (live database tests skip by default).
uv run python -m pytest tests -q
```

Use `tests` explicitly to avoid collecting generated Airflow log directories.
The `dagbag` fixture in `conftest.py` loads repository DAGs with examples
disabled and adds the repository and DAG directories to the test import path.
It imports the correctly capitalized `DagBag` class inside the fixture, so
collecting ordinary unit tests does not require Airflow.

`test_dag_integrity` verifies all of the following:

- No DAG files have import errors; error details appear in assertion output.
- Exactly one DAG is loaded, with the exact ID `products_elt`. Missing and
  unexpected DAGs fail the test.
- `products_elt` contains exactly seven tasks, including both quality gates.

The explicit contract is `expected_tasks_per_dag = {"products_elt": 7}` in
`tests/unit_test.py`. Update this mapping when intentionally adding a DAG or
changing its task count. Each DAG is checked against its own expected count.
The separate quality-gate test below verifies dependency relationships;
counting tasks alone does not validate execution order.

`test_products_dag_loads_with_quality_gates` verifies there are no DAG import
errors and that both quality gates have the expected task dependencies. It
loads DAG definitions without executing tasks or scanning PostgreSQL.
Both DAG tests are skipped when Airflow is not installed; run them with pytest in an
environment containing the project's Airflow version and providers to exercise
the real DAG loader:

```powershell
uv run python -m pytest tests/unit_test.py::test_dag_integrity -v
uv run python -m pytest tests/unit_test.py::test_products_dag_loads_with_quality_gates -v
```

The latest targeted verification collected three tests in `unit_test.py`:
the mocked connection test passed, and both DagBag tests skipped because
Airflow is absent locally. Lint and formatting checks passed. Actual DagBag
integrity assertions still need execution in an Airflow-capable environment.

For real PostgreSQL quality checks, trigger `products_elt` and inspect
`check_staging_quality` and `check_core_quality`, as described in the
[data quality guide](data-quality.md).

### PostgreSQL integration test

`tests/integration_test.py` adds a connection smoke test. It opens a cursor,
executes `SELECT 1`, and expects `(1,)`. This checks connectivity and query
execution; it does not check whether the database is empty, validate product
rows, or run Soda. A context manager closes the cursor, and the
`real_postgres_connection` fixture yields the connection and closes it in
`finally`, including when the test fails. Connection or query errors propagate
as pytest failures.

The new fixture in `tests/conftest.py` calls the real warehouse
`get_db_connection()` helper. It needs Airflow and the PostgreSQL provider,
the configured `postgres_db_yt_elt` connection, and network access to the ELT
database. Unlike `mock_postgres_hook`, it does not mock external services.

The module has a registered `integration` marker. Collection skips these tests
unless `--run-integration` is supplied; the fixture independently checks the
same option before opening a connection. Default local and CI runs therefore
need no database. Even directly selecting the file without the option skips
the live test.

In an environment containing the project's Airflow version and PostgreSQL
provider, with its warehouse connection configured and database reachable, run:

```powershell
uv run python -m pytest tests/integration_test.py --run-integration -v
# Alternatively, select all tests marked integration.
uv run python -m pytest tests -m integration --run-integration -v
```

These invocations have not yet been verified against a live database. The
plain local uv environment does not install Airflow; the option enables tests
but does not install their runtime or configure credentials. When explicitly
enabled, missing dependencies or an unreachable database fail the test.

An earlier default-suite verification reported **74 passed, 2 skipped** before
the E2E and additional DAG integrity tests were added. Use the current pytest
summary for up-to-date counts; live database, E2E, and Airflow-dependent DAG
tests have separate opt-in or dependency requirements as described here.

### End-to-end Airflow test

`tests/test_airflow_e2e.py` runs from the host and uses the Docker Compose CLI
to trigger `products_elt` through Airflow. It exercises the running scheduler,
executor, worker, CSV transformations, PostgreSQL loads, and both Soda scans.
The host needs Docker and uv, but does not need a local Airflow installation.

Start the Compose stack with the latest built image, wait for healthy services,
and unpause `products_elt` in the UI. Run this on the local development stack:
it performs real warehouse upserts and rewrites processed CSV outputs. Do not
run another pipeline run concurrently against the shared input/output files.

```powershell
docker compose up -d
docker compose ps
uv run python -m pytest tests/test_airflow_e2e.py --run-e2e -v -s
```

The test prints a unique `e2e__...` run ID, polls for up to ten minutes, requires
all seven tasks to succeed, and verifies both processed CSV files exist. A
failed quality gate fails the test with task states. This is a success-path
test: known bad core data is not accepted as a passing result. The run and its
logs remain in Airflow for inspection; a timeout does not cancel the run.

E2E tests skip unless `--run-e2e` is supplied. This flag is independent from
`--run-integration`: the latter enables the direct database connection test,
which requires an Airflow-capable Python environment. Default CI runs enable
neither. No live E2E run has yet been verified from this development session.

The test uses Airflow's documented [CLI trigger and task-state commands](https://airflow.apache.org/docs/apache-airflow/stable/cli-ref.html).

## Git workflow

Use a feature branch based on the latest `main` for a change:

```powershell
git switch main
git pull --ff-only
git switch -c feature/<short-description>
```

Keep changes focused. Update the relevant documentation and tests with the
implementation. Before opening a pull request, run the local checks above and
review the diff:

```powershell
git diff --check
git status --short
git diff
```

Open a pull request targeting `main`. Merge only after the checks and review
are complete. The repository keeps feature branches for learning and reference
when that is useful.

## GitHub Actions

`.github/workflows/ci.yml` runs for pull requests targeting `main`. The job:

1. checks out the repository;
2. installs uv 0.11.14 and Python 3.12;
3. installs dependencies with `uv sync --locked --dev`;
4. runs `uv run python -m pytest -v`;
5. runs `uv run ruff check .`; and
6. runs `uv run ruff format --check .`.

The workflow has read-only repository contents permission. Review the result
from the pull request's Checks tab or the repository's Actions tab.

## Docker and Airflow

For the current Soda setup, the 11 PostgreSQL checks, scan commands, and known
data failures, see [PostgreSQL data quality checks](data-quality.md).

Before starting the stack, set `AIRFLOW_JWT_SECRET` in your local `.env` to a
random secret. Generate one with the managed Python environment:

```powershell
uv run python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copy the output into `.env` as `AIRFLOW_JWT_SECRET=<generated value>`. Keep
this value stable across restarts and keep `.env` out of commits. Compose
requires this variable and passes it to the Airflow services.

Build and start the local stack with Docker Desktop:

```powershell
docker build -t dominicho97/products_elt:1.0.2 .
docker compose up -d
docker compose ps
```

Soda Core Postgres 3.3.14 runs in `/home/airflow/soda-venv` because its
OpenTelemetry dependencies conflict with Airflow 3.4.0. Run scans from Airflow
tasks using a subprocess with `/home/airflow/soda-venv/bin/soda`, or use the
`SODA_PYTHON` environment variable for a Python scan script. Importing Soda
directly into an Airflow task uses the wrong Python environment.

The image exposes `soda` on `PATH`. Verify the installation inside the worker:

```bash
soda --version
uv pip show --python "$SODA_PYTHON" soda-core-postgres
```

To use Soda's Python interactively, activate its environment in the current shell:

```bash
source /home/airflow/soda-venv/bin/activate
python -c "from importlib.metadata import version; print(version('soda-core-postgres'))"
deactivate
```

Plain `pip show` checks Airflow's environment; use the explicit `uv pip show`
command above to inspect Soda's environment.

Airflow is available at `http://localhost:8080`. The dataset is mounted at
`/opt/airflow/dataset`, and PostgreSQL initialization uses
`docker/postgres/init-multiple-databases.sh`.

Stop with `docker compose down`. Use `docker compose down -v` only to delete
the PostgreSQL volume.

### Login and authentication recovery

The shared environment in `docker-compose.yml` explicitly selects FAB for
Airflow 3 authentication:

```yaml
AIRFLOW__CORE__AUTH_MANAGER: airflow.providers.fab.auth_manager.fab_auth_manager.FabAuthManager
```

The initial administrator credentials come from `AIRFLOW_WWW_USER_USERNAME`
and `AIRFLOW_WWW_USER_PASSWORD` in `.env`. Changing these values does not
reset an existing account's password.

If login returns HTTP 401 or `airflow users` fails with
`AirflowSecurityManagerV2` missing `find_user` or `get_all_users`, check the
active authentication manager:

```powershell
docker compose exec airflow-api-server airflow config get-value core auth_manager
```

If this reports `SimpleAuthManager`, ensure the FAB setting above is present
under `&airflow-common-env`, then recreate the services and verify the setting
again:

```powershell
docker compose up -d
docker compose exec airflow-api-server airflow config get-value core auth_manager
```

Once FAB is active, reset the existing user's password (replace `airflow` if
your configured username differs):

```powershell
docker compose exec airflow-api-server airflow users reset-password --username airflow
```

Enter the new password at the prompt. If the account does not exist, create it:

```powershell
docker compose exec airflow-api-server airflow users create --username airflow --firstname Airflow --lastname Admin --role Admin --email airflow@example.com
```

Enter a password when prompted, then log in at `http://localhost:8080`.
These recovery steps preserve the PostgreSQL volume. If the attribute error
persists with FAB active, inspect the API server logs and installed Airflow/FAB
provider versions before making further changes.

### Execution API configuration

For this Airflow 3.4 setup, a working UI does not by itself verify that Celery
tasks can start. The scheduler sends work through Redis, and the worker must
also reach the execution API and present a valid task token.

The shared Compose environment configures:

```yaml
AIRFLOW__CORE__EXECUTION_API_SERVER_URL: 'http://airflow-api-server:8080/execution/'
AIRFLOW__API_AUTH__JWT_SECRET: ${AIRFLOW_JWT_SECRET:?Set AIRFLOW_JWT_SECRET in .env}
```

The URL uses the Compose service name: `localhost` inside the worker refers to
the worker container. The scheduler and API server must share the same JWT
signing secret so the API can validate task tokens. This secret is separate
from the UI account password and Fernet key.

The API server health check uses
`http://localhost:8080/api/v2/monitor/health`. The old `/health` path returned
404 and marked the API container unhealthy even while the UI was available.

After changing shared configuration or the JWT secret, recreate the services:

```powershell
docker compose up -d --force-recreate
docker compose exec airflow-worker airflow config get-value core execution_api_server_url
docker compose ps
```

Confirm the execution URL matches the service URL above and the API server
becomes healthy. Trigger a new DAG run to obtain fresh task tokens. Changing
the JWT secret can also require logging back into the UI.

### Run and verify products_elt

1. Ensure `dataset/raw/products.csv` exists on the host. Compose mounts
   `./dataset:/opt/airflow/dataset` for the Airflow services.
2. Open `http://localhost:8080`, log in, and find `products_elt`.
3. Unpause the DAG and trigger a manual run; it has no automatic schedule.
4. Confirm `extract`, `update_staging`, `check_staging_quality`, `transform`,
   `load`, `update_core`, and `check_core_quality`
   execute in that order. With the currently observed data, all tasks through
   `update_core` succeed and `check_core_quality` fails as described below.
5. Verify the persisted files on the host:

The core quality task currently detects a blank product name and a negative
price in the observed dataset. Until those issues are resolved, expect that
task to fail; inspect its Soda output in the task log. See the
[quality guide](data-quality.md) for investigation SQL and layer-specific rules.

```powershell
Get-ChildItem dataset/processed
```

Expect `products_clean.csv` and `products_duplicates.csv`. The `load` task
verifies these files exist. The separate `update_staging` and `update_core`
tasks populate PostgreSQL using the `postgres_db_yt_elt` Airflow connection
provided by Compose.

Verify row counts in the ELT database with your SQL client:

```sql
SELECT COUNT(*) FROM staging.products;
SELECT COUNT(*) FROM core.products;
SELECT * FROM core.products LIMIT 10;
```

Staging retains raw observations by source record ID plus occurrence number
(stored together as JSON text in `source_record_id`); core retains cleaned,
deduplicated products by SKU. Reruns update matching keys without deleting
rows absent from the input. Core reads the raw CSV and applies the shared
transformation functions again; it does not query staging.

Existing tables from the earlier schema need a migration before loading:
staging requires a unique `source_record_id`, and core requires unique `sku`.
Table creation does not upgrade existing tables. Do not delete the PostgreSQL
volume to work around a schema mismatch.

The warehouse DAG was confirmed successful locally on 2026-11-16 before
quality gates were added. The subsequent automated run verified both quality
tasks: staging passed, and only core quality failed on the two known data
issues. The core log reported 9/11 passing checks and Soda exit status 2,
propagated as `CalledProcessError`. The latest code checks passed 73 tests;
Ruff lint and formatting checks passed for the changed Python files.
Run local tests with:

```powershell
uv run python -m pytest tests -q
```

Specifying `tests` avoids collecting Airflow's generated log directories.

Two data issues were resolved during the first warehouse runs:

- Repeated raw `record_id` values are valid staging observations. Staging
  combines the original ID and its occurrence number into a unique key,
  preserving repeated observations and making retries of the same file safe.
- Blank or missing SKUs cannot identify core products. Core transformation
  excludes these rows and logs the skipped count. The rows remain in staging
  and processed CSV outputs; the database writer still validates core keys.

To retry a failed warehouse task after a fix, clear that task in Airflow or
trigger a new run. Changes under the mounted `dags/` directory need no image
rebuild; changes to image dependencies or copied `src/` code require rebuilding.

### Diagnose task startup failures

The executor message reporting a failed task whose state is still `queued`
is a symptom. Inspect the worker log for the underlying error:

```powershell
docker compose logs --since 5m --tail 100 airflow-worker
docker compose logs --since 5m --tail 100 airflow-api-server
docker compose ps
```

In this setup we resolved these failures:

| Symptom | Cause and resolution |
| --- | --- |
| `ConnectError: [Errno 111] Connection refused` before task startup | Configure the execution API URL with the API server's Compose service name. |
| `ServerResponseError: Invalid auth token` after connectivity was fixed | Configure the same JWT secret for the scheduler and API server, recreate services, and trigger a fresh run. |
| API server unhealthy with `/health` returning 404 | Update the health-check path to `/api/v2/monitor/health`. |

The products DAG ran successfully after these configuration fixes. No
PostgreSQL volume deletion was needed.
