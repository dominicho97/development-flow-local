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


def airflow(*arguments, check=True):
    result = subprocess.run(
        ["docker", "compose", "exec", "-T", "airflow-scheduler", "airflow", *arguments],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )
    if not check:
        return f"exit_code={result.returncode}\n{result.stdout}{result.stderr}"
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


def failure_details(run_id):
    """Report both DAGs and task exceptions without hiding the original failure."""
    sections = [f"Airflow E2E run: {run_id}"]
    for dag_id in ("products_pipeline", "products_elt"):
        try:
            output = airflow(
                "tasks",
                "states-for-dag-run",
                dag_id,
                run_id,
                "-o",
                "json",
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as error:
            output = f"Could not retrieve task states: {error}"
        sections.append(f"{dag_id} task states:\n{output}")

        # Airflow writes actual Python exceptions to task files, not necessarily
        # to `docker compose logs`. Include bounded excerpts in pytest output.
        log_folder = PROJECT_ROOT / "logs" / f"dag_id={dag_id}" / f"run_id={run_id}"
        try:
            log_files = sorted(log_folder.rglob("*.log"))
            if not log_files:
                sections.append(f"No task log files found at {log_folder}")
            for path in log_files:
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
                sections.append(
                    f"{path.relative_to(PROJECT_ROOT)} (last 60 lines):\n"
                    + "\n".join(lines[-60:])
                )
        except OSError as error:
            sections.append(f"Could not read task logs: {error}")

    details = "\n\n".join(sections)
    try:
        report_folder = PROJECT_ROOT / ".ci" / "reports"
        report_folder.mkdir(parents=True, exist_ok=True)
        (report_folder / "e2e-failure.txt").write_text(details, encoding="utf-8")
    except OSError as error:
        details += f"\nCould not save diagnostics: {error}"
    return details


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
            if "success" not in states:
                pytest.fail(failure_details(run_id))
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
            if not all(state == "success" for state in task_states.values()):
                pytest.fail(failure_details(run_id))
            break
        time.sleep(5)
    else:
        pytest.fail(
            f"Run {run_id} did not finish within 600 seconds.\n{failure_details(run_id)}"
        )

    # The DAG's load task checks these too; verify the mounted host artifacts.
    for filename in ("products_clean.csv", "products_duplicates.csv"):
        assert (PROJECT_ROOT / "dataset" / "processed" / filename).is_file()
