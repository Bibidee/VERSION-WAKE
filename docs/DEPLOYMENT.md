# Versionwake deployment and release record

## Current status

Versionwake v0.1.0 is a local release candidate. It has **not** been deployed. No address, deployment transaction, live verdict, or Explorer source-parity claim is recorded.

## Required pre-deployment gate

Use Python 3.12+, install the exact versions in `requirements.txt`, fetch the pinned GenVM validation artifact, and run from this project directory:

```powershell
python -m pip install -r requirements.txt
genvm-lint download --version v0.2.12
python scripts/preflight.py
python -m pytest tests/direct -q
genvm-lint check contracts/versionwake.py --json
genvm-lint schema contracts/versionwake.py --output artifacts/versionwake.abi.json
```

All commands must exit successfully; Direct Mode tests must execute rather than skip due to missing GenLayer tooling. The deployable `contracts/` directory must contain exactly one Python source. If any check fails, do not deploy. Correct the cause, rerun the complete gate, and verify CI on that exact commit.

## Freeze and deployment evidence checklist

Before deployment, record the commit and SHA-256 of `contracts/versionwake.py`, confirm the release gate and GitHub Actions are green, and make no source edits between hashing and deployment. After deployment, record the network, address, transaction hash, finality and execution result, `get_info()`, and raw retrieved source SHA-256. Claim byte parity only after comparing retrieved bytes against the frozen local source byte-for-byte. Live semantic evidence must identify the exact notice ID, proposer, artifact URLs and raw-byte hashes, proposal/review transactions, consensus results, and canonical stored outcome. Keep historical addresses separate from the current release.

No wallet or deployment credentials belong in this repository. A finalized deployment or semantic result must never be inferred from an EVM submission receipt alone; verify the Intelligent Contract transaction's GenLayer lifecycle/finality.
