import hashlib
import json

import pytest


CONTRACT = "contracts/versionwake.py"
DIRECT_MODE_GENVM_VERSION = "v0.2.12"
BASELINE_URL = "https://baseline.example.org/releases/v1.txt"
NOTICE_URL = "https://notices.example.net/releases/v1.txt"
BASELINE = b"Widget API v1 supports the legacy submit(record) method."
NOTICE = b"Widget API v1 submit(record) is deprecated and will be removed after 2027-01-01."
SUBJECT = "example/widget-api"
VERSION = "1.0"
SUMMARY = "The publisher notice deprecates submit(record) for Widget API v1."
LIVE_BASELINE = (
    b"Controlled Versionwake lifecycle fixture VWK-LIVE-001. "
    b"Example Widget SDK version 1.0 supports the GET /v1/status endpoint."
)
LIVE_NOTICE = (
    b"Controlled Versionwake lifecycle fixture VWK-LIVE-001. "
    b"Example Widget SDK version 1.0 deprecates GET /v1/status and schedules its removal for 2025-01-01."
)


def digest(raw):
    return "0x" + hashlib.sha256(raw).hexdigest()


def deploy(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    direct_vm.check_pickling = True
    return direct_deploy(CONTRACT, sdk_version=DIRECT_MODE_GENVM_VERSION)


def submit(contract, notice_id="notice-1", summary=SUMMARY, baseline=BASELINE, notice=NOTICE):
    contract.submit_notice(
        notice_id,
        SUBJECT,
        VERSION,
        BASELINE_URL,
        digest(baseline),
        NOTICE_URL,
        digest(notice),
        summary,
    )


def install_review_mocks(direct_vm, result=None, baseline=BASELINE, notice=NOTICE, baseline_status=200, notice_status=200):
    direct_vm.mock_web(r"baseline\.example\.org/releases/v1\.txt", {"status": baseline_status, "body": baseline})
    direct_vm.mock_web(r"notices\.example\.net/releases/v1\.txt", {"status": notice_status, "body": notice})
    if result is None:
        result = {
            "target_match": "yes",
            "change_kind": "deprecation",
            "confidence": 91,
            "rationale": "The notice names the pinned API version and explicitly says the method is deprecated.",
        }
    direct_vm.mock_llm(r"Return a JSON object with exactly these keys", json.dumps(result))


def submit_live_boundary_fixture(contract):
    contract.submit_notice(
        "live-boundary",
        "example/widget-sdk",
        "1.0",
        BASELINE_URL,
        digest(LIVE_BASELINE),
        NOTICE_URL,
        digest(LIVE_NOTICE),
        "The pinned fixture says the endpoint is deprecated and scheduled for removal.",
    )


def compare_validator_result(direct_vm, direct_deploy, direct_alice, leader, validator):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    submit(contract)
    install_review_mocks(direct_vm, result=leader)
    contract.review_notice("notice-1", direct_alice)
    direct_vm.clear_mocks()
    install_review_mocks(direct_vm, result=validator)
    return contract, direct_vm.run_validator()


def test_valid_proposal_is_namespaced_and_readable(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    submit(contract)
    row = contract.get_notice("notice-1", direct_alice)
    assert row["status"] == "pending"
    assert row["proposer"].lower() == ("0x" + direct_alice.hex()).lower()
    assert row["baseline_hash"] == digest(BASELINE)
    assert row["notice_hash"] == digest(NOTICE)
    assert row["confidence"] == 0
    assert row["rationale"] == ""

    with direct_vm.prank(direct_bob):
        submit(contract)
    assert contract.get_notice("notice-1", direct_bob)["status"] == "pending"


def test_duplicate_notice_rejected_within_proposer_namespace(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    submit(contract)
    with direct_vm.expect_revert("Notice unavailable"):
        submit(contract)


@pytest.mark.parametrize("notice_id", ["", "two words", "../notice", "x" * 97])
def test_invalid_notice_id_rejected(direct_vm, direct_deploy, direct_alice, notice_id):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    with direct_vm.expect_revert("Invalid notice_id"):
        submit(contract, notice_id=notice_id)


@pytest.mark.parametrize("url", [
    "http://public.example.org/change",
    "https://localhost/change",
    "https://127.0.0.1/change",
    "https://10.0.0.1/change",
    "https://192.168.1.1/change",
    "https://172.16.1.1/change",
    "https://[::1]/change",
    "https://[fc00::1]/change",
    "https://[fe80::1]/change",
    "https://user@public.example.org/change",
    "https://public.example.org:8443/change",
    "https://service.internal/change",
    "https://registry.home.arpa/change",
    "https://service.intranet/change",
    "https://registry.corp/change",
])
def test_non_public_or_unsafe_url_forms_rejected(direct_vm, direct_deploy, direct_alice, url):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    with direct_vm.expect_revert():
        contract.submit_notice("bad-url", SUBJECT, VERSION, url, digest(BASELINE), NOTICE_URL, digest(NOTICE), SUMMARY)


@pytest.mark.parametrize("bad_hash", ["", "0x12", "0x" + "G" * 64, 123])
def test_malformed_hash_rejected(direct_vm, direct_deploy, direct_alice, bad_hash):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    with direct_vm.expect_revert("Invalid SHA-256"):
        contract.submit_notice("bad-hash", SUBJECT, VERSION, BASELINE_URL, bad_hash, NOTICE_URL, digest(NOTICE), SUMMARY)


@pytest.mark.parametrize("summary", ["", "   \n\t   ", "s" * 501])
def test_empty_or_oversized_summary_rejected(direct_vm, direct_deploy, direct_alice, summary):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    with direct_vm.expect_revert("Invalid summary"):
        submit(contract, summary=summary)


def test_summary_is_whitespace_normalized(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    submit(contract, summary="  publisher   marks\n  v1   deprecated ")
    assert contract.get_notice("notice-1", direct_alice)["summary"] == "publisher marks v1 deprecated"


def test_cancel_is_proposer_scoped_and_pending_only(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    submit(contract)
    with direct_vm.prank(direct_bob):
        with direct_vm.expect_revert("Notice not found"):
            contract.cancel_notice("notice-1")
    contract.cancel_notice("notice-1")
    assert contract.get_notice("notice-1", direct_alice)["status"] == "cancelled"
    with direct_vm.expect_revert("Only the proposer"):
        contract.cancel_notice("notice-1")


def test_get_info_reports_version_and_protocol_bounds(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    info = contract.get_info()
    assert info["name"] == "Versionwake"
    assert info["version"] == "0.2.1"
    assert info["max_notices_per_proposer_lifetime"] == 64
    assert info["max_artifact_bytes"] == 16000
    assert info["minimum_confidence"] == 75
    assert info["consensus_classes"] == ["none", "non_breaking", "breaking", "lifecycle_material", "unclear"]


def test_lifetime_capacity_is_isolated_by_proposer_and_keeps_terminal_history(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    for index in range(64):
        submit(contract, notice_id=f"notice-{index}")
    assert contract.get_proposer_notice_count(direct_alice) == 64

    install_review_mocks(direct_vm)
    contract.review_notice("notice-0", direct_alice)
    contract.cancel_notice("notice-1")
    assert contract.get_notice("notice-0", direct_alice)["status"] == "confirmed"
    assert contract.get_notice("notice-1", direct_alice)["status"] == "cancelled"
    assert contract.get_proposer_notice_count(direct_alice) == 64

    with direct_vm.expect_revert("proposer capacity reached"):
        submit(contract, notice_id="notice-64")

    # Reaching one account's cap does not consume another account's quota;
    # proposer-scoped IDs also allow an independent second record with the same ID.
    with direct_vm.prank(direct_bob):
        submit(contract, notice_id="notice-0")
    assert contract.get_notice("notice-0", direct_bob)["status"] == "pending"
    assert contract.get_proposer_notice_count(direct_bob) == 1


def test_per_proposer_capacity_boundary_has_no_decrement_or_overflow_path(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    for index in range(63):
        submit(contract, notice_id=f"boundary-{index}")
    assert contract.get_proposer_notice_count(direct_alice) == 63
    submit(contract, notice_id="boundary-63")
    assert contract.get_proposer_notice_count(direct_alice) == 64
    with direct_vm.expect_revert("proposer capacity reached"):
        submit(contract, notice_id="boundary-overflow")
    assert contract.get_proposer_notice_count(direct_alice) == 64


def test_review_hash_verifies_both_documents_and_confirms_deprecation(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    submit(contract)
    install_review_mocks(direct_vm)
    contract.review_notice("notice-1", direct_alice)
    row = contract.get_notice("notice-1", direct_alice)
    assert row["status"] == "confirmed"
    assert row["outcome"] == "confirmed"
    assert row["target_match"] == "yes"
    assert row["change_kind"] == "deprecation"
    assert row["consensus_class"] == "lifecycle_material"
    assert row["confidence"] == 91
    assert contract.is_confirmed_for("notice-1", direct_alice, SUBJECT, VERSION) is True
    assert contract.is_confirmed_for("notice-1", direct_alice, SUBJECT, "2.0") is False


@pytest.mark.parametrize("result,expected", [
    ({"target_match": "yes", "change_kind": "none", "confidence": 88, "rationale": "No change."}, "no_material_change"),
    ({"target_match": "yes", "change_kind": "non_breaking", "confidence": 88, "rationale": "Compatible change."}, "no_material_change"),
    ({"target_match": "no", "change_kind": "deprecation", "confidence": 88, "rationale": "Different API."}, "not_applicable"),
    ({"target_match": "yes", "change_kind": "unclear", "confidence": 88, "rationale": "Effect unclear."}, "inconclusive"),
    ({"target_match": "yes", "change_kind": "breaking", "confidence": 74, "rationale": "Low confidence."}, "inconclusive"),
])
def test_outcome_is_deterministic_and_fail_closed(direct_vm, direct_deploy, direct_alice, result, expected):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    submit(contract)
    install_review_mocks(direct_vm, result=result)
    contract.review_notice("notice-1", direct_alice)
    assert contract.get_notice("notice-1", direct_alice)["status"] == expected
    assert contract.is_confirmed_for("notice-1", direct_alice, SUBJECT, VERSION) is False


def test_hash_mismatch_fails_closed_and_leaves_notice_retryable(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    submit(contract)
    install_review_mocks(direct_vm, notice=b"different notice bytes")
    with direct_vm.expect_revert("Committed source could not be verified"):
        contract.review_notice("notice-1", direct_alice)
    assert contract.get_notice("notice-1", direct_alice)["status"] == "pending"


@pytest.mark.parametrize("which,content", [
    ("baseline", b""),
    ("notice", b""),
    ("baseline", b"x" * 16001),
    ("notice", b"y" * 16001),
    ("baseline", b"\xff"),
    ("notice", b"\xff"),
])
def test_empty_oversized_and_invalid_utf8_sources_fail_closed(direct_vm, direct_deploy, direct_alice, which, content):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    baseline = content if which == "baseline" else BASELINE
    notice = content if which == "notice" else NOTICE
    submit(contract, baseline=baseline, notice=notice)
    install_review_mocks(direct_vm, baseline=baseline, notice=notice)
    with direct_vm.expect_revert("Committed source could not be verified"):
        contract.review_notice("notice-1", direct_alice)
    assert contract.get_notice("notice-1", direct_alice)["status"] == "pending"


def test_http_unavailable_is_retryable_without_state_mutation(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    submit(contract)
    install_review_mocks(direct_vm, baseline_status=503)
    with direct_vm.expect_revert("External review unavailable"):
        contract.review_notice("notice-1", direct_alice)
    assert contract.get_notice("notice-1", direct_alice)["status"] == "pending"


@pytest.mark.parametrize("status", [400, 404])
def test_permanent_http_failure_is_not_authorizing(direct_vm, direct_deploy, direct_alice, status):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    submit(contract)
    install_review_mocks(direct_vm, baseline_status=status)
    with direct_vm.expect_revert("Committed source could not be verified"):
        contract.review_notice("notice-1", direct_alice)
    assert contract.get_notice("notice-1", direct_alice)["status"] == "pending"


@pytest.mark.parametrize("status", [429, 500, 503])
def test_rate_limit_and_server_errors_are_retryable(direct_vm, direct_deploy, direct_alice, status):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    submit(contract)
    install_review_mocks(direct_vm, baseline_status=status)
    with direct_vm.expect_revert("External review unavailable"):
        contract.review_notice("notice-1", direct_alice)
    assert contract.get_notice("notice-1", direct_alice)["status"] == "pending"


def test_malformed_model_output_never_confirms(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    submit(contract)
    direct_vm.mock_web(r"baseline\.example\.org/releases/v1\.txt", {"status": 200, "body": BASELINE})
    direct_vm.mock_web(r"notices\.example\.net/releases/v1\.txt", {"status": 200, "body": NOTICE})
    direct_vm.mock_llm(r"Return a JSON object with exactly these keys", json.dumps({"target_match": "yes"}))
    with direct_vm.expect_revert():
        contract.review_notice("notice-1", direct_alice)
    assert contract.get_notice("notice-1", direct_alice)["status"] == "pending"
    assert contract.is_confirmed_for("notice-1", direct_alice, SUBJECT, VERSION) is False


@pytest.mark.parametrize("bad_result", [
    [],
    {"target_match": "yes", "change_kind": "deprecation", "confidence": 95, "rationale": "Valid", "extra": "no"},
    {"target_match": "maybe", "change_kind": "deprecation", "confidence": 95, "rationale": "Invalid enum"},
    {"target_match": "yes", "change_kind": "deprecation", "confidence": True, "rationale": "Boolean is not integer confidence"},
    {"target_match": "yes", "change_kind": "deprecation", "confidence": -1, "rationale": "Too low"},
    {"target_match": "yes", "change_kind": "deprecation", "confidence": 101, "rationale": "Too high"},
    {"target_match": "yes", "change_kind": "deprecation", "confidence": 95, "rationale": "   "},
    {"target_match": "yes", "change_kind": "deprecation", "confidence": 95, "rationale": "r" * 401},
])
def test_malformed_model_shapes_are_never_authorizing(direct_vm, direct_deploy, direct_alice, bad_result):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    submit(contract)
    install_review_mocks(direct_vm, result=bad_result)
    with direct_vm.expect_revert():
        contract.review_notice("notice-1", direct_alice)
    assert contract.get_notice("notice-1", direct_alice)["status"] == "pending"
    assert contract.is_confirmed_for("notice-1", direct_alice, SUBJECT, VERSION) is False


def test_validator_rationale_variance_is_ignored_but_decision_disagreement_fails(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    submit(contract)
    leader = {"target_match": "yes", "change_kind": "deprecation", "confidence": 91, "rationale": "The notice explicitly deprecates the pinned interface."}
    install_review_mocks(direct_vm, result=leader)
    contract.review_notice("notice-1", direct_alice)

    direct_vm.clear_mocks()
    direct_vm.mock_web(r"baseline\.example\.org/releases/v1\.txt", {"status": 200, "body": BASELINE})
    direct_vm.mock_web(r"notices\.example\.net/releases/v1\.txt", {"status": 200, "body": NOTICE})
    direct_vm.mock_llm(r"Return a JSON object with exactly these keys", json.dumps({"target_match": "yes", "change_kind": "deprecation", "confidence": 96, "rationale": "The old version is named, and removal is stated."}))
    assert direct_vm.run_validator() is True

    direct_vm.clear_mocks()
    direct_vm.mock_web(r"baseline\.example\.org/releases/v1\.txt", {"status": 200, "body": BASELINE})
    direct_vm.mock_web(r"notices\.example\.net/releases/v1\.txt", {"status": 200, "body": NOTICE})
    direct_vm.mock_llm(r"Return a JSON object with exactly these keys", json.dumps({"target_match": "yes", "change_kind": "non_breaking", "confidence": 96, "rationale": "This sounds compatible."}))
    assert direct_vm.run_validator() is False


def test_validator_confidence_crossing_threshold_disagrees(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    submit(contract)
    install_review_mocks(direct_vm, result={"target_match": "yes", "change_kind": "sunset", "confidence": 82, "rationale": "The version is scheduled for removal."})
    contract.review_notice("notice-1", direct_alice)
    direct_vm.clear_mocks()
    direct_vm.mock_web(r"baseline\.example\.org/releases/v1\.txt", {"status": 200, "body": BASELINE})
    direct_vm.mock_web(r"notices\.example\.net/releases/v1\.txt", {"status": 200, "body": NOTICE})
    direct_vm.mock_llm(r"Return a JSON object with exactly these keys", json.dumps({"target_match": "yes", "change_kind": "sunset", "confidence": 70, "rationale": "The signal is too uncertain."}))
    assert direct_vm.run_validator() is False


@pytest.mark.parametrize("leader_kind,leader_confidence,validator_kind,validator_confidence", [
    ("deprecation", 91, "sunset", 82),
    ("sunset", 82, "deprecation", 96),
    ("deprecation", 81, "sunset", 99),
    ("sunset", 70, "deprecation", 74),
])
def test_lifecycle_subtypes_agree_when_target_and_threshold_outcome_match(
    direct_vm, direct_deploy, direct_alice, leader_kind, leader_confidence, validator_kind, validator_confidence
):
    leader = {
        "target_match": "yes",
        "change_kind": leader_kind,
        "confidence": leader_confidence,
        "rationale": "The notice calls the endpoint deprecated and gives a scheduled removal date.",
    }
    validator = {
        "target_match": "yes",
        "change_kind": validator_kind,
        "confidence": validator_confidence,
        "rationale": "The same wording can be read as a sunset of the pinned endpoint.",
    }
    contract, agreed = compare_validator_result(direct_vm, direct_deploy, direct_alice, leader, validator)
    assert agreed is True
    row = contract.get_notice("notice-1", direct_alice)
    assert row["consensus_class"] == "lifecycle_material"
    assert row["change_kind"] == leader_kind  # preserve the leader subtype for diagnostics
    assert row["status"] == ("confirmed" if leader_confidence >= 75 else "inconclusive")


@pytest.mark.parametrize("leader_kind,validator_kind", [
    ("breaking", "deprecation"),
    ("breaking", "sunset"),
    ("non_breaking", "deprecation"),
    ("none", "sunset"),
    ("deprecation", "unclear"),
])
def test_different_change_classes_still_disagree(direct_vm, direct_deploy, direct_alice, leader_kind, validator_kind):
    leader = {"target_match": "yes", "change_kind": leader_kind, "confidence": 91, "rationale": "Leader classification."}
    validator = {"target_match": "yes", "change_kind": validator_kind, "confidence": 91, "rationale": "Validator classification."}
    _, agreed = compare_validator_result(direct_vm, direct_deploy, direct_alice, leader, validator)
    assert agreed is False


@pytest.mark.parametrize("leader_target,validator_target", [
    ("yes", "no"),
    ("yes", "unclear"),
])
def test_lifecycle_equivalence_requires_identical_target_applicability(
    direct_vm, direct_deploy, direct_alice, leader_target, validator_target
):
    leader = {"target_match": leader_target, "change_kind": "deprecation", "confidence": 91, "rationale": "Leader."}
    validator = {"target_match": validator_target, "change_kind": "sunset", "confidence": 91, "rationale": "Validator."}
    _, agreed = compare_validator_result(direct_vm, direct_deploy, direct_alice, leader, validator)
    assert agreed is False


def test_lifecycle_equivalence_does_not_hide_threshold_crossing(direct_vm, direct_deploy, direct_alice):
    leader = {"target_match": "yes", "change_kind": "sunset", "confidence": 82, "rationale": "Above threshold."}
    validator = {"target_match": "yes", "change_kind": "deprecation", "confidence": 74, "rationale": "Below threshold."}
    _, agreed = compare_validator_result(direct_vm, direct_deploy, direct_alice, leader, validator)
    assert agreed is False


def test_exact_live_deprecation_sunset_fixture_reaches_canonical_equivalence(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    submit_live_boundary_fixture(contract)
    leader = {"target_match": "yes", "change_kind": "sunset", "confidence": 82, "rationale": "It schedules endpoint removal."}
    install_review_mocks(direct_vm, result=leader, baseline=LIVE_BASELINE, notice=LIVE_NOTICE)
    contract.review_notice("live-boundary", direct_alice)
    direct_vm.clear_mocks()
    validator = {"target_match": "yes", "change_kind": "deprecation", "confidence": 91, "rationale": "It declares the endpoint deprecated."}
    install_review_mocks(direct_vm, result=validator, baseline=LIVE_BASELINE, notice=LIVE_NOTICE)
    assert direct_vm.run_validator() is True
    row = contract.get_notice("live-boundary", direct_alice)
    assert row["status"] == "confirmed"
    assert row["consensus_class"] == "lifecycle_material"
    assert row["change_kind"] == "sunset"


def test_malformed_leader_result_cannot_agree_with_valid_lifecycle_analysis(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    submit(contract)
    install_review_mocks(direct_vm, result={"target_match": "yes"})
    with direct_vm.expect_revert():
        contract.review_notice("notice-1", direct_alice)
    direct_vm.clear_mocks()
    install_review_mocks(direct_vm, result={"target_match": "yes", "change_kind": "sunset", "confidence": 91, "rationale": "Valid."})
    assert direct_vm.run_validator() is False
    assert contract.get_notice("notice-1", direct_alice)["status"] == "pending"


def test_retryable_leader_observation_cannot_agree_with_valid_analysis(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    submit(contract)
    install_review_mocks(direct_vm, baseline_status=503)
    with direct_vm.expect_revert("External review unavailable"):
        contract.review_notice("notice-1", direct_alice)
    direct_vm.clear_mocks()
    install_review_mocks(direct_vm, result={"target_match": "yes", "change_kind": "sunset", "confidence": 91, "rationale": "Valid."})
    assert direct_vm.run_validator() is False
    assert contract.get_notice("notice-1", direct_alice)["status"] == "pending"


def test_invalid_artifact_leader_observation_cannot_agree_with_valid_analysis(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_vm, direct_deploy, direct_alice)
    submit(contract)
    install_review_mocks(direct_vm, baseline=b"different bytes fail the committed digest")
    with direct_vm.expect_revert("Committed source could not be verified"):
        contract.review_notice("notice-1", direct_alice)
    direct_vm.clear_mocks()
    install_review_mocks(direct_vm, result={"target_match": "yes", "change_kind": "sunset", "confidence": 91, "rationale": "Valid."})
    assert direct_vm.run_validator() is False
    assert contract.get_notice("notice-1", direct_alice)["status"] == "pending"
