# Versionwake design

## Protocol boundary

Versionwake records a proposer-scoped, immutable notice about one named subject and pinned version. The submitter commits two HTTPS artifacts: a baseline snapshot and a candidate notice. Reviewers independently fetch each URL, reject non-success HTTP results, empty/oversized/invalid-UTF-8 content, and compare SHA-256 against the exact raw bytes. Only verified UTF-8 content is passed to semantic review.

Deterministic responsibilities include input normalization and limits, DNS-style HTTPS URL admission, proposer namespacing, duplicate/capacity checks, raw-byte digest checks, schema validation, outcome derivation, access control, and persistent state updates. Web requests and model calls run only within `gl.vm.run_nondet_unsafe`; contract storage is copied into local strings before the block. No storage writes or events occur inside the nondeterministic callbacks.

## Consensus rule

The model returns a bounded object with `target_match`, `change_kind`, `confidence`, and `rationale`. The contract validates exact keys, enums, types, integer bounds, and rationale length. Approval-like classification is deterministic:

- `confirmed`: exact target match, material effect (`breaking`, `deprecation`, or `sunset`), and confidence >= 75.
- `no_material_change`: exact target match, `none` or `non_breaking`, and confidence >= 75.
- `not_applicable`: clear non-match and confidence >= 75.
- `inconclusive`: unclear dimension or confidence below 75.

The validator repeats the full two-artifact fetch and semantic analysis. It accepts only when `target_match`, `change_kind`, and derived outcome agree. The reason text is not compared, because natural-language rationales vary. Confidence is not compared numerically; its security-relevant effect is captured by whether each validator crosses the same fixed threshold and therefore derives the same outcome. A model output that does not satisfy the schema is marked malformed, and the validator rejects it rather than creating a consensual failure result or a false classification.

Fetch/LLM availability failures have bounded retryable categories. They can be accepted only if the independent observer reports the same retryable category; after agreement, the public method raises a retryable error without changing the pending record. Invalid committed content similarly cannot transition the record to a confirmed state. Variation in external responses may cause disagreement or a transaction that does not finalize; safety is preferred over forcing consensus.

## State machine and capacity

```text
PENDING -> CONFIRMED
        -> NO_MATERIAL_CHANGE
        -> NOT_APPLICABLE
        -> INCONCLUSIVE
        -> CANCELLED
```

Only the original proposer can cancel, and only before a successful review. Finalized review states are immutable. A fresh source observation is represented by a new notice ID. IDs are scoped as `<proposer address>:<caller id>`, so unrelated submitters cannot front-run a global ID. A single deployment accepts at most 512 notices; finalized records remain stored for auditability, making that intentionally a finite lifetime capacity.

## Trust model

The contract proves what exact bytes validators reviewed, not who authored them, whether the URL's DNS/redirect route is safe, or whether the publisher has authority in the real world. It does not poll URLs, enforce an API migration, or perform a downstream state change. An integrator must select acceptable submitters/publishers and use `is_confirmed_for` with the exact subject/version as one signal in its own policy.
