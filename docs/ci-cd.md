# Validation and release pipeline

[GitHub Actions](../.github/workflows/ci.yml) validates pull requests and pushes
to `main`, version-tag pushes, and manual runs. Deployment is outside the
workflow's scope.

## Validation gates

| Stage | What it checks |
| --- | --- |
| Tests and lint | Python 3.12, locked dependencies, pytest, Ruff, actionlint, and a Gitleaks scan of fetched Git history. |
| Runtime and integration | Builds the production image and a test image based on it; starts a disposable Compose stack; checks DAG loading, PostgreSQL connectivity, and the parent/child Airflow run. |
| Image security | Generates a CycloneDX SBOM and scans the runtime image with Trivy. Fixable HIGH and CRITICAL findings fail the gate. |
| Release | After validation succeeds on a version-tag push, publishes the validated runtime image to GHCR and creates a provenance attestation. |

Local pytest skips tests that need Airflow, a live database, or the `--run-e2e`
option. CI runs those checks in or against its disposable stack. The E2E test
triggers `products_pipeline`, checks all seven `products_elt` tasks, including
both Soda scans, and verifies the processed files.

## CI environment and reports

`scripts/ci/prepare_environment.py` creates a fresh `.env.ci` with disposable
credentials and secrets. It refuses to overwrite an existing file and does not
read the developer's `.env`. The workflow uses `docker-compose.yml` with
`docker-compose.ci.yml`, a separate Compose project, and two worker slots so
the waiting parent and its child can run concurrently.

CI prepares permissions on `dataset/processed`, waits for both DAGs to register,
and unpauses them before E2E. It collects diagnostics and attempts to clean up
the disposable stack even on failure. Do not run this CI configuration against
the local stack: the base Compose file uses fixed container names and ports.

The production image contains application code, DAGs, sample data, and Soda
configuration. The test target extends the exact production image built by CI
with test dependencies and sources. The release job uses that validated image
rather than rebuilding it.

Actions uploads test reports and available integration/E2E reports, Compose
diagnostics, SBOM, and scan results for seven days. The release image transfer
artifact is retained for one day. `.env.ci` is not uploaded; treat logs as
diagnostic data. Gitleaks findings are redacted before the report is saved.
See the [security review](security-review.md) for scope and limitations.

## Security policy

Trivy and Gitleaks images are pinned by digest and GitHub Actions by commit SHA.
Trivy fetches its vulnerability database at runtime, so new advisories can
cause a previously passing image to fail. The scan covers the application
runtime image, not all third-party Compose service images. Lower-severity and
unfixed findings do not block the stated gate.

The reviewed `security/pip-setuptools.openvex.json` statement applies to
CVE-2025-47273 in pip's vendored `pkg_resources` subset. Before applying it, CI
runs `scripts/security/verify_pip_vendoring.py` inside the image; unexpected
or missing vendor contents fail verification. Trivy displays suppressed results.
Review both the statement and guard when changing pip or the base image; do not
reuse the statement for images that have not passed the guard.

The Dockerfile synchronizes inherited dpkg status fragments after package
upgrades to prevent stale metadata from misrepresenting installed versions.
The [artifact review](vulnerability-review-2026-11-17.md) records the
investigation and package findings. Review the latest scan and runtime inventory
when updating dependencies or diagnosing scanner discrepancies.

The image uses the Linux-only `airflow` dependency group from `uv.lock`;
ordinary local `uv sync` does not install Airflow. Keep the Dockerfile Airflow
version aligned with the dependency declaration and retain the Celery
compatibility bound until the provider supports a newer version. To change
image-only dependencies, use `uv add --group airflow --no-sync <requirement>`
and preserve the Linux markers.

## Publishing a release

After merging the intended commit into `main`, create and push an unused
version tag, for example:

```powershell
git switch main
git pull --ff-only
git tag v1.0.3
git push origin v1.0.3
```

The tag must use `vMAJOR.MINOR.PATCH` and point to a commit that is an ancestor
of `origin/main`. Validation runs again for that commit. On success, the
workflow publishes the validated image as:

```text
ghcr.io/<owner>/<repository>:1.0.3
ghcr.io/<owner>/<repository>:sha-<full-commit-sha>
```

The Actions summary records the registry digest and the workflow attaches a
provenance attestation. It does not push `latest`, create a GitHub Release,
or deploy. Do not reuse version tags; protect Git tags with repository rules
if immutability is required.

Publishing uses the job-scoped `GITHUB_TOKEN`; the repository or organization
must permit GHCR publishing and attestations, and any existing package must
grant the repository access. Set package visibility deliberately. PR, main,
and manual runs do not publish. Configure required checks on `main` in GitHub
settings; the workflow alone does not enforce merge protection.

## Verification status

The project owner reported a passing CI run on 2026-11-17, including the image
build, Airflow and PostgreSQL checks, E2E execution, and the fixable
HIGH/CRITICAL security gate. This is a dated result, not a guarantee about
later commits or advisories. The gate does not imply zero vulnerabilities.

The recorded local run passed 90 tests with 5 expected skips. Release-tag
publishing and provenance were configured but were not separately confirmed by
that report. Check the relevant Actions run for the current result.

## Troubleshooting

- **Missing test reports after startup failure:** inspect the first service
  exception or health-check failure in the Compose diagnostics; tests that
  never started cannot produce reports.
- **Parent DAG fails:** inspect the child task states and logs in the E2E
  failure report. A failing child or Soda check propagates to the parent.
- **Processed-file permission errors:** CI prepares both the output directory
  and existing CSV files for the Airflow worker and checks write access before
  E2E. Inspect the worker logs if the preflight or transform fails.
- **Celery worker import error:** the Airflow provider previously failed with
  Celery 5.7. Keep the locked compatible version and inspect the actual
  executor import and worker logs when changing the runtime.
- **Security gate failure:** inspect the vulnerability report and
  `runtime-inventory.json`, update affected packages or the base image, and
  rerun CI. Preserve the VEX verification guard and visible suppression output.

For local stack setup and diagnostics, see
[Development: Docker and Airflow](development.md#docker-and-airflow).
