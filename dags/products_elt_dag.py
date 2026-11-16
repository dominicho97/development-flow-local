from pathlib import Path

import pendulum
from airflow.sdk import dag, task
from datawarehouse.dwh import core_table, staging_table

from src.ingestion import load_products
from src.transformation import clean_products, deduplicate_products

DATASET_DIR = Path("/opt/airflow/dataset")
RAW_FILE = DATASET_DIR / "raw" / "products.csv"
PROCESSED_DIR = DATASET_DIR / "processed"
CLEAN_FILE = PROCESSED_DIR / "products_clean.csv"
DUPLICATES_FILE = PROCESSED_DIR / "products_duplicates.csv"


@dag(
    dag_id="products_elt",
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    schedule=None,
    catchup=False,
    tags=["products", "elt"],
)
def products_elt_dag():
    @task
    def extract() -> str:
        """Validate the raw product file and pass its path downstream."""

        load_products(RAW_FILE)
        return str(RAW_FILE)

    @task
    def transform(raw_file: str) -> tuple[str, str]:
        """Clean products and separate duplicate rows for audit."""

        raw_products = load_products(raw_file)
        cleaned_products = clean_products(raw_products)
        latest_products, duplicate_products = deduplicate_products(cleaned_products)

        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        latest_products.to_csv(CLEAN_FILE, index=False)
        duplicate_products.to_csv(DUPLICATES_FILE, index=False)

        return str(CLEAN_FILE), str(DUPLICATES_FILE)

    @task
    def load(output_files: tuple[str, str]) -> None:
        """Confirm that the transformed output files were written."""

        for output_file in output_files:
            if not Path(output_file).is_file():
                raise FileNotFoundError(
                    f"Expected output file was not created: {output_file}"
                )

    @task
    def update_staging(raw_file: str) -> int:
        """Insert or update raw observations in staging.products."""
        return staging_table(csv_path=raw_file)

    @task
    def update_core(raw_file: str) -> int:
        """Insert or update cleaned, deduplicated products in core.products."""
        return core_table(csv_path=raw_file)

    raw_file = extract()
    staging = update_staging(raw_file)
    outputs = transform(raw_file)
    verified = load(outputs)
    core = update_core(raw_file)

    staging >> outputs
    verified >> core


products_elt_dag()
