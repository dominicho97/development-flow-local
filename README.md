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
- Added a command-line entry point that loads and previews the raw dataframe.
- Added `src/transformation.py` with in-memory product cleaning helpers.
- Added string trimming and category standardization for product data.
- Added price normalization for decimal commas, euro symbols, missing values,
  and invalid text.
- Added the sample input at `dataset/raw/products.csv`.
- Added ingestion and transformation tests; the current suite contains 65 tests.
- Added `AGENTS.md` with project conventions for future development.
- Added GitHub Actions CI for pull requests targeting `main`.

The ingestion stage validates the CSV structure and displays a preview of the
raw dataframe. The transformation stage is currently exposed as Python
functions rather than a CLI or persisted output step. Business-rule validation
and a complete pipeline are still planned.

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
- **Product cleaning:** Added `clean_products()` to copy a dataframe, trim
  whitespace in string columns, and standardize selected category variants.
- **Price normalization:** Added `clean_price()` and integrated it into
  `clean_products()` so supported price strings become numeric values and
  missing or invalid values become missing values.
- **Date normalization:** Added `clean_date()` and integrated it into
  `clean_products()` to support the dataset's mixed date formats, remove
  time-of-day values, and convert invalid dates to missing values.
- **Categorical normalization:** Added normalization for category aliases,
  country names/codes, currency codes, and common active-status values.
- **Duplicate handling:** Added `deduplicate_products()` to select the latest
  observation for each valid SKU while returning all duplicate rows in an
  audit dataframe with the selected row marked.
- **Pull request CI:** GitHub Actions installs locked uv dependencies and runs
  pytest and Ruff checks automatically.

### Issues fixed

- Replaced the invalid `print(pd.df)` statement with printing the loaded local
  dataframe.
- Added a `main()` entry point so running `src\ingestion.py` performs ingestion.
- Added `src\__init__.py` and pytest path configuration so tests can import the
  ingestion module reliably.
- Added automated ingestion tests covering valid input, missing files, missing
  columns, and malformed CSV data.
- Added transformation tests covering whitespace trimming, category cleanup,
  price formats, missing prices, invalid price text, stock quantities, and
  date formats, countries, currencies, active-status values, invalid-value
  handling, and duplicate SKU selection.
- Added `.github/workflows/ci.yml` for automated testing and linting.

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

## Continuous integration

The workflow in `.github/workflows/ci.yml` runs on pull requests targeting
`main`. It uses Python 3.12 and uv, installs dependencies from the committed
lockfile, and runs:

```powershell
uv sync --locked --dev
uv run python -m pytest -v
uv run ruff check .
uv run ruff format --check .
```

The workflow grants the job read-only repository contents permission. Check the
pull request's **Checks** tab or the repository's **Actions** tab to review the
CI result.

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

Load and preview the default product dataset:

```powershell
uv run python src\ingestion.py
```

To load a different CSV:

```powershell
uv run python src\ingestion.py path\to\products.csv
```

Use the transformation helpers from Python code:

```python
from src.ingestion import load_products
from src.transformation import clean_products

raw = load_products("dataset/raw/products.csv")
cleaned = clean_products(raw)
```

`clean_products()` returns a new dataframe; it does not write a cleaned CSV.

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

## Current limitations and next steps

- Add a pipeline entry point that runs ingestion and transformation together.
- Add output persistence for cleaned data.
- Add explicit validation reporting so invalid dates and other rejected values
  are retained as traceable data-quality issues.
- Extend duplicate handling to duplicate `record_id` values and define the
  business rule for conflicting observations with missing timestamps.
- Expand normalization beyond the currently supported category and price
  variants.
