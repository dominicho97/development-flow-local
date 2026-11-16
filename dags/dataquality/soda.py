"""Run warehouse quality checks in Soda's isolated Python environment."""

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)
SODA_EXECUTABLE = "/home/airflow/soda-venv/bin/soda"
SODA_PATH = Path("/opt/airflow/include/soda")
LAYER_CHECKS = {
    "staging": ("postgres_staging", "checks_staging.yml"),
    "core": ("postgres_core", "checks.yml"),
}


def products_elt_data_quality(layer: str) -> None:
    """Stream scan results and fail the task when Soda exits unsuccessfully."""
    if layer not in LAYER_CHECKS:
        raise ValueError("Expected staging or core layer.")
    datasource, checks_file = LAYER_CHECKS[layer]
    configuration = SODA_PATH / "configuration.yml"
    checks = SODA_PATH / checks_file
    for path in (configuration, checks):
        if not path.is_file():
            raise FileNotFoundError(f"Soda configuration file not found: {path}")
    logger.info("Running Soda checks for %s.products", layer)
    subprocess.run(
        [
            SODA_EXECUTABLE,
            "scan",
            "-d",
            datasource,
            "-c",
            str(configuration),
            str(checks),
        ],
        check=True,
    )
