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
