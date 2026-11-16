"""Test scan routing and failure propagation without PostgreSQL or Airflow."""

import subprocess
from unittest.mock import Mock

import pytest

from dags.dataquality import soda


@pytest.mark.parametrize("layer", ["staging", "core"])
def test_layer_scan_and_failure(monkeypatch, tmp_path, layer):
    monkeypatch.setattr(soda, "SODA_PATH", tmp_path)
    datasource, filename = soda.LAYER_CHECKS[layer]
    (tmp_path / "configuration.yml").touch()
    (tmp_path / filename).touch()
    run = Mock()
    monkeypatch.setattr(soda.subprocess, "run", run)
    soda.products_elt_data_quality(layer)
    command = run.call_args.args[0]
    assert command[command.index("-d") + 1] == datasource
    assert command[-1] == str(tmp_path / filename)
    assert run.call_args.kwargs == {"check": True}
    run.side_effect = subprocess.CalledProcessError(2, command)
    with pytest.raises(subprocess.CalledProcessError):
        soda.products_elt_data_quality(layer)


def test_invalid_layer():
    with pytest.raises(ValueError, match="staging or core"):
        soda.products_elt_data_quality("public")


def test_missing_configuration(monkeypatch, tmp_path):
    monkeypatch.setattr(soda, "SODA_PATH", tmp_path)
    with pytest.raises(FileNotFoundError, match="configuration.yml"):
        soda.products_elt_data_quality("staging")
