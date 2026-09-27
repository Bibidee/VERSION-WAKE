# Versionwake

Versionwake is a standalone GenLayer Intelligent Contract primitive for recording and independently classifying hash-committed upstream change notices against a specific dependency or standard version. It is aimed at release systems and downstream Intelligent Contracts that need an auditable signal when a notice says a pinned API, protocol, or specification version is breaking, deprecated, or scheduled for removal.

It is contract-only: there is no frontend, token, escrow, trusted decision service, or claim that a caller's publisher label proves real-world authority.

## Why GenLayer?

A deterministic contract can verify that downloaded bytes match a SHA-256 commitment, but cannot determine whether prose in a new notice actually applies to a named version or describes a deprecation rather than a compatible change. Versionwake uses ordinary deterministic code for IDs, bounds, hashes, state transitions, and output validation. Within `run_nondet_unsafe`, the leader and validators independently fetch the exact committed baseline and notice and make the bounded semantic classification. Only after consensus does deterministic execution store the result.

The reviewers compare `target_match`, `change_kind`, and the derived outcome. Rationale and exact confidence values are diagnostic rather than consensus-critical; crossing the fixed confidence threshold changes the derived outcome and therefore fails equivalence. Different categories or outcomes disagree. A malformed model response is never accepted as an analysis: its validator returns disagreement so GenLayer can rotate execution rather than committing an invented verdict. Source unavailability is retryable; integrity failures never authorize a change.

