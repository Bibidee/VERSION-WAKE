"""Run the full local release gate for the sole Versionwake contract."""

import ast
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PINNED_GENVM_RELEASE = "v0.2.12"
os.environ.setdefault("GENVM_VERSION", PINNED_GENVM_RELEASE)
CONTRACT_DIR = ROOT / "contracts"
CONTRACTS = sorted(CONTRACT_DIR.glob("*.py"))
CONTRACT = CONTRACT_DIR / "versionwake.py"


def run(command: list[str]) -> None:
    print("+", " ".join(command), flush=True)
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


if len(CONTRACTS) != 1 or CONTRACTS[0] != CONTRACT:
    raise SystemExit("Release gate requires exactly one deployable source: contracts/versionwake.py")

source = CONTRACT.read_text(encoding="utf-8")
ast.parse(source, filename=str(CONTRACT))
required_invariants = (
    '"Depends": "py-genlayer:',
    "class Versionwake(gl.Contract):",
    "class ChangeNotice:",
    "def canonical_sha256(value:",
    "def fetch_verified(source_url:",
    "gl.nondet.web.get(source_url)",
    'gl.nondet.exec_prompt(prompt, response_format="json")',
    "gl.vm.run_nondet_unsafe(leader, validator)",
    "MIN_CONFIDENCE = 75",
    "MAX_NOTICES = 512",
)
missing = [token for token in required_invariants if token not in source]
if missing:
    raise SystemExit(f"Required contract invariants are missing: {missing}")
if "import pytest" in source or "from pytest" in source:
    raise SystemExit("Test dependencies must not appear in deployable contract source")

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
schema_path = artifacts / "versionwake.abi.json"
run([sys.executable, "-m", "compileall", "-q", str(CONTRACT_DIR)])
run([sys.executable, "-m", "pytest", "tests/direct", "-q"])
run([lint, "check", str(CONTRACT), "--json"])
run([lint, "schema", str(CONTRACT), "--output", str(schema_path)])
try:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as exc:
    raise SystemExit(f"ABI/schema output is missing or invalid JSON: {exc}") from exc
if not isinstance(schema, dict) or not schema:
    raise SystemExit("ABI/schema output is empty or has an unexpected shape")

print(f"Versionwake preflight PASS: {len(required_invariants)} invariants, Direct Mode, GenVM lint, ABI/schema (GenVM artifact {PINNED_GENVM_RELEASE})")
