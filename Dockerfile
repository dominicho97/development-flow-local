ARG AIRFLOW_VERSION=3.4.0
ARG PYTHON_VERSION=3.12
ARG UV_VERSION=0.13.7

FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

FROM apache/airflow:${AIRFLOW_VERSION}-python${PYTHON_VERSION}

ARG AIRFLOW_VERSION

ENV AIRFLOW_HOME=/opt/airflow
ENV PYTHONPATH=/opt/airflow/project
ENV SODA_PYTHON=/home/airflow/soda-venv/bin/python

# Copy the official uv binary into the Airflow image.
COPY --from=uv /uv /uvx /usr/local/bin/

WORKDIR /opt/airflow/project

# Copy dependency metadata separately for better Docker layer caching.
COPY pyproject.toml uv.lock ./

USER root

# Export only runtime dependencies from the committed lockfile.
RUN uv export \
        --frozen \
        --no-dev \
        --no-emit-project \
        --prune soda-core-postgres \
        --format requirements.txt \
        --output-file /tmp/project-requirements.txt \
    && uv export \
        --frozen \
        --no-dev \
        --no-emit-project \
        --format requirements.txt \
        --output-file /tmp/soda-requirements.txt \
    && chown airflow:root /tmp/project-requirements.txt /tmp/soda-requirements.txt

USER airflow

# Install into Airflow's existing Python environment.
RUN uv pip install \
        --no-cache \
        --python "${VIRTUAL_ENV}/bin/python" \
        "apache-airflow==${AIRFLOW_VERSION}" \
        --requirement /tmp/project-requirements.txt \
    && rm /tmp/project-requirements.txt

# Soda 3.3.14 requires older OpenTelemetry packages than Airflow 3.4.0.
# Keep its locked dependencies in a separate environment, invoked via subprocess.
USER root
RUN mkdir -p /tmp/.cache/uv && chown -R airflow:root /tmp/.cache/uv
USER airflow
RUN uv venv --python "${VIRTUAL_ENV}/bin/python" /home/airflow/soda-venv \
    && uv pip install \
        --no-cache \
        --python "${SODA_PYTHON}" \
        --requirement /tmp/soda-requirements.txt \
    && rm /tmp/soda-requirements.txt

# Expose the Soda CLI without changing Airflow's Python or dependency environment.
USER root
RUN ln -s /home/airflow/soda-venv/bin/soda /usr/local/bin/soda
USER airflow
RUN soda --version \
    && uv pip show --python "${SODA_PYTHON}" soda-core-postgres

# Make the repository modules available to Airflow tasks.
COPY --chown=airflow:root src ./src
COPY --chown=airflow:root dataset ./dataset
