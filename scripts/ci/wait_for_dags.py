"""Wait for both DAGs to be registered, then unpause them for the CI run."""

import subprocess
import time


def main():
    for dag_id in ("products_elt", "products_pipeline"):
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            result = subprocess.run(
                [
                    "docker",
                    "compose",
                    "exec",
                    "-T",
                    "airflow-scheduler",
                    "airflow",
                    "dags",
                    "unpause",
                    dag_id,
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if result.returncode == 0:
                print(f"Ready: {dag_id}", flush=True)
                break
            time.sleep(5)
        else:
            raise RuntimeError(
                f"DAG {dag_id} was not ready: {result.stdout}{result.stderr}"
            )


if __name__ == "__main__":
    main()
