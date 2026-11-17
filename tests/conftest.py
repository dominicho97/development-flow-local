"""Shared unit fixtures and optional Airflow DAG-loading fixtures."""

import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--run-e2e",
        action="store_true",
        default=False,
        help="Trigger and validate a real products_elt run through Docker Compose.",
    )
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests requiring Airflow and a live PostgreSQL database.",
    )


def pytest_collection_modifyitems(config, items):
    for item in items:
        if "integration" in item.keywords and not config.getoption("--run-integration"):
            item.add_marker(pytest.mark.skip(reason="Use --run-integration"))
        if "e2e" in item.keywords and not config.getoption("--run-e2e"):
            item.add_marker(pytest.mark.skip(reason="Use --run-e2e"))


@pytest.fixture
def dagbag(monkeypatch):
    """Load repository DAGs when Airflow is available; otherwise skip the test."""
    # Local unit tests do not require Airflow. Only tests requesting this fixture
    # are skipped if Airflow is unavailable; the rest of the suite still runs.
    pytest.importorskip("airflow", reason="DagBag tests require Airflow")
    from airflow.dag_processing.dagbag import DagBag

    project_root = Path(__file__).resolve().parents[1]
    dags_folder = project_root / "dags"
    # Mirror the container's import paths for src, datawarehouse, and dataquality.
    # monkeypatch restores these paths after the test finishes.
    monkeypatch.syspath_prepend(str(project_root))
    monkeypatch.syspath_prepend(str(dags_folder))
    # Parse our DAG files and collect their task definitions and import errors.
    # Airflow 3.4 scans this explicit folder; include_examples was removed.
    # Loading does not execute our task bodies.
    return DagBag(dag_folder=str(dags_folder))


@pytest.fixture
def mock_postgres_hook(monkeypatch):
    """Replace the lazily imported Airflow hook with a controlled test double."""
    module_name = "airflow.providers.postgres.hooks.postgres"
    module = ModuleType(module_name)
    hook = MagicMock(name="PostgresHook")
    module.PostgresHook = hook
    monkeypatch.setitem(sys.modules, module_name, module)
    return hook


@pytest.fixture
def real_postgres_connection(request):
    """Open a live warehouse connection and always close it after the test."""
    # Guard the fixture too, so accidentally using it in an unmarked test
    # cannot open a database connection during an ordinary local or CI run.
    if not request.config.getoption("--run-integration"):
        pytest.skip("Use --run-integration to test the live database")
    from dags.datawarehouse.data_utils import get_db_connection

    connection = get_db_connection()
    try:
        yield connection
    finally:
        connection.close()
