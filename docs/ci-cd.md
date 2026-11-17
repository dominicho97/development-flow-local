# Validation and release pipeline

`.github/workflows/ci.yml` validates pull requests to `main`, pushes to `main`,
version tags matching `v*.*.*`, and manual workflow dispatches. It stops before
deployment: no server, database, or hosted Airflow installation is updated.

## Gates

| Job | Checks |
| --- | --- |
| Tests and lint | Python 3.12, `uv sync --locked --dev`, local pytest suite, Ruff lint/format, and actionlint workflow/shell validation. |
| Image, Airflow, database, and E2E | Production Docker build, a test image extending that exact local runtime image, disposable Compose stack, real DagBag integrity/operator checks, PostgreSQL connection test, and parent/child DAG E2E run. |
| Image security (within the Airflow job) | CycloneDX SBOM plus Trivy scan; fixable HIGH and CRITICAL findings fail the job. Unfixed and lower-severity findings do not block this gate. |
| Publish validated release image | Only on successful version-tag pushes: transfer the already built/validated runtime image, publish to GHCR, and generate a provenance attestation. |

Default local pytest still skips tests requiring Airflow, a live database, or
`--run-e2e`. CI runs the DagBag tests inside the Airflow image, explicitly opts
into the real PostgreSQL test there, and launches E2E from the host. A successful
host-only test run is therefore only the first gate.

The E2E test triggers `products_pipeline`, waits for its trigger task, checks
all seven `products_elt` tasks (including both Soda scans), and verifies the
processed CSV files. A failing quality gate blocks publishing.

## Isolated CI environment

`scripts/ci/prepare_environment.py` creates a new `.env.ci` with disposable
database users/passwords, an Airflow JWT secret, a Fernet key, and UI credentials.
It refuses to overwrite an existing file and never reads or changes a local
developer `.env`. The configuration is ignored by Git and Docker build context.

The job sets:

```text
COMPOSE_FILE=docker-compose.yml:docker-compose.ci.yml
COMPOSE_PROJECT_NAME=products-ci
COMPOSE_ENV_FILES=.env.ci
AIRFLOW_ENV_FILE=.env.ci
```

The override selects the test image and worker concurrency of two: one slot can
wait in `TriggerDagRunOperator` while another executes child tasks. The base
Compose environment, database initialization script, DAG mounts, and Soda
configuration are reused. Local Compose continues to use `.env` by default.
Each GitHub-hosted job has a fresh Docker host and database volume. Do not run
this CI setup against your local stack: the base file still uses fixed container
names/ports. Volume deletion is restricted to the disposable runner's stack.

Before starting the stack, CI runs a one-off root container to assign
`dataset/processed` and its existing files to the configured Airflow UID and
group 0, with owner read/write permissions. This is limited to generated
outputs; it does not change ownership of the raw dataset. The worker and tasks
continue to run as the normal Airflow user. A preflight in the running worker
creates a temporary file and opens existing CSVs for append without writing
content, verifying both directory and existing-file access before E2E.

`scripts/ci/wait_for_dags.py` waits for the DAGs to register and unpauses both
before E2E. The job always attempts to collect diagnostics and remove its
containers/volumes, including after test failure.

## Runtime and test images

The Dockerfile's default/final `production` target contains application code,
the sample dataset, DAGs, and Soda configuration. It excludes test-only tools.
The `test` target adds the locked development dependencies, test sources, and
pytest configuration. CI supplies `TEST_RUNTIME_IMAGE` to extend the exact
production image already built, rather than independently resolving a base.

`.dockerignore` excludes credentials, Git history, local environments, generated
outputs, logs, and CI artifacts. The release has DAGs and configuration baked
in; development still uses the existing bind mounts.

## Reports and security policy

See the [2026-11-17 artifact review](vulnerability-review-2026-11-17.md) for the
full remaining package findings, successful application test results, inventory
discrepancies, and the Soda/protobuf compatibility blocker. CI now also records
`runtime-inventory.json` to compare installed versions with scanner metadata.

The Actions run uploads a unit-test JUnit report and a separate validation
artifact containing available DagBag/integration/E2E JUnit reports, Compose
status/logs, a CycloneDX SBOM, and vulnerability JSON. Reports are retained for
seven days. A release image transfer artifact is retained for one day.
Generated `.env.ci` is never uploaded. Treat logs as diagnostic data even though
CI uses disposable credentials.

