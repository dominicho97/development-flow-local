# Agent instructions

## Python and dependency management

- Use `uv` for all Python environment and dependency operations.
- Do not use `pip` directly for project dependencies.
- The supported Python line is 3.12, as defined by `.python-version` and
  `requires-python` in `pyproject.toml`.
- Run project commands with `uv run` so they use the managed environment.
- Add dependencies with `uv add` or `uv add --dev`.
- Keep `uv.lock` synchronized with `uv sync` and commit intentional lockfile
  changes.

## Standard commands

```powershell
uv sync
uv run python --version
uv run <command>
uv add <package>
uv add --dev <package>
uv lock
```

The `.venv` directory is local environment state and must not be committed.
