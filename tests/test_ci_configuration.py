"""Verify disposable CI configuration never overwrites developer settings."""

import base64

import pytest

from scripts.ci.prepare_environment import main


def test_ci_environment_is_complete_and_preserves_local_env(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_SHA", "test-commit")
    local_env = tmp_path / ".env"
    local_env.write_text("KEEP_LOCAL_SETTINGS=true\n", encoding="utf-8")

    main()

    values = dict(
        line.split("=", 1)
        for line in (tmp_path / ".env.ci").read_text(encoding="utf-8").splitlines()
    )
    assert values["IMAGE_TAG"] == "test-commit"
    assert values["POSTGRES_CONN_HOST"] == "postgres"
    assert len(base64.urlsafe_b64decode(values["FERNET_KEY"])) == 32
    for prefix in ("METADATA_DATABASE", "CELERY_BACKEND", "ELT_DATABASE"):
        assert values[f"{prefix}_NAME"]
        assert values[f"{prefix}_USERNAME"]
        assert len(values[f"{prefix}_PASSWORD"]) == 32
    assert local_env.read_text(encoding="utf-8") == "KEEP_LOCAL_SETTINGS=true\n"
    assert (tmp_path / "dataset/processed").is_dir()
    with pytest.raises(FileExistsError):
        main()
