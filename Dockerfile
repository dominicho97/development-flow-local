ARG AIRFLOW_VERSION=3.4.0
ARG PYTHON_VERSION=3.12
ARG UV_VERSION=0.13.7

FROM apache/airflow:${AIRFLOW_VERSION}-python${PYTHON_VERSION}

ARG AIRFLOW_VERSION

ENV AIRFLOW_HOME=/opt/airflow
ENV PYTHONPATH=/opt/airflow/project

# Copy the official uv binary into the Airflow image.
COPY --from=ghcr.io/astral-sh/uv:${UV_VERSION} /uv /uvx /usr/local/bin/

WORKDIR /opt/airflow/project

# Copy dependency metadata separately for better Docker layer caching.
COPY pyproject.toml uv.lock ./

USER root

# Export only runtime dependencies from the committed lockfile.
RUN uv export \
        --frozen \
        --no-dev \
        --no-emit-project \
        --format requirements.txt \
        --output-file /tmp/project-requirements.txt \
    && chown airflow:root /tmp/project-requirements.txt

USER airflow

# Install into Airflow's existing Python environment.
RUN uv pip install \
        --no-cache \
        --python "${VIRTUAL_ENV}/bin/python" \
        "apache-airflow==${AIRFLOW_VERSION}" \
        --requirement /tmp/project-requirements.txt \
    && rm /tmp/project-requirements.txt

# Make the repository modules available to Airflow tasks.
COPY --chown=airflow:root src ./src
COPY --chown=airflow:root dataset ./dataset
