"""Check failure reporting without launching Docker or Airflow."""

import subprocess

import test_airflow_e2e as e2e


def test_failure_details_includes_child_exception(monkeypatch, tmp_path):
    monkeypatch.setattr(e2e, "PROJECT_ROOT", tmp_path)
    calls = []

    def fake_airflow(*arguments, check=True):
        calls.append((arguments, check))
        return "child state: failed"

    monkeypatch.setattr(e2e, "airflow", fake_airflow)
    log = (
        tmp_path
        / "logs/dag_id=products_elt/run_id=e2e__test/task_id=extract/attempt=1.log"
    )
    log.parent.mkdir(parents=True)
    log.write_text("RuntimeError: underlying task failure\n", encoding="utf-8")

    details = e2e.failure_details("e2e__test")

    assert "products_pipeline task states" in details
    assert "products_elt task states" in details
    assert "RuntimeError: underlying task failure" in details
    assert len(calls) == 2
    assert all(check is False for _, check in calls)
    assert (tmp_path / ".ci/reports/e2e-failure.txt").read_text(
        encoding="utf-8"
    ) == details


def test_failure_details_preserves_reporting_when_cli_fails(monkeypatch, tmp_path):
    monkeypatch.setattr(e2e, "PROJECT_ROOT", tmp_path)

    def timed_out(*arguments, **kwargs):
        raise subprocess.TimeoutExpired("airflow", 45)

    monkeypatch.setattr(e2e, "airflow", timed_out)
    details = e2e.failure_details("e2e__missing")
    assert details.count("Could not retrieve task states") == 2
    assert "No task log files found" in details
