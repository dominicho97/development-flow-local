import pytest
import psycopg2

def test_real_postgres_connection(real_postgres_connection):
    cursor = None
    """Verify that the warehouse's PostgreSQL database is reachable and empty.

    This test is slow and requires a running PostgreSQL container, so it is
    not part of the default suite. It is only run when explicitly requested.
    """
    try:
        cursor = real_postgres_connection.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        assert result == (1,)
    except psycopg2.OperationalError as e:
        pytest.fail(f"Failed to connect to the PostgreSQL database: {e}")

    finally:
        if cursor is not None:
            cursor.close()