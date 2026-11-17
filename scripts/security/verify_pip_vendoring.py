"""Fail closed unless the reviewed setuptools finding is only pip's subset."""

import json
import sys
import sysconfig
from email.parser import Parser
from pathlib import Path

from packaging.version import Version


def verify_root(root):
    """Reject vulnerable full distributions and unexpected vendored code."""
    for metadata in root.rglob("setuptools-*.dist-info/METADATA"):
        version = Parser().parsestr(metadata.read_text(encoding="utf-8"))["Version"]
        if not version or Version(version) < Version("78.1.1"):
            raise ValueError(f"Vulnerable full setuptools distribution: {metadata}")

    vendor = root / "pip" / "_vendor"
    bom_path = vendor / "bom.cdx.json"
    if not bom_path.is_file():
        return None
    components = json.loads(bom_path.read_text(encoding="utf-8"))["components"]
    versions = {item["name"]: item.get("version") for item in components}
    for name, minimum in (("msgpack", "1.2.3"), ("urllib3", "2.8.0")):
        if name in versions and Version(versions[name]) < Version(minimum):
            raise ValueError(f"Unpatched pip-vendored {name}: {bom_path}")
    if versions.get("setuptools") != "70.3.0":
        raise ValueError(f"Pip's setuptools subset changed; review VEX: {bom_path}")
    if not (vendor / "pkg_resources" / "__init__.py").is_file():
        raise ValueError(f"Expected pip pkg_resources subset not found: {vendor}")
    if (vendor / "setuptools").exists() or list(vendor.rglob("package_index.py")):
        raise ValueError(f"Potentially vulnerable setuptools code is present: {vendor}")
    return {
        "bom": str(bom_path),
        "vendored_versions": versions,
        "package_index_present": False,
    }


def main():
    version = f"{sys.version_info.major}.{sys.version_info.minor}"
    roots = {
        Path(sysconfig.get_paths()["purelib"]),
        Path(f"/usr/lib/python{version}/site-packages"),
        Path("/usr/lib/python3/dist-packages"),
        Path(f"/usr/local/lib/python{version}/site-packages"),
        Path(f"/home/airflow/soda-venv/lib/python{version}/site-packages"),
    }
    evidence = [
        result
        for root in sorted(roots)
        if root.is_dir()
        for result in [verify_root(root)]
        if result is not None
    ]
    if not evidence:
        raise ValueError(
            "No reviewed pip vendoring inventories found; do not apply VEX"
        )
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
