"""Unit checks for the warehouse's Airflow connection boundary."""

from dags.datawarehouse.data_utils import get_db_connection


def test_postgres_connection_uses_warehouse_hook(mock_postgres_hook):
    connection = get_db_connection()

    mock_postgres_hook.assert_called_once_with(postgres_conn_id="postgres_db_yt_elt")
    mock_postgres_hook.return_value.get_conn.assert_called_once_with()
    assert connection is mock_postgres_hook.return_value.get_conn.return_value
