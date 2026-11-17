# Repository security review — 2026-11-17

## Result and scope

No exposed secrets were detected in the reviewed tracked working files or
available Git history. This is reasonable evidence for repository hygiene,
not a guarantee that the project or a deployed stack is secure.

The review covered the local CI feature branch, all locally available Git
refs, source/configuration, CI permissions, Docker context, and local port
bindings. The clone is not shallow. It did not verify GitHub account settings,
collaborator access, branch/tag rules, historical remote artifacts, forks,
package visibility, or an actual production deployment.

## Checks performed

- Checksum-verified Gitleaks 8.30.1 scanned Git history with
  `--all --full-history --redact=100` and found no leaks.
- A second Gitleaks scan of the tracked working files, including uncommitted
  documentation updates, found no leaks. Ignored local credentials were not
  treated as publicly tracked files.
- A local comparison of six current secret values of at least 12 characters
  from `.env` against 194 Git blobs found no matches. Neither values nor
  credential-bearing lines were printed. Short/common passwords are not
  covered by this exact-value comparison.
- No tracked `.env`, AWS credential directory, or private-key path was found
  in the reviewed history. Docker context excludes local credentials and caches.
- CI uses read-only repository permissions for validation, with registry/OIDC
  permissions scoped to the release job. No `pull_request_target` trigger was
  found. Release tags must reference commits on main's history.
- The product dataset identifies itself as synthetic practice data.

These results describe local refs as scanned, not unreachable/deleted GitHub
commits or previously distributed copies.

## Improvements made during review

- Ignore `.env.*`, `.aws/`, and `.ssh/`, while allowing a sanitized `.env.example`.
- Bind local Airflow and PostgreSQL ports to `127.0.0.1`; recreate existing
  containers to apply the bindings. Internal Compose networking is unchanged.
- Add a digest-pinned, redacted Gitleaks history scan to CI. The scan runs
  before credentials are generated and blocks the validation job on findings.
- Fetch full history for the scan and disable checkout credential persistence.
- Pin the actionlint container by digest and mount its repository read-only.

The CI secret scan uses a read-only source mount and a separate report mount.
Its JSON report is redacted and uploaded beside the unit-test report. No
Gitleaks ignore baseline was added.

Workflow syntax checks passed locally. The new Docker-based secret scan and
changed Compose port bindings still need validation in CI/local Docker.

## Remaining decisions

1. **PostgreSQL 13 is unsupported.** It reached end-of-life on 2025-11-13.
   Plan a supported-major upgrade with backup and migration of the persistent
   volume; do not simply change the tag over an existing data directory.
   The existing Trivy gate scans the application image, not the PostgreSQL
   and Redis service images. [PostgreSQL version policy](https://www.postgresql.org/support/versioning/).
2. **Private-repository attestations depend on the GitHub plan.** GitHub Free,
   Pro, and Team support artifact attestations only for public repositories;
   private/internal attestations require Enterprise Cloud. The current release
   step may therefore fail after a visibility change on a personal plan.
   Choose a supported provenance strategy before publishing a private-repo
   release; no step was silently disabled by this review.
   [GitHub attestation availability](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations).
3. **Check remote access controls separately.** Review collaborators, workflow
   permissions, branch/tag protection, Actions artifacts, and GHCR package
   visibility in GitHub settings. Those settings were not accessible here.
4. **Public history cannot be recalled.** Making a repository private does not
   invalidate downloaded copies or leaked credentials. If a secret is found
   later, rotate/revoke it first, then assess history cleanup.
   [GitHub sensitive-data guidance](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository).

Deployment remains outside the project scope. The local Compose stack is not
a production security configuration; localhost bindings do not replace a
deployment's network policy, authentication, TLS, patching, and recovery plan.
