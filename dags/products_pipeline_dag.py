"""Manual entry point that launches and monitors the products ELT DAG."""

from datetime import timedelta

import pendulum
from airflow.providers.standard.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.sdk import dag


@dag(
    dag_id="products_pipeline",
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    tags=["products", "orchestration"],
)
def products_pipeline_dag():
    # Reuse the parent's run ID in the child DAG to make both runs easy to find.
    # Waiting propagates ELT/Soda failures to the orchestration DAG.
    TriggerDagRunOperator(
        task_id="trigger_products_elt",
        trigger_dag_id="products_elt",
        trigger_run_id="{{ run_id }}",
        wait_for_completion=True,
        allowed_states=["success"],
        failed_states=["failed"],
        poke_interval=15,
        reset_dag_run=False,
        retries=0,
        # Compose currently has no triggerer. Wait on a worker instead.
        deferrable=False,
        execution_timeout=timedelta(minutes=15),
    )


products_pipeline_dag()
