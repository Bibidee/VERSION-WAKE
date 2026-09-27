# Versionwake + VersionGuard deployment and release record

## Historical / superseded deployment — Versionwake v0.1.1

This is the last deployed Versionwake source before the current v0.2.0 / VersionGuard v0.1.0 source changes. It is preserved as historical evidence and is not a deployment of either current source.

| Evidence | Value |
| --- | --- |
| Frozen source commit | `e3d756184e18e75b4f984cc0af3202e5d5c3c827` |
| Contract source SHA-256 | `8c8b7ed5f03db17b83941133e885f95e458e2a29174bbf919e78b5a51d381392` |
| Network | GenLayer Studionet (chain ID `61999`) |
| Contract address | [`0xfaC85C5728F57b53B2973add5A14C24F7A45268d`](https://explorer-studio.genlayer.com/address/0xfaC85C5728F57b53B2973add5A14C24F7A45268d) |
| Deployment transaction | [`0x0c9f55e00dc657da265f636d97ac77eb81dc520f686cb645fc583e4942698c99`](https://explorer-studio.genlayer.com/tx/0x0c9f55e00dc657da265f636d97ac77eb81dc520f686cb645fc583e4942698c99) |
| Finality / consensus | `FINALIZED` / `MAJORITY_AGREE` |
| GenVM execution | `SUCCESS` |
| Deployed-source parity | Verified byte-for-byte through GenLayerJS `getContractCode()` / `gen_getContractCode` |
| Source bytes | 17,452 local; 17,452 retrieved |
| `get_info()` | `Versionwake`, `0.1.1`, max notices `512`, max artifact bytes `16000`, minimum confidence `75` |
| GitHub release gate | [Run 36322467965 — PASS](https://github.com/Bibidee/VERSION-WAKE/actions/runs/36322467965) |

The source was not edited between its final release-gate commit/hash and deployment.

## Historical live lifecycle evidence — v0.1.1

Controlled fixture notice `VWK-LIVE-002` used commit-pinned [baseline](https://raw.githubusercontent.com/Bibidee/VERSION-WAKE/6c941f5e8b140acce424fc63f5f1afb26cfe694b/evidence/live/baseline.txt) (SHA-256 `5cc129eaa1c8adbebf275ea957989e5f9baed1d5edc6b2c74e5fceb6130d5524`) and [notice](https://raw.githubusercontent.com/Bibidee/VERSION-WAKE/6c941f5e8b140acce424fc63f5f1afb26cfe694b/evidence/live/notice.txt) (SHA-256 `6249db9322cef1faf3bef8426da5c55233bfc9c5dad0cf302df2e441542b4af9`). The fixture is demonstrative and not a factual claim about a real third-party SDK.

- Proposal [`0x6dffbb044b25ddbc71de02c8665fa916997486a1db20801a0c6917f1ad637cdf`](https://explorer-studio.genlayer.com/tx/0x6dffbb044b25ddbc71de02c8665fa916997486a1db20801a0c6917f1ad637cdf): `FINALIZED`, `MAJORITY_AGREE`, GenVM `SUCCESS`; canonical read returned `pending` with matching proposer, subject/version, URLs, hashes, and summary.
- Review [`0xf87adedd37e1ab7ac84a32e31aad76555c3d80bf595140c38662d859c5955a1e`](https://explorer-studio.genlayer.com/tx/0xf87adedd37e1ab7ac84a32e31aad76555c3d80bf595140c38662d859c5955a1e): `FINALIZED`, `MAJORITY_AGREE`, GenVM `SUCCESS`.
- Final canonical state: `confirmed`; `target_match=yes`; `change_kind=sunset`; confidence `95`. The exact-scope `is_confirmed_for` view returned `true` when called through GenLayerJS with typed arguments.

## Historical / superseded v0.1.0 deployment

The first deployment [`0xC85F766E74c77638E70859a417d01b799726Eb7E`](https://explorer-studio.genlayer.com/address/0xC85F766E74c77638E70859a417d01b799726Eb7E), deployment transaction [`0x79eec415ef9e96903b211bab2fc35d672bd2d0a4d099c22f2a87ba4c82203bf5`](https://explorer-studio.genlayer.com/tx/0x79eec415ef9e96903b211bab2fc35d672bd2d0a4d099c22f2a87ba4c82203bf5), is historical. Its review transaction [`0xe2efe0ed00090b6dfb1018a8eb10be05c0b87ef9344764a533a720992d0b6742`](https://explorer-studio.genlayer.com/tx/0xe2efe0ed00090b6dfb1018a8eb10be05c0b87ef9344764a533a720992d0b6742) finalized but GenVM failed while encoding the four-positional-field `NoticeReviewed` event (`SystemError: 2: inval`), leaving the notice pending. v0.1.1 emits only three positional fields and moves `change_kind` into the event blob; the new live review finalized successfully.

## Current source deployment status

Versionwake v0.2.0 and VersionGuard v0.1.0 have not yet been verified as deployed. Do not use the historical Versionwake v0.1.1 address or transaction as evidence for either current source. Deploy only to GenLayer Studionet chain ID `61999`, after the final commit passes the release gate. Deploy both exact frozen sources, verify each transaction reaches `FINALIZED` with successful GenVM execution, retrieve deployed source through the supported code retrieval API, and compare exact bytes against the frozen local files. Then run the two-contract lifecycle: register policy, submit notice, read pending state, review to confirmed, apply exact notice through VersionGuard, read both final states, and confirm replay and untrusted-proposer rejection. Simulator results are test evidence, not live-chain evidence.

## Release gate for future source changes

Use Python 3.12+, install the exact versions in `requirements.txt`, fetch the pinned GenVM validation artifact, and run from this project directory:

```powershell
python -m pip install -r requirements.txt
genvm-lint download --version v0.2.12
python scripts/preflight.py
python -m pytest tests/direct -q
genvm-lint check contracts/versionwake.py --json
genvm-lint schema contracts/versionwake.py --output artifacts/versionwake.abi.json
genvm-lint check contracts/version_guard.py --json
genvm-lint schema contracts/version_guard.py --output artifacts/version_guard.abi.json
```

All commands must exit successfully; Direct Mode tests must execute rather than skip due to missing GenLayer tooling. The deployable `contracts/` directory must contain exactly `versionwake.py` and `version_guard.py`. If any check fails, do not deploy. Correct the cause, rerun the complete gate, and verify CI on that exact commit.

## Deployment and future live-evidence checklist

For each future deployment, keep v0.1.1 evidence intact and clearly label it historical. Record both source commits/hashes, contract addresses, deployment and transaction hashes, source-parity results, exact chain ID, policy ID/owner/trusted proposer, live notice ID and proposer, artifact URLs and raw-byte hashes, proposal/review/apply transactions, consensus results, and canonical Versionwake and VersionGuard reads. Never present simulator-only calls as live evidence.

No wallet or deployment credentials belong in this repository. A finalized deployment or semantic result must never be inferred from an EVM submission receipt alone; verify the Intelligent Contract transaction's GenLayer lifecycle/finality.
