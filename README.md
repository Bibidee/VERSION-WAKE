# Versionwake

Versionwake is a standalone GenLayer Intelligent Contract primitive for recording and independently classifying hash-committed upstream change notices against a specific dependency or standard version. It is aimed at release systems and downstream Intelligent Contracts that need an auditable signal when a notice says a pinned API, protocol, or specification version is breaking, deprecated, or scheduled for removal. The repository also includes VersionGuard, an optional but integrated downstream policy contract that consumes Versionwake's exact-scope confirmed result and records a deterministic migration/review consequence.

It is contract-only: there is no frontend, token, escrow, trusted decision service, or claim that a caller's publisher label proves real-world authority. Versionwake remains independently usable; VersionGuard is a separate, opt-in integration for protocols that want a deterministic on-chain reaction.

## Why GenLayer?

A deterministic contract can verify that downloaded bytes match a SHA-256 commitment, but cannot determine whether prose in a new notice actually applies to a named version or describes a deprecation rather than a compatible change. Versionwake uses ordinary deterministic code for IDs, bounds, hashes, state transitions, and output validation. Within `run_nondet_unsafe`, the leader and validators independently fetch the exact committed baseline and notice and make the bounded semantic classification. Only after consensus does deterministic execution store the result.

The reviewers compare exact `target_match`, a bounded canonical consensus class, and the deterministic outcome. `change_kind` remains the leader's exact diagnostic subtype. For an exact target match, `deprecation` and `sunset` map to `lifecycle_material`; they may agree only when both observations derive the same outcome. `breaking`, `non_breaking`, `none`, and `unclear` remain distinct classes. A confidence-threshold crossing, target mismatch, different outcome, or different class still causes disagreement. `get_notice()` exposes both `change_kind` and `consensus_class`, so consumers can distinguish diagnostic subtype from the consensus-backed class. Rationale and exact confidence values themselves are diagnostic, but confidence's threshold consequence remains consensus-critical. Malformed model output is never accepted as analysis; source unavailability is retryable, and integrity failures never authorize a change.

Without GenLayer, an application could still fetch and hash the documents, but would normally rely on one server or one model call to decide applicability and impact. That service could selectively classify notices. Versionwake places the semantic judgment and its explicit equivalence rule in the consensus execution path. This reduces single-operator dependence; it does not prove that an artifact publisher is authentic or that every validator is infallible.

## Architecture and downstream consequence

```text
commit-pinned baseline + notice
              |
              v
Versionwake: each validator fetches and hashes both artifacts, independently classifies
              |
              v
consensus-backed exact-scope result: proposer + notice ID + subject + pinned version
              |
              v
VersionGuard: policy owner selects registry + trusted proposer + dependency scope
              |
              v
active -> review_required | migration_required
```

Versionwake owns artifact integrity, independent observation, semantic classification, equivalence, and the immutable result record. VersionGuard owns the consuming application's trust policy, dependency snapshot, replay marker, and deterministic response. It does not make another model call.

A policy owner explicitly registers a `policy_id`, dependency subject, pinned version, Versionwake contract address, and trusted proposer address. Anyone may call `apply_notice(owner, policy_id, notice_id)`, but the call can transition the policy only if the configured Versionwake contract reports that exact notice as `confirmed` for that exact proposer, subject, and pinned version, the exact-scope view gate returns true, and the material-change confidence threshold is met. A breaking change sets `migration_required`; deprecation or sunset sets `review_required`. A notice can be applied once, and the resulting policy state is terminal. A new dependency pin is represented by a new policy ID; neither contract provides an owner reset or arbitrary history deletion.

Example downstream gate:

```python
# Another Intelligent Contract may gate an upgrade or privileged operation:
policy = version_guard.get_policy(policy_id, policy_owner)
if policy["state"] == "migration_required":
    raise gl.vm.UserError("Dependency migration is required before this operation")
```

The caller must use the policy owner's namespace and follow its own access-control rules. VersionGuard is not an identity system: its configured trusted proposer is an explicit address choice, not proof that an address represents a real publisher.

## Lifecycle

