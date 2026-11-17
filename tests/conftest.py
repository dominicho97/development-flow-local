"""Shared fixtures for unit tests; no running Airflow or database is needed."""

import sys
from types import ModuleType
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_postgres_hook(monkeypatch):
    """Replace the lazily imported Airflow hook with a controlled test double."""
    module_name = "airflow.providers.postgres.hooks.postgres"
    module = ModuleType(module_name)
    hook = MagicMock(name="PostgresHook")
    module.PostgresHook = hook
    monkeypatch.setitem(sys.modules, module_name, module)
    return hook
