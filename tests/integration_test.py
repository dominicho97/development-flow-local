"""Opt-in checks against the real warehouse database."""

import pytest

pytestmark = pytest.mark.integration


def test_real_postgres_connection(real_postgres_connection):
    """Verify connectivity and SQL execution, without changing warehouse data."""
    # The context manager closes the cursor even when execution/assertion fails.
    # The fixture separately owns and closes the connection.
    with real_postgres_connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        assert cursor.fetchone() == (1,)