```text
submit_notice -> pending -> confirmed
                         -> no_material_change
                         -> not_applicable
                         -> inconclusive
                         -> cancelled (proposer only, while pending)
```

Each record is immutable except for its one review outcome (or pending cancellation). A transient fetch/LLM failure or a source-integrity failure leaves the record pending and does not store an outcome. The caller can retry review after an external availability problem; finalized records cannot be rewritten or re-reviewed. A new observation requires a new ID.

`confirmed` means the agreed analysis classified a matching, hash-verified notice as `breaking`, `deprecation`, or `sunset` with confidence at least 75. It is a semantic evidence signal, not a legal or cryptographic proof of publisher authority. Consumers should bind the notice ID, proposer, subject, and version they rely on and independently decide their own policy response.

## Public interface

- `submit_notice(notice_id, subject, version_ref, baseline_url, baseline_hash, notice_url, notice_hash, summary)` — permissionless immutable submission. IDs are namespaced by the submitting address.
- `review_notice(notice_id, proposer)` — permissionless semantic review with independent validator observations.
- `cancel_notice(notice_id)` — submitting address may cancel its own pending record only.
- `get_notice(notice_id, proposer)` — read the complete evidence commitment and review record, including diagnostic `change_kind` and canonical `consensus_class`.
- `is_confirmed_for(notice_id, proposer, subject, version_ref)` — exact-scope boolean gate for downstream callers.
- `get_info()` — version and protocol bounds.

Example downstream policy (pseudocode):

```python
if not versionwake.is_confirmed_for(notice_id, notice_submitter, package, pinned_version):
    raise gl.vm.UserError("No confirmed change notice for this exact version")
# Apply the downstream contract's own response; Versionwake does not mutate that contract.
```

## Security and limitations

- SHA-256 is calculated over the exact raw response bytes before UTF-8 decoding. Both baseline and notice must match their committed hashes, be non-empty valid UTF-8, and fit the byte limit.
- URLs require HTTPS and a DNS-style hostname; IP literals, local/internal suffixes, userinfo, explicit ports, fragments, and malformed authorities are rejected. Contract validation cannot prove DNS resolution, prevent DNS rebinding, or guarantee redirect behavior in the execution environment.
- Artifacts and submitter summaries are untrusted prompt data. The prompt says not to follow embedded instructions, but prompt-injection resistance is not absolute; the semantic outcome is additionally subject to independent validator review.
- An unavailable source or LLM does not become `confirmed`; it leaves the record pending/retryable. Hash mismatch and malformed content also cannot authorize a notice.
- Evidence is immutable only by its hash commitment. External hosts can disappear or serve different bytes; replacement bytes fail verification.
- The publisher/authority of the evidence is not authenticated by this contract. Integrators must establish their own trust policy for sources and submitters.
- Versionwake allows at most 64 lifetime submissions per proposer address. Terminal records remain stored and continue to count; cancellation/finalization does not reclaim a slot, preserving history without deletion authority. This isolates one address's quota but is not Sybil resistance: multiple controlled addresses have independent quotas, and the design does not claim a strict global storage ceiling. VersionGuard separately permits 64 lifetime policies per owner address, retaining terminal policies and without a reset/delete path.
- Consensus disagreement, provider variability, or prolonged infrastructure failure can prevent a review from finalizing. No contract can promise zero `UNDETERMINED` outcomes; the safe property is that uncertainty never becomes a confirmed change.
- Versionwake does not fetch continuously. It classifies the exact two artifacts submitted for one record, not the current state of the entire internet.

## Development and release checks

Python 3.12+ is required. Dependencies are pinned in `requirements.txt`. The release gate validates against the pinned `v0.2.12` GenVM artifact, which contains the runner hash published in the current GenLayer first-contract documentation; this avoids silently switching SDK/runtime during a release check.

```powershell
python -m pip install -r requirements.txt
python scripts/preflight.py
python -m pytest tests/direct -q
genvm-lint check contracts/versionwake.py --json
genvm-lint schema contracts/versionwake.py --output artifacts/versionwake.abi.json
genvm-lint check contracts/version_guard.py --json
genvm-lint schema contracts/version_guard.py --output artifacts/version_guard.abi.json
```