Trivy is pinned to a version and digest; GitHub Actions are pinned to commit
SHAs. Its vulnerability database is fetched at run time, so a new advisory can
fail an unchanged image. Review the vulnerability report, update the affected
base image or dependency, and rerun validation. No vulnerability exceptions are
configured. Fixable HIGH/CRITICAL findings in the current image may require
dependency upgrades before the first green release. The scan covers the
application runtime image, not every third-party Compose service image.

The first vulnerability gate reported CVE-2026-98466 against the inherited
`linux-libc-dev` package at `6.12.115-2+dhi0`. Debian lists `6.12.117-1` as the
fixed trixie security version. The Dockerfile now refreshes APT metadata,
upgrades that installed package, and requires its version to be at least
`6.12.117-1` using `dpkg --compare-versions`. It removes APT indexes afterward.
If the base image's configured repositories cannot supply the fixed version,
the build fails instead of suppressing the advisory. CI also pulls fresh base
images for the production build; its test extension still uses that exact
locally built runtime image.

The current runtime uses Airflow's slim 3.4.0 Python 3.12 image, with the
Linux-only `airflow` dependency group exported from `uv.lock`. That group
provides the required Celery/FAB/PostgreSQL/standard providers and security
minimums without pulling unused Ray/AI integrations. Local `uv sync` still
installs the main project and dev group, not Airflow. To update image-only
dependencies, use `uv add --group airflow --no-sync <requirement>` and keep
Linux markers on those requirements. Keep `AIRFLOW_VERSION` in the Dockerfile
and the exact Airflow dependency in `pyproject.toml` aligned.

Soda is now 3.5.6 with protobuf 6.33.6, and the OS update includes both zlib
packages as well as linux-libc-dev. `uv pip check` validates both installed
Python environments at build time. See the artifact review for remaining
verification and inherited-metadata questions.

This addresses the reported package finding, not necessarily all entries in
`vulnerabilities.json`. Rebuild and scan in CI to verify the installed version
and identify remaining packages. For a local rebuild after new repository
security updates, use `docker build --pull --no-cache -t dominicho97/products_elt:1.0.2 .`
so an older cached APT layer is not reused. This package update does not patch
the Docker host's kernel. See the [Debian advisory](https://security-tracker.debian.org/tracker/CVE-2026-98466).

## Publishing a release

The default destination is `ghcr.io/<github-owner>/<repository>`. This is
separate from the local Docker Hub tag `dominicho97/products_elt:1.0.2`; the
workflow does not push to Docker Hub or change your local `.env`.

After merging the intended code into `main`, create and push an unused version
tag. For example, choose `v1.0.3` if that is your next release:

```powershell
git switch main
git pull --ff-only
git tag v1.0.3
git push origin v1.0.3
```

The workflow requires a `vMAJOR.MINOR.PATCH` tag whose commit is an ancestor of
`origin/main`. All validation jobs run again for the tagged commit. The release
job downloads the validated runtime image instead of rebuilding it, then pushes:

```text
ghcr.io/<owner>/<repository>:1.0.3
ghcr.io/<owner>/<repository>:sha-<full-commit-sha>
```

It records the registry digest in the Actions summary and attaches a GitHub
provenance attestation. Use the digest to identify the exact image for a future
deployment. No `latest` tag is pushed; do not reuse version tags. Registry tags
are not enforced immutable by this workflow, so protect Git release tags with
repository rules if you need that guarantee.

Publishing uses the job-scoped `GITHUB_TOKEN`, with package-write, attestation,
and OIDC permissions only in the publishing job. No Docker Hub password is
needed. The repository/organization must permit GHCR package publishing and
artifact attestations for its plan/visibility. Existing packages must grant this
repository access. A first GHCR package may be private; set package visibility
deliberately in GitHub if public pulls are intended.

PR/main/manual runs never publish. The workflow does not create GitHub Releases
or deploy. Protect `main` with required checks for the tests/lint and Airflow
jobs in GitHub repository settings; workflow code alone does not enforce merges.

## Verification status

### Stack startup failures versus missing reports

If stack startup fails, DagBag and integration tests never run, so their
`/tmp/dag-tests.xml` and `/tmp/integration-tests.xml` files do not exist.
Missing-file messages during diagnostic collection are secondary; they do not
identify why Airflow failed to start. CI now prints container status plus
PostgreSQL/init/API/scheduler/DAG-processor/worker log tails directly in the
failed startup step. Cleanup reports unavailable XML files without emitting
misleading Docker copy errors. Use the first service exception or healthcheck
failure to diagnose startup. The startup issue reported after the slim-image
change was subsequently traced to the Celery compatibility issue below.

