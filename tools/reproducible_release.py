#!/usr/bin/env python3
"""Build from committed sources and an explicitly locked Windows build environment."""
from __future__ import annotations
import argparse
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.release_source_guard import release_source_state, export_committed_sources, reject_runtime_files

LOCK = Path("packaging/build-environment.lock.json")
PINS = Path("packaging/requirements-build.lock.txt")


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()


def environment(iscc):
    packages = {}
    for dist in metadata.distributions():
        name = re.sub(r"[-_.]+", "-", dist.metadata["Name"]).lower()
        version = dist.version
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name) or not re.fullmatch(r"[a-zA-Z0-9.+!_-]+", version):
            raise ValueError("Unpinnable package metadata")
        if name in packages:
            raise ValueError("Duplicate installed distribution: " + name)
        if dist.read_text("direct_url.json"):
            raise ValueError("Direct URL/editable packages require a wheel-based release environment")
        packages[name] = version
    required = {"pillow", "pyinstaller", "keyring", "paramiko", "cryptography", "pip"}
    if not required.issubset(packages):
        raise ValueError("Release environment is missing required packages")
    return {"schema": 1, "python": platform.python_version(),
            "implementation": platform.python_implementation(), "platform": sys.platform,
            "machine": platform.machine(), "python_executable_sha256": sha256(sys.executable),
            "inno_iscc_sha256": sha256(iscc), "packages": dict(sorted(packages.items()))}


def requirements(lock):
    return "".join(name + "==" + version + "\n" for name, version in sorted(lock["packages"].items()))


def check_environment(expected, actual):
    if expected != actual:
        raise ValueError("Build environment differs from committed lock; no build started")


def tree_hashes(directory):
    result = {}
    for path in sorted(Path(directory).rglob("*")):
        if path.is_symlink():
            raise ValueError("Symlink in build output")
        if path.is_file():
            result[path.relative_to(directory).as_posix()] = sha256(path)
    return result


def source_version(root):
    text = (Path(root)/"ugreen_app/nas_manager.py").read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*"([0-9]+\.[0-9]+\.[0-9]+)"', text)
    if not match:
        raise ValueError("Missing source version")
    return match.group(1)


def build(root, iscc, output):
    root, iscc, output = Path(root).resolve(), Path(iscc).resolve(), Path(output).absolute()
    if output.exists():
        raise ValueError("Output directory must not exist; previous builds are preserved")
    version = source_version(root)
    state = release_source_state(root, version)
    with tempfile.TemporaryDirectory(prefix="ugreen-release-source-") as temporary:
        source = Path(temporary)/"source"
        source.mkdir()
        source_manifest = export_committed_sources(root, source, state)
        lock = json.loads((source/LOCK).read_text(encoding="utf-8"))
        observed = environment(iscc)
        check_environment(lock, observed)
        if observed["platform"] != "win32":
            raise ValueError("Windows release build required")
        if (source/PINS).read_text(encoding="utf-8") != requirements(lock):
            raise ValueError("Exact dependency pins differ from environment lock")
        # Exported committed sources have no private developer files or runtime JSON.
        epoch = subprocess.check_output(["git", "-C", str(root), "show", "-s", "--format=%ct", state["source_commit"]]).decode().strip()
        env = dict(os.environ)
        env.update(SOURCE_DATE_EPOCH=epoch, PYTHONHASHSEED="0", PYTHONNOUSERSITE="1")
        env.pop("PYTHONPATH", None)
        subprocess.run([sys.executable, "-m", "pip", "check"], check=True, env=env)
        subprocess.run([sys.executable, "-m", "PyInstaller", str(source/"packaging/UgreenNASAdmin.spec"),
                        "--clean", "--noconfirm", "--distpath", str(source/"dist"),
                        "--workpath", str(source/"build")], cwd=source, env=env, check=True)
        subprocess.run([str(iscc), "/DMyAppVersion="+version, str(source/"installer/UgreenNASAdmin_installer.iss")],
                       cwd=source/"installer", env=env, check=True)
        check_environment(lock, environment(iscc))
        if source_version(source) != version:
            raise ValueError("Source version changed during build")
        for relative, digest in source_manifest["source_sha256"].items():
            if sha256(source/relative) != digest:
                raise ValueError("Committed source changed during build: "+relative)
        portable = source/"dist/UgreenNASAdmin"
        installer = source/"installer/output"/("UgreenNASAdmin_setup_"+version+".exe")
        if not (portable/"UgreenNASAdmin.exe").is_file() or not installer.is_file():
            raise ValueError("Build did not produce expected artifacts")
        reject_runtime_files(portable)
        result = Path(temporary)/"result"
        result.mkdir()
        shutil.copytree(portable, result/"portable")
        (result/"installer").mkdir()
        shutil.copy2(installer, result/"installer"/installer.name)
        manifest = {"schema": 1, "source": source_manifest, "environment": observed,
                    "source_date_epoch": epoch, "artifacts_sha256": tree_hashes(result),
                    "claim": "Recorded build; reproducibility requires an independent matching rebuild"}
        (result/"BUILD_MANIFEST.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
        # Only publish after every build and source verification step succeeded.
        output.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=".ugreen-build-", dir=output.parent))
        try:
            shutil.copytree(result, staging, dirs_exist_ok=True)
            staging.rename(output)
        finally:
            if staging.exists():
                shutil.rmtree(staging)
    return manifest


def verify_record(directory):
    directory = Path(directory)
    record = json.loads((directory/"BUILD_MANIFEST.json").read_text(encoding="utf-8"))
    actual = tree_hashes(directory)
    actual.pop("BUILD_MANIFEST.json", None)
    if actual != record["artifacts_sha256"]:
        raise ValueError("Build artifacts no longer match manifest")
    return record


def compare(first, second):
    a, b = verify_record(first), verify_record(second)
    if (a["source"]["source_commit"] != b["source"]["source_commit"]
            or a["source"]["source_sha256"] != b["source"]["source_sha256"]
            or a["environment"] != b["environment"]):
        raise ValueError("Build inputs differ; not a reproducibility comparison")
    if a["artifacts_sha256"] != b["artifacts_sha256"]:
        raise ValueError("Build outputs are not byte-identical")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    capture = commands.add_parser("lock", help="Capture a dedicated existing build environment; no packages are installed")
    capture.add_argument("--iscc", type=Path, required=True)
    run = commands.add_parser("build")
    run.add_argument("--iscc", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    check = commands.add_parser("compare")
    check.add_argument("first", type=Path)
    check.add_argument("second", type=Path)
    args = parser.parse_args()
    if args.command == "lock":
        lock = environment(args.iscc)
        if (ROOT/LOCK).exists() or (ROOT/PINS).exists():
            raise ValueError("Lock already exists; review/remove it explicitly before recapturing")
        (ROOT/LOCK).write_text(json.dumps(lock, indent=2)+"\n", encoding="utf-8")
        (ROOT/PINS).write_text(requirements(lock), encoding="utf-8")
        print("Review and commit the two lock files before building.")
    elif args.command == "build":
        build(ROOT, args.iscc, args.output)
        print("Verified build written to", args.output)
    else:
        compare(args.first, args.second)
        print("Recorded inputs and all artifact bytes match.")


if __name__ == "__main__":
    main()
