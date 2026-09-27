# Versionwake + VersionGuard deployment and release record

## Historical / superseded deployment — Versionwake v0.1.1

This is the last deployed Versionwake source before the v0.2.x releases. It is preserved as historical evidence and is not a deployment of the current Versionwake source.

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

## Historical semantic disagreement — Versionwake v0.2.0 (superseded)

The live review [`0x6e51b265c2bbe2ff6d9d118268405380d84bac34a1a7da9a01f8eae92d461fcd`](https://explorer-studio.genlayer.com/tx/0x6e51b265c2bbe2ff6d9d118268405380d84bac34a1a7da9a01f8eae92d461fcd) on [`0x1Bd5cA5da9a6142adAFFAA937f93639cbdF637a9`](https://explorer-studio.genlayer.com/address/0x1Bd5cA5da9a6142adAFFAA937f93639cbdF637a9) reached `MAJORITY_DISAGREE` after six rounds; the notice stayed `pending`. The stored consensus history contains distinct, successful model observations classifying the same hash-verified matching notice as both `deprecation` and `sunset`. Versionwake v0.2.0 compared these exact subtypes and therefore rejected otherwise consequence-equivalent observations. No authorization occurred. The current v0.2.1 deployment uses `consensus_class=lifecycle_material` for exact-target deprecation/sunset results; breaking and non-material classes remain distinct, and threshold/applicability disagreement still fails equivalence.

## Historical / superseded v0.1.0 deployment

The first deployment [`0xC85F766E74c77638E70859a417d01b799726Eb7E`](https://explorer-studio.genlayer.com/address/0xC85F766E74c77638E70859a417d01b799726Eb7E), deployment transaction [`0x79eec415ef9e96903b211bab2fc35d672bd2d0a4d099c22f2a87ba4c82203bf5`](https://explorer-studio.genlayer.com/tx/0x79eec415ef9e96903b211bab2fc35d672bd2d0a4d099c22f2a87ba4c82203bf5), is historical. Its review transaction [`0xe2efe0ed00090b6dfb1018a8eb10be05c0b87ef9344764a533a720992d0b6742`](https://explorer-studio.genlayer.com/tx/0xe2efe0ed00090b6dfb1018a8eb10be05c0b87ef9344764a533a720992d0b6742) finalized but GenVM failed while encoding the four-positional-field `NoticeReviewed` event (`SystemError: 2: inval`), leaving the notice pending. v0.1.1 emits only three positional fields and moves `change_kind` into the event blob; the new live review finalized successfully.

## Current deployment — Versionwake v0.2.1

| Evidence | Value |
| --- | --- |
| Frozen source commit | `3aa478ee20b7012e8e90ad4b41c64286ce9a69de` |
| Contract source SHA-256 | `c69ba1499750b4fd0e8db6c3395b1ab4394c57110b5414773dc9b1c3fcfc2663` |
| Network | GenLayer Studionet (chain ID `61999`) |
| Contract address | [`0x92E564996598E92a4DA7f6520798D6b9Df90db28`](https://explorer-studio.genlayer.com/address/0x92E564996598E92a4DA7f6520798D6b9Df90db28) |
| Deployment transaction | [`0xa34dd227f4c4534d39d04ebe6680fc5173c8bb0df5d8ee313c04101b2bd4bfa8`](https://explorer-studio.genlayer.com/tx/0xa34dd227f4c4534d39d04ebe6680fc5173c8bb0df5d8ee313c04101b2bd4bfa8) |
| Finality / consensus / leader execution | `FINALIZED` / `MAJORITY_AGREE` / `SUCCESS` |
| Source parity | Verified byte-for-byte using `gen_getContractCode`; local and deployed are both 18,915 bytes and SHA-256 identical |
| `get_info()` | Name `Versionwake`; version `0.2.1`; min confidence `75`; consensus classes `none`, `non_breaking`, `breaking`, `lifecycle_material`, `unclear` |
| Exact-source GitHub CI | [Run 36343777104 — PASS](https://github.com/Bibidee/VERSION-WAKE/actions/runs/36343777104) |

### Live deprecation/sunset regression

The regression reuses the historical commit-pinned [baseline](https://raw.githubusercontent.com/Bibidee/VERSION-WAKE/6c941f5e8b140acce424fc63f5f1afb26cfe694b/evidence/live/baseline.txt) that produced the v0.2.0 six-round `MAJORITY_DISAGREE` (SHA-256 `5cc129eaa1c8adbebf275ea957989e5f9baed1d5edc6b2c74e5fceb6130d5524`) and [notice](https://raw.githubusercontent.com/Bibidee/VERSION-WAKE/6c941f5e8b140acce424fc63f5f1afb26cfe694b/evidence/live/notice.txt) (SHA-256 `6249db9322cef1faf3bef8426da5c55233bfc9c5dad0cf302df2e441542b4af9`). Both raw artifacts were fetched independently before submission and matched these hashes.

- Notice `VWK-021-LIVE-1790537109437`; proposer `0x2cd419603eBa593074653930Ddc4073d4FD8fc60`; subject/version `example/widget-sdk` / `1.0`.
- Proposal [`0x1f32345ff77aff26bcd0569cb8dba4b93cd7412b2623c1b564a7c835dc996629`](https://explorer-studio.genlayer.com/tx/0x1f32345ff77aff26bcd0569cb8dba4b93cd7412b2623c1b564a7c835dc996629): `FINALIZED`, `MAJORITY_AGREE`, leader GenVM `SUCCESS`; read confirmed `pending` and all stored fields/hashes.
- Review [`0xc302e537346bb24d7968be7380bd0e10e79c661e02752c5ad604d47f3d989cd7`](https://explorer-studio.genlayer.com/tx/0xc302e537346bb24d7968be7380bd0e10e79c661e02752c5ad604d47f3d989cd7): `FINALIZED`, `MAJORITY_AGREE` in one round; leader GenVM `SUCCESS`.
- Canonical state: `confirmed`, `target_match=yes`, `consensus_class=lifecycle_material`, leader diagnostic subtype `sunset`, confidence `97`; reviewed state includes the rationale explaining the supported baseline versus the notice's scheduled removal. The public receipt records validator votes and the consensus result but does not establish that each validator selected the same diagnostic subtype.

### VersionGuard integration on the current registry

The existing separately deployed VersionGuard v0.1.0 at [`0xac581d2B38b8931119aeC9d1D3F2AFbB824101e2`](https://explorer-studio.genlayer.com/address/0xac581d2B38b8931119aeC9d1D3F2AFbB824101e2) has a new policy, `vwk021-1790537404899`, explicitly pinned to the v0.2.1 address, subject `example/widget-sdk`, version `1.0`, and the notice proposer as trusted proposer. Registration [`0xc1798ff2e0e7ea9ece953db9efc1b4e8ab080c16b9e600a84ee59feeb5b065a1`](https://explorer-studio.genlayer.com/tx/0xc1798ff2e0e7ea9ece953db9efc1b4e8ab080c16b9e600a84ee59feeb5b065a1) and application [`0x1be0e4da25d0f9d4fe12d481b24b0bc2e2199a60c1a9c5cf71084a88ba3f8a37`](https://explorer-studio.genlayer.com/tx/0x1be0e4da25d0f9d4fe12d481b24b0bc2e2199a60c1a9c5cf71084a88ba3f8a37) both finalized `MAJORITY_AGREE`; the leader GenVM execution succeeded. `get_policy()` then returned `review_required` with the matching notice ID and diagnostic subtype `sunset`.

A live fail-closed scope check registered a separate policy with subject `example/other-sdk` but the same current registry and trusted proposer. Its apply transaction [`0xe2495423caa8bece7e5c90098ecb050971ef7e33c2e66889ecf0a1a64551c6a1`](https://explorer-studio.genlayer.com/tx/0xe2495423caa8bece7e5c90098ecb050971ef7e33c2e66889ecf0a1a64551c6a1) finalized `MAJORITY_AGREE` with leader execution `ERROR`; the policy remained `active` with no notice recorded. Direct Mode integration tests additionally verify wrong trusted proposer, wrong subject/version, and non-confirmed/cancelled notices cannot transition policy state.

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
