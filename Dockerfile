ARG AIRFLOW_VERSION=3.4.0
ARG PYTHON_VERSION=3.12
ARG UV_VERSION=0.13.7
ARG TEST_RUNTIME_IMAGE=runtime

FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

FROM apache/airflow:${AIRFLOW_VERSION}-python${PYTHON_VERSION} AS runtime

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

# Refresh the inherited development headers for CVE-2026-98466. Fail the build
# if the configured Debian repositories cannot supply the fixed version.
RUN apt-get update \
    && apt-get install -y --no-install-recommends --only-upgrade linux-libc-dev \
    && dpkg --compare-versions \
        "$(dpkg-query -W -f='${Version}' linux-libc-dev)" ge '6.12.117-1' \
    && rm -rf /var/lib/apt/lists/*

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
COPY --chown=airflow:root dags /opt/airflow/dags
COPY --chown=airflow:root include /opt/airflow/include

# CI extends the runtime with locked test tools; release images exclude them.
FROM ${TEST_RUNTIME_IMAGE} AS test
ENV PYTHONPATH=/opt/airflow:/opt/airflow/project
RUN uv export --frozen --only-group dev --no-emit-project \
        --format requirements.txt --output-file /tmp/test-requirements.txt \
    && uv pip install --no-cache --python "${VIRTUAL_ENV}/bin/python" \
        --requirement /tmp/test-requirements.txt \
    && rm /tmp/test-requirements.txt
COPY --chown=airflow:root tests /opt/airflow/tests
COPY --chown=airflow:root pyproject.toml /opt/airflow/pyproject.toml

# Keep the default docker build output suitable for release.
FROM runtime AS production
