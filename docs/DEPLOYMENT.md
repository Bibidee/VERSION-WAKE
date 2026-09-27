# Versionwake deployment and release record

## Current deployment

Versionwake v0.1.0 is deployed on GenLayer Studionet.

| Evidence | Value |
| --- | --- |
| Frozen source commit | `d91ceba7f56c52722fa2769291700b3a5e444b12` |
| Contract source SHA-256 | `814ad05373d84d0d25575471ad063b441d1fdc09007509c1623c6c12361179ed` |
| Network | GenLayer Studionet (chain ID `61999`) |
| Contract address | [`0xC85F766E74c77638E70859a417d01b799726Eb7E`](https://explorer-studio.genlayer.com/address/0xC85F766E74c77638E70859a417d01b799726Eb7E) |
| Deployment transaction | [`0x79eec415ef9e96903b211bab2fc35d672bd2d0a4d099c22f2a87ba4c82203bf5`](https://explorer-studio.genlayer.com/tx/0x79eec415ef9e96903b211bab2fc35d672bd2d0a4d099c22f2a87ba4c82203bf5) |
| Finality / consensus | `FINALIZED` / `MAJORITY_AGREE` |
| GenVM execution | `SUCCESS` |
| Deployed-source parity | Verified byte-for-byte through GenLayerJS `getContractCode()` / `gen_getContractCode` |
| Source bytes | 17,399 local; 17,399 retrieved |
| `get_info()` | `Versionwake`, `0.1.0`, max notices `512`, max artifact bytes `16000`, minimum confidence `75` |
| GitHub release gate | [Run 36320944416 — PASS](https://github.com/Bibidee/VERSION-WAKE/actions/runs/36320944416) |

The source was not edited between its final release-gate commit/hash and deployment. Deployment evidence does **not** claim a live notice proposal or semantic-review lifecycle; those transactions have not been run.

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

## Deployment and future live-evidence checklist

For a future live notice demonstration, record the exact notice ID, proposer, artifact URLs and raw-byte hashes, proposal/review transactions, consensus results, and canonical stored outcome. Keep any future deployments clearly separate from this current release.

No wallet or deployment credentials belong in this repository. A finalized deployment or semantic result must never be inferred from an EVM submission receipt alone; verify the Intelligent Contract transaction's GenLayer lifecycle/finality.
