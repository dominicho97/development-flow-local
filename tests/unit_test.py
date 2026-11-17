"""Check DAG definitions and the warehouse's mocked Airflow connection boundary."""

from dags.datawarehouse.data_utils import get_db_connection


def test_dag_integrity(dagbag):
    """Require exactly our declared DAGs, with their expected task counts."""
    # Maintain this contract when intentionally adding a DAG or changing tasks.
    expected_tasks_per_dag = {"products_elt": 7}

    # A failed import must fail the test, rather than silently omit a DAG.
    assert not dagbag.import_errors, dagbag.import_errors

    # Verify both the total count and exact IDs: no missing or unexpected DAGs.
    assert len(dagbag.dags) == len(expected_tasks_per_dag), list(dagbag.dags)
    assert set(dagbag.dags) == set(expected_tasks_per_dag)

    # Validate every DAG against its own explicit expected task count.
    for dag_id, expected_count in expected_tasks_per_dag.items():
        dag = dagbag.dags[dag_id]
        assert len(dag.tasks) == expected_count, (
            f"{dag_id}: expected {expected_count} tasks, "
            f"found {len(dag.tasks)}: {dag.task_ids}"
        )


def test_products_dag_loads_with_quality_gates(dagbag):
    # Detect parsing/import failures, such as invalid Python or missing providers.
    # Include the error dictionary in pytest's failure output for diagnosis.
    assert not dagbag.import_errors, dagbag.import_errors

    # Confirm Airflow discovered the expected DAG ID in our DAG files.
    dag = dagbag.dags.get("products_elt")
    assert dag is not None

    # Both database layers must have a quality-check task in the DAG.
    assert "check_staging_quality" in dag.task_ids
    assert "check_core_quality" in dag.task_ids

    # upstream_task_ids lists a task's direct prerequisites:
    # staging loads before its scan, and transformation waits for that scan.
    assert dag.get_task("check_staging_quality").upstream_task_ids == {"update_staging"}
    # >= allows transform to have other prerequisites, such as extract.
    assert dag.get_task("transform").upstream_task_ids >= {"check_staging_quality"}

    # Core scans only after the core load has finished.
    assert dag.get_task("check_core_quality").upstream_task_ids == {"update_core"}
    # This validates the graph, not task execution or the contents of PostgreSQL.


def test_postgres_connection_uses_warehouse_hook(mock_postgres_hook):
    # Call our real helper; the fixture replaces only the external Airflow hook.
    connection = get_db_connection()

    # Verify the connection ID matches the one configured by Docker Compose.
    mock_postgres_hook.assert_called_once_with(postgres_conn_id="postgres_db_yt_elt")
    # Verify the helper opens and returns the hook's connection, without a real DB.
    mock_postgres_hook.return_value.get_conn.assert_called_once_with()
    assert connection is mock_postgres_hook.return_value.get_conn.return_value
