"""Shared unit fixtures and optional Airflow DAG-loading fixtures."""

import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def dagbag(monkeypatch):
    """Load repository DAGs when Airflow is available; otherwise skip the test."""
    # Local unit tests do not require Airflow. Only tests requesting this fixture
    # are skipped if Airflow is unavailable; the rest of the suite still runs.
    pytest.importorskip("airflow", reason="DagBag tests require Airflow")
    from airflow.models.dagbag import DagBag

    project_root = Path(__file__).resolve().parents[1]
    dags_folder = project_root / "dags"
    # Mirror the container's import paths for src, datawarehouse, and dataquality.
    # monkeypatch restores these paths after the test finishes.
    monkeypatch.syspath_prepend(str(project_root))
    monkeypatch.syspath_prepend(str(dags_folder))
    # Parse our DAG files and collect their task definitions and import errors.
    # Exclude Airflow's example DAGs. Loading does not execute our task bodies.
    return DagBag(dag_folder=str(dags_folder), include_examples=False)


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
def test_real_postgres_connection():
    """Return a real connection to the warehouse's PostgreSQL database.

    This fixture is only for tests that need to verify the warehouse's
    actual database state. It is not used by default, because it requires
    a running PostgreSQL container and can be slow.
    """
    from dags.datawarehouse.data_utils import get_db_connection

    return get_db_connection()
