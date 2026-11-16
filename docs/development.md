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

Run the full test suite:

```powershell
uv run python -m pytest -v
```

Run Ruff linting and formatting checks:

```powershell
uv run ruff check .
uv run ruff format --check .
```

The current suite covers ingestion and transformation behavior, including
invalid values and duplicate-SKU selection.

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
docker build -t dominicho97/products_elt:1.0.1 .
docker compose up -d
docker compose ps
```

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
4. Confirm `extract`, `transform`, and `load` all succeed.
5. Verify the persisted files on the host:

```powershell
Get-ChildItem dataset/processed
```

Expect `products_clean.csv` and `products_duplicates.csv`. The final `load`
task verifies these files exist; it does not load records into PostgreSQL.

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