### Celery 5.7 worker startup incompatibility

The worker traceback identified `ImportError: cannot import name 'retry' from
'celery.backends.database'`. The resolved Celery 5.7.0 removed that helper,
while the current Airflow Celery provider imports it. Its declared dependency
range still permits Celery 5.7, so both resolution and `uv pip check` can pass
despite this runtime incompatibility. The final optional-provider wrapper
message about requiring Airflow >=2.8 is secondary and misleading here;
Airflow 3.4.0 is already installed.

The Linux-only Airflow group now requires `celery[redis]>=5.6.0,<5.7.0`, with
the exact compatible version in `uv.lock`. Keep this bound until a provider
release supports the changed backend API. The Dockerfile also imports the
actual Celery executor during the build, so a recurrence fails before stack
startup. This smoke check does not connect to Redis or PostgreSQL; CI still
validates actual worker health and E2E execution afterward.

References: [Celery 5.6 backend helper](https://raw.githubusercontent.com/celery/celery/v5.6.0/celery/backends/database/__init__.py)
and [Celery 5.7 backend](https://raw.githubusercontent.com/celery/celery/v5.7.0/celery/backends/database/__init__.py).

### E2E processed-output permissions fix

The task log identified the parent run's underlying failure: `transform`
raised `PermissionError` while opening
`/opt/airflow/dataset/processed/products_clean.csv`. Git checkout created the
tracked CSV as a runner-owned file with ordinary 0644 permissions, while the
Airflow task ran as UID 50000. Making only the directory writable did not
change permissions on the existing file. The staging load succeeded; the
parent correctly propagated its child's failure.

CI now repairs ownership of the generated output directory and existing files
before startup, then checks real worker write access before triggering a DAG.
This also covers `products_duplicates.csv`. The fix still needs a live CI run
to confirm end-to-end success; tests and quality thresholds were not relaxed.

### E2E parent failure diagnostics

The next CI run passed DAG validation and database connectivity, then failed
in `products_pipeline.trigger_products_elt`. The reported parent state alone
does not identify the cause: the trigger can fail itself or propagate a failed
child run. The underlying task exception is still needed before attributing
this failure to a specific component.

The E2E failure output now includes task states for both DAGs and the last 60
lines of each available task log for that run. It also saves
`.ci/reports/e2e-failure.txt`. CI copies the full worker task-log directory into
the validation report artifact before cleanup; `compose.log` alone may not
contain task exceptions. Missing child runs or diagnostic timeouts no longer
prevent reporting the original E2E failure.

For the reported run, inspect the exception under
`dag_id=products_pipeline/run_id=e2e__28e8190f4c5740d79923b96d2c6a81df/task_id=trigger_products_elt/`.
If it reports that `products_elt` failed, inspect that child run's failed task
instead. These diagnostics preserve strict success requirements; the quality
gates and expected task states are unchanged. The subsequent task exception
identified the output-permissions problem documented above.

The first CI DagBag step exposed an Airflow 3.4 API mismatch in the fixture:
`include_examples` is no longer a constructor argument, and the
`airflow.models.dagbag` import is deprecated. The fixture now uses
`airflow.dag_processing.dagbag.DagBag(dag_folder=...)`, matching the pinned
Airflow 3.4.0 source. Rerun CI with the updated commit to verify DAG loading
and subsequent gates; the earlier failure happened before database/E2E tests.

The workflow and Compose YAML have been parsed locally, and actionlint validated
the workflow (shellcheck is provided by its CI container, not the local Windows
binary). Local verification passed **83 tests, with 5 expected skips**; Ruff
lint and formatting passed. Tests validate disposable environment generation
and core cleaning. The sample CSV yields 51 eligible core rows with no blank names or
negative prices. Docker is unavailable in the current coding session, so image
builds, the new CI stack, vulnerability results, publishing, and attestations
still need their first GitHub Actions execution. No images have been published
by this implementation session.

References: [Docker Compose overrides](https://docs.docker.com/compose/how-tos/multiple-compose-files/merge/),
[Compose startup health waits](https://docs.docker.com/reference/cli/docker/compose/up),
and [GitHub artifact attestations](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations).
