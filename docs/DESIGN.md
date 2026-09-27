# Versionwake and VersionGuard design

## Responsibility split

Versionwake remains a standalone semantic notice registry. VersionGuard is an optional but integrated consumer contract: it turns an exact, consensus-backed Versionwake result into a deterministic dependency-policy transition. It does not duplicate semantic interpretation.

```text
hash-bound artifacts -> Versionwake validators independently fetch/review -> exact-scope confirmed record
                      -> VersionGuard verifies registry + proposer + notice + subject + pinned version
                      -> deterministic review_required or migration_required state
```

## Versionwake protocol boundary

Versionwake records a proposer-scoped, immutable notice about one named subject and pinned version. The submitter commits two HTTPS artifacts: a baseline snapshot and a candidate notice. Reviewers independently fetch each URL, reject non-success HTTP results, empty/oversized/invalid-UTF-8 content, and compare SHA-256 against the exact raw bytes. Only verified UTF-8 content is passed to semantic review.

Deterministic responsibilities include input normalization and limits, DNS-style HTTPS URL admission, proposer namespacing, duplicate/capacity checks, raw-byte digest checks, schema validation, outcome derivation, access control, and persistent state updates. Web requests and model calls run only within `gl.vm.run_nondet_unsafe`; contract storage is copied into local strings before the block. No storage writes or events occur inside the nondeterministic callbacks.

## Consensus rule

The model returns a bounded object with `target_match`, `change_kind`, `confidence`, and `rationale`. The contract validates exact keys, enums, types, integer bounds, and rationale length. Outcome classification and consensus-class derivation are deterministic:

- `confirmed`: exact target match, material effect (`breaking`, `deprecation`, or `sunset`), and confidence >= 75.
- `no_material_change`: exact target match, `none` or `non_breaking`, and confidence >= 75.
- `not_applicable`: clear non-match and confidence >= 75.
- `inconclusive`: unclear dimension or confidence below 75.

Each validator repeats the full two-artifact fetch and semantic analysis. Equivalence requires exact `target_match`, equal bounded consensus class, and equal deterministic outcome. The diagnostic subtype and canonical class are separate: when `target_match=yes`, `deprecation` and `sunset` map to `lifecycle_material`, because both are material lifecycle changes and produce the same `confirmed` consequence above the confidence threshold. The accepted leader subtype remains in `change_kind`; `consensus_class` exposes the class validators agreed on. These are not interchangeable with other classes: `breaking` remains distinct because VersionGuard requires migration, `non_breaking` and `none` remain distinct and non-material, and `unclear` remains fail-closed. Target `no` or `unclear` does not receive lifecycle canonicalization. If confidence observations straddle 75, deterministic outcomes differ and equivalence fails. Exact rationales and confidence values are not compared, but their bounded validity and threshold effect are enforced. Malformed output is rejected by validator equivalence instead of becoming a consensual authorization result. Fetch/LLM availability failures are retryable and do not mutate the pending record; integrity/content failures cannot authorize.

## State machine and capacity

```text
PENDING -> CONFIRMED
        -> NO_MATERIAL_CHANGE
        -> NOT_APPLICABLE
        -> INCONCLUSIVE
        -> CANCELLED
```

Only the original proposer can cancel, and only while pending. Finalized review states are immutable. A fresh source observation is represented by a new notice ID. IDs are scoped as `<proposer address>:<caller id>`, so unrelated submitters cannot front-run a global ID. Each proposer address has a 64-submission lifetime quota. Cancelled and reviewed records stay in storage and continue consuming quota; no deletion/reclaim path exists. This prevents one address from consuming everyone else's quota but does not provide Sybil resistance or a strict global storage bound. Aggregate deployment storage remains open to many distinct addresses; that trade-off is documented rather than disguised as a global cap.

## VersionGuard consumer policy

The policy owner registers an immutable tuple: owner namespace, policy ID, dependency subject, pinned version, accepted Versionwake contract address, and trusted proposer address. The configured address is an explicit trust choice, not proof of real-world publisher identity. A random submitter cannot affect the policy unless it is the address selected by the policy owner.

`apply_notice(owner, policy_id, notice_id)` is permissionless to trigger but deterministic in effect. It reads `get_info`, `get_notice(notice_id, trusted_proposer)`, and `is_confirmed_for(notice_id, trusted_proposer, subject, pinned_version)` from the configured contract. It checks registry identity, exact notice/proposer/subject/version, canonical `confirmed` status and outcome, target match, material change kind, and the registry's confidence threshold. Only then does it write `migration_required` for breaking changes or `review_required` for deprecation/sunset. Both lifecycle diagnostic subtypes therefore have the same policy consequence; breaking remains separate. Other statuses, external-call failures, wrong scope, malformed values, and unknown registries fail closed without changing policy state.

Each exact notice reference is marked applied once. A transitioned policy is terminal; a new pinned dependency configuration uses a new policy ID. VersionGuard has a per-owner lifetime cap of 64 policies, retains all records, and has no owner reset/delete method. This also does not claim global Sybil-resistant capacity.

The downstream consumer must enforce policy state in its own authorization path. A VersionGuard state is not a global pause primitive and cannot force unrelated contracts to obey it.

## Trust model and limitations

The contracts prove what exact bytes validators reviewed, not who authored them, whether the URL's DNS/redirect route is safe, or whether the publisher has authority in the real world. Versionwake does not poll URLs continuously. An integrator must select acceptable submitters/publishers and bind `is_confirmed_for` to the exact subject/version. VersionGuard adds an explicit proposer address policy, but does not authenticate the underlying identity. Semantic-model/provider variability, validator disagreement, or unavailable HTTPS resources can delay or prevent a decision; uncertainty never becomes `confirmed` or a VersionGuard transition.
