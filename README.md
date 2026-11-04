# development-flow-local

## Progress so far

- Set up uv as the project’s only Python and dependency workflow.
- Pinned the supported Python version to 3.12 with `.python-version` and
  `requires-python = ">=3.12,<3.13"`.
- Added pandas as a runtime dependency and pytest and Ruff as development
  dependencies.
- Added `uv.lock` with seven-day `exclude-newer` resolution and major-version
  bounds for dependencies added with `uv add`.
- Added `src/ingestion.py` with CSV loading and required-column validation.
- Added a command-line entry point that prints the loaded dataframe.
- Added the sample input at `dataset/raw/products.csv`.
- Added ingestion tests; the current test suite passes all 4 tests.
- Added `AGENTS.md` with project conventions for future development.

The current ingestion stage validates the CSV structure and displays the raw
dataframe. Data normalization and business-rule validation can be added in the
next stage.

## Issues and features implemented

### Features

- **UV-based project setup:** Python, virtual environments, dependencies, and
  lockfiles are managed through uv.
- **Pinned Python runtime:** The project uses Python 3.12.
- **Dependency reproducibility:** Added `uv.lock`, major dependency bounds, and
  a seven-day `exclude-newer` window.
- **CSV ingestion:** Added `load_products()` to read UTF-8 CSV files as strings
  and validate required columns.
- **Dataframe inspection:** Added a CLI that prints the loaded dataframe.
- **Custom input files:** The ingestion CLI accepts an optional CSV path.

### Issues fixed

- Replaced the invalid `print(pd.df)` statement with printing the loaded local
  dataframe.
- Added a `main()` entry point so running `src\ingestion.py` performs ingestion.
- Added `src\__init__.py` and pytest path configuration so tests can import the
  ingestion module reliably.
- Added automated ingestion tests covering valid input, missing files, missing
  columns, and malformed CSV data.

## Delivery workflow

Use this checklist when implementing a feature or fixing an issue:

- [x] Create an issue describing the feature or problem.
- [x] Create and publish a feature branch.
- [x] Implement the change and update documentation.
- [x] Run the test suite and relevant checks.
- [x] Commit and push the changes.
- [x] Create a pull request.
- [x] Review the code changes.
- [x] Merge the pull request into `main`.

### Current delivery status

The current feature has been merged into `main`. The feature branch is being
kept intentionally for learning and reference, so it should not be deleted after
merge. Future work should use a new feature branch created from the latest
`main`.

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
