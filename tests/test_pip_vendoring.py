import json

import pytest

from scripts.security.verify_pip_vendoring import verify_root


def prepare_vendor(root, **versions):
    vendor = root / "pip/_vendor"
    (vendor / "pkg_resources").mkdir(parents=True)
    (vendor / "pkg_resources/__init__.py").touch()
    components = {"setuptools": "70.3.0", "msgpack": "1.2.4", "urllib3": "2.8.0"}
    components.update(versions)
    (vendor / "bom.cdx.json").write_text(
        json.dumps(
            {
                "components": [
                    {"name": name, "version": version}
                    for name, version in components.items()
                ]
            }
        ),
        encoding="utf-8",
    )
    return vendor


def test_reviewed_subset_has_no_vulnerable_module(tmp_path):
    prepare_vendor(tmp_path)
    assert verify_root(tmp_path)["package_index_present"] is False


def test_real_vulnerable_setuptools_is_rejected(tmp_path):
    prepare_vendor(tmp_path)
    metadata = tmp_path / "setuptools-70.3.0.dist-info/METADATA"
    metadata.parent.mkdir()
    metadata.write_text("Version: 70.3.0\n", encoding="utf-8")
    with pytest.raises(ValueError, match="full setuptools"):
        verify_root(tmp_path)


def test_vulnerable_module_in_vendor_is_rejected(tmp_path):
    vendor = prepare_vendor(tmp_path)
    (vendor / "package_index.py").touch()
    with pytest.raises(ValueError, match="vulnerable setuptools code"):
        verify_root(tmp_path)


@pytest.mark.parametrize(
    "package,version", [("msgpack", "1.1.2"), ("urllib3", "2.7.0")]
)
def test_unpatched_bundled_dependencies_are_rejected(tmp_path, package, version):
    prepare_vendor(tmp_path, **{package: version})
    with pytest.raises(ValueError, match="Unpatched pip-vendored"):
        verify_root(tmp_path)
