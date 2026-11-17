"""Opt-in scheduler/worker test, launched from the host with Docker available."""

import json
import shutil
import subprocess
import time
from pathlib import Path
from uuid import uuid4

import pytest

pytestmark = pytest.mark.e2e
PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_TASKS = {
    "extract",
    "update_staging",
    "check_staging_quality",
    "transform",
    "load",
    "update_core",
    "check_core_quality",
}


def airflow(*arguments):
    result = subprocess.run(
        ["docker", "compose", "exec", "-T", "airflow-scheduler", "airflow", *arguments],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


def json_rows(output, required_key):
    """Find CLI JSON after any Airflow startup log lines."""
    decoder = json.JSONDecoder()
    for index, character in enumerate(output):
        if character != "[":
            continue
        try:
            rows, _ = decoder.raw_decode(output[index:])
        except ValueError:
            continue
        if (
            isinstance(rows, list)
            and rows
            and all(isinstance(row, dict) and required_key in row for row in rows)
        ):
            return rows
    pytest.fail(f"No expected JSON rows in Airflow output: {output}")


def test_products_elt_end_to_end():
    """Trigger a unique run and require every task and output file to succeed."""
    assert shutil.which("docker"), "Docker CLI must be available on the host PATH"
    dags = json_rows(airflow("dags", "list", "-o", "json"), "dag_id")
    for dag_id in ("products_pipeline", "products_elt"):
        dag = next((row for row in dags if row["dag_id"] == dag_id), None)
        assert dag is not None, f"{dag_id} is not loaded; inspect DAG import errors"
        assert str(dag.get("is_paused")).lower() == "false", (
            f"Unpause {dag_id} in the UI before running this test"
        )

    run_id = f"e2e__{uuid4().hex}"
    print(f"Testing products_pipeline and products_elt run {run_id}", flush=True)
    airflow("dags", "trigger", "products_pipeline", "-r", run_id)
    deadline = time.monotonic() + 600
    while time.monotonic() < deadline:
        output = airflow("dags", "state", "products_pipeline", run_id)
        states = [line.strip() for line in output.splitlines()]
        if "success" in states or "failed" in states:
            parent_rows = json_rows(
                airflow(
                    "tasks",
                    "states-for-dag-run",
                    "products_pipeline",
                    run_id,
                    "-o",
                    "json",
                ),
                "task_id",
            )
            assert "success" in states, (
                f"Parent run {run_id} failed: {parent_rows}; inspect child products_elt"
            )
            assert {row["task_id"]: row["state"] for row in parent_rows} == {
                "trigger_products_elt": "success"
            }
            rows = json_rows(
                airflow(
                    "tasks", "states-for-dag-run", "products_elt", run_id, "-o", "json"
                ),
                "task_id",
            )
            task_states = {row["task_id"]: row["state"] for row in rows}
            assert "success" in states, f"Run {run_id} failed: {task_states}"
            assert set(task_states) == EXPECTED_TASKS, task_states
            assert all(state == "success" for state in task_states.values()), (
                task_states
            )
            break
        time.sleep(5)
    else:
        pytest.fail(
            f"Run {run_id} did not finish within 600 seconds; inspect Airflow UI"
        )

    # The DAG's load task checks these too; verify the mounted host artifacts.
    for filename in ("products_clean.csv", "products_duplicates.csv"):
        assert (PROJECT_ROOT / "dataset" / "processed" / filename).is_file()
