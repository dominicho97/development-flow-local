import argparse
from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = {
    "record_id",
    "sku",
    "product_name",
    "listed_price",
}


def load_products(file_path: str | Path) -> pd.DataFrame:
    """Read a raw product CSV and validate its structure."""

    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError(f"CSV file not found: {path}")

    try:
        df = pd.read_csv(
            path,
            encoding="utf-8-sig",
            dtype=str,
            keep_default_na=False,
            on_bad_lines="error",
        )
    except (
        pd.errors.ParserError,
        pd.errors.EmptyDataError,
        UnicodeError,
    ) as exc:
        raise ValueError(f"Invalid CSV file: {path}") from exc

    missing_columns = REQUIRED_COLUMNS - set(df.columns)

    if missing_columns:
        raise ValueError(f"Missing required columns: {sorted(missing_columns)}")

    return df


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    default_file = project_root / "dataset" / "raw" / "products.csv"

    parser = argparse.ArgumentParser(description="Load and print product data.")
    parser.add_argument(
        "file_path",
        nargs="?",
        type=Path,
        default=default_file,
        help=f"Path to a product CSV (default: {default_file})",
    )
    args = parser.parse_args()

    df = load_products(args.file_path)
    print(f"Successfully loaded {len(df)} products.")
    print(df.head())


if __name__ == "__main__":
    main()
