# development-flow-local

## Development setup

This project uses [uv](https://docs.astral.sh/uv/) for Python version management,
virtual environments, dependency installation, and locking. Do not install project
dependencies with `pip` directly.

### Prerequisites

Install uv, then run the following commands from the project root:

```powershell
uv python install 3.12
uv sync
```

The project is pinned to Python 3.12 through `.python-version` and
`requires-python` in `pyproject.toml`. `uv sync` creates or updates `.venv` and
`uv.lock`.

Run Python commands through uv:

```powershell
uv run python --version
uv run python your_script.py
```

Load and print the default product dataset:

```powershell
uv run python src\ingestion.py
```

To load a different CSV:

```powershell
uv run python src\ingestion.py path\to\products.csv
```

Add dependencies with uv:

```powershell
uv add <package>
uv add --dev <package>
```

Commit `pyproject.toml`, `.python-version`, and `uv.lock`. Do not commit `.venv`.

### Reproducibility settings

The project uses major-version bounds for dependencies added with `uv add`.
Dependency candidates newer than seven days are excluded during resolution. The
checked-in `uv.lock` remains the source of exact dependency versions; update it
intentionally with:

```powershell
uv lock
uv sync
```