Without GenLayer, an application could still fetch and hash the documents, but would normally rely on one server or one model call to decide applicability and impact. That service could selectively classify notices. Versionwake places the semantic judgment and its explicit equivalence rule in the consensus execution path. This reduces single-operator dependence; it does not prove that an artifact publisher is authentic or that every validator is infallible.

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
- `get_notice(notice_id, proposer)` — read the complete evidence commitment and review record.
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
- Capacity is bounded to 512 records per deployment and is a lifetime limit; records are retained for auditability.
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
```

The preflight fails if a required tool, test, linter, or schema step is missing or failing. Tests live outside `contracts/`; only `contracts/versionwake.py` is deployable. A failed release gate means **do not freeze or deploy**; fix the root cause and rerun every gate.

## Studionet deployment

The current deployment is Versionwake v0.1.1 at frozen source commit `e3d756184e18e75b4f984cc0af3202e5d5c3c827`. Its deployment transaction finalized with `MAJORITY_AGREE` and leader GenVM `SUCCESS`.

- Contract: [`0xfaC85C5728F57b53B2973add5A14C24F7A45268d`](https://explorer-studio.genlayer.com/address/0xfaC85C5728F57b53B2973add5A14C24F7A45268d)
- Deployment transaction: [`0x0c9f55e00dc657da265f636d97ac77eb81dc520f686cb645fc583e4942698c99`](https://explorer-studio.genlayer.com/tx/0x0c9f55e00dc657da265f636d97ac77eb81dc520f686cb645fc583e4942698c99)
- Contract source SHA-256: `8c8b7ed5f03db17b83941133e885f95e458e2a29174bbf919e78b5a51d381392`
- Source parity: **verified byte-for-byte** using GenLayerJS `getContractCode()` (`gen_getContractCode`); local and retrieved source were both 17,452 bytes and had the same SHA-256.
- `get_info()` returned name `Versionwake`, version `0.1.1`, maximum 512 notices, maximum artifact size 16,000 bytes, and minimum confidence 75.
- Release gate: GitHub Actions run [36322467965](https://github.com/Bibidee/VERSION-WAKE/actions/runs/36322467965) passed; all 61 Direct Mode tests passed, followed by GenVM lint and schema generation.

### Live lifecycle evidence

This controlled fixture demonstrates the full submitted-notice review path. It is intentionally a contract fixture, not a claim about a real third-party SDK.

- Notice ID: `VWK-LIVE-002`; proposer: `0x2cd419603eBa593074653930Ddc4073d4FD8fc60`.
- Subject/version: `example/widget-sdk` / `1.0`.
- Baseline: [commit-pinned raw fixture](https://raw.githubusercontent.com/Bibidee/VERSION-WAKE/6c941f5e8b140acce424fc63f5f1afb26cfe694b/evidence/live/baseline.txt), SHA-256 `5cc129eaa1c8adbebf275ea957989e5f9baed1d5edc6b2c74e5fceb6130d5524`.
- Notice: [commit-pinned raw fixture](https://raw.githubusercontent.com/Bibidee/VERSION-WAKE/6c941f5e8b140acce424fc63f5f1afb26cfe694b/evidence/live/notice.txt), SHA-256 `6249db9322cef1faf3bef8426da5c55233bfc9c5dad0cf302df2e441542b4af9`.
- Proposal: [`0x6dffbb044b25ddbc71de02c8665fa916997486a1db20801a0c6917f1ad637cdf`](https://explorer-studio.genlayer.com/tx/0x6dffbb044b25ddbc71de02c8665fa916997486a1db20801a0c6917f1ad637cdf) — `FINALIZED`, `MAJORITY_AGREE`, GenVM `SUCCESS`; canonical read confirmed `pending` and matching committed fields.
- Review: [`0xf87adedd37e1ab7ac84a32e31aad76555c3d80bf595140c38662d859c5955a1e`](https://explorer-studio.genlayer.com/tx/0xf87adedd37e1ab7ac84a32e31aad76555c3d80bf595140c38662d859c5955a1e) — `FINALIZED`, `MAJORITY_AGREE`, GenVM `SUCCESS`.
- Canonical reviewed state: `confirmed`, `target_match=yes`, `change_kind=sunset`, confidence `95`; rationale: “The notice explicitly names Example Widget SDK version 1.0, matching the subject and pinned version, and states that GET /v1/status is deprecated with a scheduled removal date of 2025-01-01, which is a scheduled removal (sunset) relative to the baseline where the endpoint was supported.”
- The exact-scope `is_confirmed_for` gate returned `true` when queried with typed GenLayerJS arguments.

### Superseded v0.1.0 deployment

The earlier v0.1.0 deployment [`0xC85F766E74c77638E70859a417d01b799726Eb7E`](https://explorer-studio.genlayer.com/address/0xC85F766E74c77638E70859a417d01b799726Eb7E), transaction [`0x79eec415ef9e96903b211bab2fc35d672bd2d0a4d099c22f2a87ba4c82203bf5`](https://explorer-studio.genlayer.com/tx/0x79eec415ef9e96903b211bab2fc35d672bd2d0a4d099c22f2a87ba4c82203bf5), is historical and superseded. Its live review [`0xe2efe0ed00090b6dfb1018a8eb10be05c0b87ef9344764a533a720992d0b6742`](https://explorer-studio.genlayer.com/tx/0xe2efe0ed00090b6dfb1018a8eb10be05c0b87ef9344764a533a720992d0b6742) finalized with a GenVM event-encoding error at `NoticeReviewed.emit()` (`SystemError: 2: inval`); its notice remained pending. v0.1.1 bounds the event's positional fields and keeps the diagnostic category in the event blob.

## References

- [GenLayer Skills](https://skills.genlayer.com/) — production contract writing, GenVM lint, Direct Mode, and integration workflows.
- [Intelligent Contract testing](https://docs.genlayer.com/developers/intelligent-contracts/testing)
- [Direct Mode API](https://docs.genlayer.com/api-references/genlayer-test/direct)
- [Equivalence Principle](https://docs.genlayer.com/developers/intelligent-contracts/equivalence-principle)
- [Non-determinism](https://docs.genlayer.com/developers/intelligent-contracts/features/non-determinism)
- [Web access](https://docs.genlayer.com/developers/intelligent-contracts/features/web-access)
- [Persistent storage](https://docs.genlayer.com/developers/intelligent-contracts/storage)
- [Calling LLMs](https://docs.genlayer.com/developers/intelligent-contracts/features/calling-llms)
