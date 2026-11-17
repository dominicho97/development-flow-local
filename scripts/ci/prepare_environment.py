"""Generate disposable CI configuration without reading a developer's .env."""

import base64
import os
import secrets
from pathlib import Path


def main():
    path = Path(".env.ci")
    values = {
        "DOCKERHUB_NAMESPACE": "ci",
        "DOCKERHUB_REPOSITORY": "products-elt",
        "IMAGE_TAG": os.environ.get("GITHUB_SHA", "test"),
        "AIRFLOW_UID": "50000",
        "AIRFLOW_JWT_SECRET": secrets.token_hex(32),
        "FERNET_KEY": base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),
        "AIRFLOW_WWW_USER_USERNAME": "ci_admin",
        "AIRFLOW_WWW_USER_PASSWORD": secrets.token_hex(16),
        "POSTGRES_CONN_HOST": "postgres",
        "POSTGRES_CONN_PORT": "5432",
        "POSTGRES_CONN_USERNAME": "postgres",
        "POSTGRES_CONN_PASSWORD": secrets.token_hex(16),
    }
    for prefix, name in (
        ("METADATA_DATABASE", "airflow_metadata"),
        ("CELERY_BACKEND", "airflow_celery"),
        ("ELT_DATABASE", "products_warehouse"),
    ):
        values[f"{prefix}_NAME"] = name
        values[f"{prefix}_USERNAME"] = name
        values[f"{prefix}_PASSWORD"] = secrets.token_hex(16)

    # Never replace even an existing CI env file silently.
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write("".join(f"{key}={value}\n" for key, value in values.items()))
    path.chmod(0o600)
    for folder in ("config", "logs", "plugins", "dataset/processed", ".ci/reports"):
        Path(folder).mkdir(parents=True, exist_ok=True)
        Path(folder).chmod(0o777)


if __name__ == "__main__":
    main()
