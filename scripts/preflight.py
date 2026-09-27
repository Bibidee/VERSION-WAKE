"""Run all contract checks, Direct Mode tests, lint, and schemas."""

import ast
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PINNED_GENVM_RELEASE = "v0.2.12"
os.environ["GENVM_VERSION"] = PINNED_GENVM_RELEASE
CONTRACT_DIR = ROOT / "contracts"
CONTRACT_SOURCES = {
    "versionwake.py": {
        '"Depends": "py-genlayer:',
        "class Versionwake(gl.Contract):",
        "class ChangeNotice:",
        "def canonical_sha256(value:",
        "def fetch_verified(source_url:",
        "gl.nondet.web.get(source_url)",
        'gl.nondet.exec_prompt(prompt, response_format="json")',
        "gl.vm.run_nondet_unsafe(leader, validator)",
        "MIN_CONFIDENCE = 75",
        "MAX_NOTICES_PER_PROPOSER = 64",
        "proposer_notice_counts: TreeMap[str, u256]",
        "def get_proposer_notice_count(",
    },
    "version_guard.py": {
        '"Depends": "py-genlayer:',
        "class VersionGuard(gl.Contract):",
        "class DependencyPolicy:",
        "class VersionwakeRegistry:",
        "gl.public.write",
        "def apply_notice(",
        "registry.is_confirmed_for(",
        "MAX_POLICIES_PER_OWNER_LIFETIME = 64",
    },
}


def run(command: list[str]) -> None:
    print("+", " ".join(command), flush=True)
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


actual_names = {path.relative_to(CONTRACT_DIR).as_posix() for path in CONTRACT_DIR.rglob("*.py")}
if actual_names != set(CONTRACT_SOURCES):
    raise SystemExit(
        "Deployable source inventory mismatch; expected exactly "
        f"{sorted(CONTRACT_SOURCES)}, got {sorted(actual_names)}"
    )

for name, invariants in CONTRACT_SOURCES.items():
    contract = CONTRACT_DIR / name
    source = contract.read_text(encoding="utf-8")
    ast.parse(source, filename=str(contract))
    missing = [token for token in invariants if token not in source]
    if missing:
        raise SystemExit(f"Required invariants missing from {name}: {missing}")
    if "import pytest" in source or "from pytest" in source:
        raise SystemExit(f"Test dependencies must not appear in deployable contract source: {name}")

lint = shutil.which("genvm-lint") or shutil.which("genvm-lint.exe")
if lint is None:
    executable = "genvm-lint.exe" if sys.platform == "win32" else "genvm-lint"
    candidates = (Path(sys.executable).parent / executable, Path(sys.executable).parent / "Scripts" / executable)
    for candidate in candidates:
        if candidate.exists():
            lint = str(candidate)
            break
if lint is None:
    raise SystemExit("genvm-lint not found; install pinned requirements; lint is a required release check")

artifacts = ROOT / "artifacts"
artifacts.mkdir(exist_ok=True)
run([sys.executable, "-m", "compileall", "-q", str(CONTRACT_DIR)])
run([sys.executable, "-m", "pytest", "tests/direct", "-q"])
for name in CONTRACT_SOURCES:
    contract = CONTRACT_DIR / name
    schema_path = artifacts / f"{contract.stem}.abi.json"
    run([lint, "check", str(contract), "--json"])
    run([lint, "schema", str(contract), "--output", str(schema_path)])
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"ABI/schema output for {name} is missing or invalid JSON: {exc}") from exc
    if not isinstance(schema, dict) or not schema:
        raise SystemExit(f"ABI/schema output for {name} is empty or has an unexpected shape")

print(
    "Versionwake preflight PASS: exactly two deployable sources, syntax and safety invariants, "
    f"Direct Mode, lint and schema for both contracts (GenVM artifact {PINNED_GENVM_RELEASE})"
)