The preflight fails if a required tool, test, linter, or schema step is missing or failing. Tests live outside `contracts/`; the only deployable sources are `contracts/versionwake.py` and `contracts/version_guard.py`. A failed release gate means **do not freeze or deploy**; fix the root cause and rerun every gate.

## Historical deployment — Versionwake v0.1.1 (superseded)

This is the last deployed Versionwake source before the v0.2.x releases. Do not treat this as the current release or as a deployment of VersionGuard.

- Contract: [`0xfaC85C5728F57b53B2973add5A14C24F7A45268d`](https://explorer-studio.genlayer.com/address/0xfaC85C5728F57b53B2973add5A14C24F7A45268d)
- Deployment transaction: [`0x0c9f55e00dc657da265f636d97ac77eb81dc520f686cb645fc583e4942698c99`](https://explorer-studio.genlayer.com/tx/0x0c9f55e00dc657da265f636d97ac77eb81dc520f686cb645fc583e4942698c99)
- Contract source SHA-256: `8c8b7ed5f03db17b83941133e885f95e458e2a29174bbf919e78b5a51d381392`
- Source parity: **verified byte-for-byte** using GenLayerJS `getContractCode()` (`gen_getContractCode`); local and retrieved source were both 17,452 bytes and had the same SHA-256.
- `get_info()` returned name `Versionwake`, version `0.1.1`, maximum 512 notices, maximum artifact size 16,000 bytes, and minimum confidence 75.
- Release gate: GitHub Actions run [36322467965](https://github.com/Bibidee/VERSION-WAKE/actions/runs/36322467965) passed; all 61 Direct Mode tests passed, followed by GenVM lint and schema generation.

### Historical live lifecycle evidence — v0.1.1

This controlled fixture demonstrates the full submitted-notice review path. It is intentionally a contract fixture, not a claim about a real third-party SDK.

- Notice ID: `VWK-LIVE-002`; proposer: `0x2cd419603eBa593074653930Ddc4073d4FD8fc60`.
- Subject/version: `example/widget-sdk` / `1.0`.
- Baseline: [commit-pinned raw fixture](https://raw.githubusercontent.com/Bibidee/VERSION-WAKE/6c941f5e8b140acce424fc63f5f1afb26cfe694b/evidence/live/baseline.txt), SHA-256 `5cc129eaa1c8adbebf275ea957989e5f9baed1d5edc6b2c74e5fceb6130d5524`.
- Notice: [commit-pinned raw fixture](https://raw.githubusercontent.com/Bibidee/VERSION-WAKE/6c941f5e8b140acce424fc63f5f1afb26cfe694b/evidence/live/notice.txt), SHA-256 `6249db9322cef1faf3bef8426da5c55233bfc9c5dad0cf302df2e441542b4af9`.
- Proposal: [`0x6dffbb044b25ddbc71de02c8665fa916997486a1db20801a0c6917f1ad637cdf`](https://explorer-studio.genlayer.com/tx/0x6dffbb044b25ddbc71de02c8665fa916997486a1db20801a0c6917f1ad637cdf) — `FINALIZED`, `MAJORITY_AGREE`, GenVM `SUCCESS`; canonical read confirmed `pending` and matching committed fields.
- Review: [`0xf87adedd37e1ab7ac84a32e31aad76555c3d80bf595140c38662d859c5955a1e`](https://explorer-studio.genlayer.com/tx/0xf87adedd37e1ab7ac84a32e31aad76555c3d80bf595140c38662d859c5955a1e) — `FINALIZED`, `MAJORITY_AGREE`, GenVM `SUCCESS`.
- Canonical reviewed state: `confirmed`, `target_match=yes`, `change_kind=sunset`, confidence `95`; rationale: “The notice explicitly names Example Widget SDK version 1.0, matching the subject and pinned version, and states that GET /v1/status is deprecated with a scheduled removal date of 2025-01-01, which is a scheduled removal (sunset) relative to the baseline where the endpoint was supported.”
- The exact-scope `is_confirmed_for` gate returned `true` when queried with typed GenLayerJS arguments.

### Historical semantic disagreement — v0.2.0 (superseded)

The v0.2.0 review [`0x6e51b265c2bbe2ff6d9d118268405380d84bac34a1a7da9a01f8eae92d461fcd`](https://explorer-studio.genlayer.com/tx/0x6e51b265c2bbe2ff6d9d118268405380d84bac34a1a7da9a01f8eae92d461fcd) on [`0x1Bd5cA5da9a6142adAFFAA937f93639cbdF637a9`](https://explorer-studio.genlayer.com/address/0x1Bd5cA5da9a6142adAFFAA937f93639cbdF637a9) finalized `MAJORITY_DISAGREE` after six rounds. Available consensus history shows outputs alternating between `deprecation` and `sunset` for the same hash-pinned notice: validators agreed on target applicability and a material lifecycle consequence, but exact subtype comparison prevented equivalence. The notice remained `pending`; no material result was authorized. v0.2.1 is now deployed at the address and with the source parity recorded below. It maps only exact-target deprecation/sunset analyses to `lifecycle_material`; it retains the leader's subtype for diagnostics and keeps breaking/non-material/unclear classes distinct.

### Historical / superseded v0.1.0 deployment

The earlier v0.1.0 deployment [`0xC85F766E74c77638E70859a417d01b799726Eb7E`](https://explorer-studio.genlayer.com/address/0xC85F766E74c77638E70859a417d01b799726Eb7E), transaction [`0x79eec415ef9e96903b211bab2fc35d672bd2d0a4d099c22f2a87ba4c82203bf5`](https://explorer-studio.genlayer.com/tx/0x79eec415ef9e96903b211bab2fc35d672bd2d0a4d099c22f2a87ba4c82203bf5), is historical and superseded. Its live review [`0xe2efe0ed00090b6dfb1018a8eb10be05c0b87ef9344764a533a720992d0b6742`](https://explorer-studio.genlayer.com/tx/0xe2efe0ed00090b6dfb1018a8eb10be05c0b87ef9344764a533a720992d0b6742) finalized with a GenVM event-encoding error at `NoticeReviewed.emit()` (`SystemError: 2: inval`); its notice remained pending. v0.1.1 bounds the event's positional fields and keeps the diagnostic category in the event blob.

## Current deployment — Versionwake v0.2.1

- Contract: [`0x92E564996598E92a4DA7f6520798D6b9Df90db28`](https://explorer-studio.genlayer.com/address/0x92E564996598E92a4DA7f6520798D6b9Df90db28) on Studionet chain `61999`.
- Deployment: [`0xa34dd227f4c4534d39d04ebe6680fc5173c8bb0df5d8ee313c04101b2bd4bfa8`](https://explorer-studio.genlayer.com/tx/0xa34dd227f4c4534d39d04ebe6680fc5173c8bb0df5d8ee313c04101b2bd4bfa8), `FINALIZED`, `MAJORITY_AGREE`, leader GenVM `SUCCESS`.
- Frozen source commit: `3aa478ee20b7012e8e90ad4b41c64286ce9a69de`; contract SHA-256: `c69ba1499750b4fd0e8db6c3395b1ab4394c57110b5414773dc9b1c3fcfc2663`.
- Source parity: verified byte-for-byte via `gen_getContractCode`; local and deployed source are both 18,915 bytes with the same SHA-256.
- `get_info()`: `Versionwake`, version `0.2.1`, minimum confidence `75`, and consensus classes `none`, `non_breaking`, `breaking`, `lifecycle_material`, `unclear`.
- Exact live regression notice: `VWK-021-LIVE-1790537109437`, proposed by `0x2cd419603eBa593074653930Ddc4073d4FD8fc60` for `example/widget-sdk` version `1.0`; it used the same commit-pinned baseline and lifecycle notice as the historical disagreement above.
- Proposal: [`0x1f32345ff77aff26bcd0569cb8dba4b93cd7412b2623c1b564a7c835dc996629`](https://explorer-studio.genlayer.com/tx/0x1f32345ff77aff26bcd0569cb8dba4b93cd7412b2623c1b564a7c835dc996629), `FINALIZED`, `MAJORITY_AGREE`, GenVM `SUCCESS`; canonical read verified the exact committed fields and `pending` state.
- Review: [`0xc302e537346bb24d7968be7380bd0e10e79c661e02752c5ad604d47f3d989cd7`](https://explorer-studio.genlayer.com/tx/0xc302e537346bb24d7968be7380bd0e10e79c661e02752c5ad604d47f3d989cd7), `FINALIZED`, `MAJORITY_AGREE` in one round, leader GenVM `SUCCESS`.
- Canonical reviewed state: `confirmed`; `target_match=yes`; leader diagnostic `change_kind=sunset`; `consensus_class=lifecycle_material`; confidence `97`. Stored rationale says the matching pinned notice adds a definite removal date to the baseline's supported endpoint. Consensus proves agreement under the contract's equivalence rule; it does not establish that every validator chose the same diagnostic subtype.
- Optional VersionGuard integration: the existing [`0xac581d2B38b8931119aeC9d1D3F2AFbB824101e2`](https://explorer-studio.genlayer.com/address/0xac581d2B38b8931119aeC9d1D3F2AFbB824101e2) v0.1.0 deployment registered fresh policy `vwk021-1790537404899` pointing to this v0.2.1 registry. Registration [`0xc1798ff2e0e7ea9ece953db9efc1b4e8ab080c16b9e600a84ee59feeb5b065a1`](https://explorer-studio.genlayer.com/tx/0xc1798ff2e0e7ea9ece953db9efc1b4e8ab080c16b9e600a84ee59feeb5b065a1) and application [`0x1be0e4da25d0f9d4fe12d481b24b0bc2e2199a60c1a9c5cf71084a88ba3f8a37`](https://explorer-studio.genlayer.com/tx/0x1be0e4da25d0f9d4fe12d481b24b0bc2e2199a60c1a9c5cf71084a88ba3f8a37) both finalized with `MAJORITY_AGREE` and leader GenVM `SUCCESS`; `get_policy()` returned `review_required`, `last_notice_id=VWK-021-LIVE-1790537109437`, `last_change_kind=sunset`.
- Live fail-closed scope check: policy `vwk021-wrongs-subject-1790537768533` was registered with subject `example/other-sdk` and the same registry/trusted proposer. Apply transaction [`0xe2495423caa8bece7e5c90098ecb050971ef7e33c2e66889ecf0a1a64551c6a1`](https://explorer-studio.genlayer.com/tx/0xe2495423caa8bece7e5c90098ecb050971ef7e33c2e66889ecf0a1a64551c6a1) finalized `MAJORITY_AGREE` with leader execution `ERROR`; canonical `get_policy()` remained `active`, with no notice recorded. Direct Mode integration tests also cover wrong proposer, wrong subject/version, and pending/cancelled notices.
- Release gates: 96 tests passed locally; preflight, GenVM lint, and ABI/schema passed for both contracts; GitHub Actions run [36343777104](https://github.com/Bibidee/VERSION-WAKE/actions/runs/36343777104) passed on the frozen source commit.

## References

- [GenLayer Skills](https://skills.genlayer.com/) — production contract writing, GenVM lint, Direct Mode, and integration workflows.
- [Intelligent Contract testing](https://docs.genlayer.com/developers/intelligent-contracts/testing)
- [Direct Mode API](https://docs.genlayer.com/api-references/genlayer-test/direct)
- [Equivalence Principle](https://docs.genlayer.com/developers/intelligent-contracts/equivalence-principle)
- [Non-determinism](https://docs.genlayer.com/developers/intelligent-contracts/features/non-determinism)
- [Web access](https://docs.genlayer.com/developers/intelligent-contracts/features/web-access)
- [Persistent storage](https://docs.genlayer.com/developers/intelligent-contracts/storage)
- [Calling LLMs](https://docs.genlayer.com/developers/intelligent-contracts/features/calling-llms)
