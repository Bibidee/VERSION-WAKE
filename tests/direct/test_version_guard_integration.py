import hashlib
import json
import os
import tempfile

import pytest


BASELINE_URL = "https://baseline.example.org/releases/v1.txt"
NOTICE_URL = "https://notices.example.net/releases/v1.txt"
BASELINE = b"Widget SDK version 1.0 supports GET /v1/status."
NOTICE = b"Widget SDK version 1.0 is a breaking change: GET /v1/status is removed."
SUBJECT = "example/widget-sdk"
VERSION = "1.0"


def digest(data):
    return "0x" + hashlib.sha256(data).hexdigest()


@pytest.fixture
def sim_world(monkeypatch):
    """Use GenLayer Test's GlSim call hook to exercise real IC-to-IC view calls."""
    from gltest.direct import sdk_loader
    from gltest.direct import loader
    from glsim.engine import SimEngine
    from glsim.state import StateStore

    # Keep this simulator run on the same runner pinned by the repository.
    monkeypatch.setattr(sdk_loader, "list_cached_versions", lambda: ["v0.2.12"])
    # The pinned loader unlinks the temporary calldata file while its handle
    # remains attached to fd 0. Windows rejects that unlink. Preserve genuine
    # encoded message injection and defer only the cleanup until VM teardown.
    pending_temp_paths = []
    original_inject = loader._inject_message_to_fd0

    def windows_safe_inject(vm):
        original_unlink = os.unlink

        def defer_open_temp_unlink(path, *args, **kwargs):
            try:
                original_unlink(path, *args, **kwargs)
            except PermissionError:
                pending_temp_paths.append(path)

        with monkeypatch.context() as patch:
            patch.setattr(os, "unlink", defer_open_temp_unlink)
            original_inject(vm)

        if pending_temp_paths and not getattr(vm, "_versionwake_cleanup_wrapped", False):
            cleanup = vm._cleanup_after_deactivate

            def cleanup_with_temp_files():
                cleanup()
                while pending_temp_paths:
                    path = pending_temp_paths.pop()
                    try:
                        original_unlink(path)
                    except FileNotFoundError:
                        pass

            vm._cleanup_after_deactivate = cleanup_with_temp_files
            vm._versionwake_cleanup_wrapped = True

    monkeypatch.setattr(loader, "_inject_message_to_fd0", windows_safe_inject)
    state = StateStore(chain_id=61999, seed="versionguard-c2c-tests")
    engine = SimEngine(state)
    engine.activate()
    try:
        owner = "0x" + "11" * 20
        proposer = "0x" + "22" * 20
        attacker = "0x" + "33" * 20
        versionwake_address, _ = engine.deploy("contracts/versionwake.py", sender=proposer)
        guard_address, _ = engine.deploy("contracts/version_guard.py", sender=owner)
        from genlayer.py.types import Address

        addresses = {
            "owner": Address(bytes.fromhex(owner[2:])),
            "proposer": Address(bytes.fromhex(proposer[2:])),
            "attacker": Address(bytes.fromhex(attacker[2:])),
            "versionwake": Address(bytes.fromhex(versionwake_address[2:])),
            "missing_registry": Address(b"\x99" * 20),
        }
        engine.vm.mock_web(r"baseline\.example\.org/releases/v1\.txt", {"status": 200, "body": BASELINE})
        engine.vm.mock_web(r"notices\.example\.net/releases/v1\.txt", {"status": 200, "body": NOTICE})
        yield {
            "engine": engine,
            "versionwake": versionwake_address,
            "guard": guard_address,
            "addresses": addresses,
            "owner": owner,
            "proposer": proposer,
            "attacker": attacker,
        }
    finally:
        engine.deactivate()


def propose_review(world, notice_id="n-1", *, subject=SUBJECT, version=VERSION, review=True, result=None, cancel=False):
    engine = world["engine"]
    engine.call_method(
        world["versionwake"],
        "submit_notice",
        [notice_id, subject, version, BASELINE_URL, digest(BASELINE), NOTICE_URL, digest(NOTICE), "Pinned change evidence."],
        sender=world["proposer"],
    )
    if cancel:
        engine.call_method(world["versionwake"], "cancel_notice", [notice_id], sender=world["proposer"])
    elif review:
        if result is None:
            result = {"target_match": "yes", "change_kind": "breaking", "confidence": 90, "rationale": "The pinned endpoint is removed in the notice."}
        engine.vm.mock_web(r"baseline\.example\.org/releases/v1\.txt", {"status": 200, "body": BASELINE})
        engine.vm.mock_web(r"notices\.example\.net/releases/v1\.txt", {"status": 200, "body": NOTICE})
        engine.vm.mock_llm(r"Return a JSON object with exactly these keys", json.dumps(result))
        engine.call_method(
            world["versionwake"],
            "review_notice",
            [notice_id, world["addresses"]["proposer"]],
            sender=world["proposer"],
        )
        engine.vm.clear_mocks()


def register_policy(world, policy_id="widget-policy", *, subject=SUBJECT, version=VERSION, versionwake=None, trusted_proposer=None):
    world["engine"].call_method(
        world["guard"],
        "register_policy",
        [
            policy_id,
            subject,
            version,
            versionwake or world["addresses"]["versionwake"],
            trusted_proposer or world["addresses"]["proposer"],
        ],
        sender=world["owner"],
    )


def policy(world, policy_id="widget-policy"):
    return world["engine"].call_method(
        world["guard"],
        "get_policy",
        [policy_id, world["addresses"]["owner"]],
        sender=world["owner"],
    )


def apply(world, policy_id="widget-policy", notice_id="n-1", sender=None):
    return world["engine"].call_method(
        world["guard"],
        "apply_notice",
        [world["addresses"]["owner"], policy_id, notice_id],
        sender=sender or world["attacker"],
    )


def test_real_versionwake_view_call_causes_versionguard_transition_and_replay_is_rejected(sim_world):
    world = sim_world
    propose_review(world)
    register_policy(world)
    before = policy(world)
    assert before["state"] == "active"

    apply(world)
    after = policy(world)
    assert after["state"] == "migration_required"
    assert after["last_notice_id"] == "n-1"
    assert after["last_change_kind"] == "breaking"

    with pytest.raises(Exception, match="Notice already applied"):
        apply(world)
    assert policy(world)["state"] == "migration_required"

    # A distinct notice cannot create another consequence against this terminal policy.
    propose_review(world, notice_id="n-2")
    with pytest.raises(Exception, match="Policy is terminal"):
        apply(world, notice_id="n-2")
    assert policy(world)["last_notice_id"] == "n-1"


@pytest.mark.parametrize("result,expected_status", [
    ({"target_match": "yes", "change_kind": "breaking", "confidence": 75, "rationale": "Threshold boundary is confirmed."}, "confirmed"),
    ({"target_match": "yes", "change_kind": "none", "confidence": 92, "rationale": "No material change."}, "no_material_change"),
    ({"target_match": "no", "change_kind": "breaking", "confidence": 92, "rationale": "This is another target."}, "not_applicable"),
    ({"target_match": "yes", "change_kind": "breaking", "confidence": 74, "rationale": "Below threshold."}, "inconclusive"),
])
def test_only_confirmed_exact_threshold_material_result_transitions(sim_world, result, expected_status):
    world = sim_world
    propose_review(world, result=result)
    row = world["engine"].call_method(
        world["versionwake"], "get_notice", ["n-1", world["addresses"]["proposer"]], sender=world["proposer"]
    )
    assert row["status"] == expected_status
    register_policy(world)
    if expected_status == "confirmed":
        apply(world)
        assert policy(world)["state"] == "migration_required"
    else:
        with pytest.raises(Exception):
            apply(world)
        assert policy(world)["state"] == "active"


def test_untrusted_proposer_cannot_apply_another_proposers_notice(sim_world):
    world = sim_world
    register_policy(world)
    attacker = world["attacker"]
    engine = world["engine"]
    engine.call_method(
        world["versionwake"],
        "submit_notice",
        ["attacker-notice", SUBJECT, VERSION, BASELINE_URL, digest(BASELINE), NOTICE_URL, digest(NOTICE), "Untrusted submitter."],
        sender=attacker,
    )
    engine.vm.mock_llm(r"Return a JSON object with exactly these keys", json.dumps({"target_match": "yes", "change_kind": "breaking", "confidence": 96, "rationale": "Apparently material."}))
    engine.call_method(world["versionwake"], "review_notice", ["attacker-notice", world["addresses"]["attacker"]], sender=attacker)
    engine.vm.clear_mocks()

    with pytest.raises(Exception):
        apply(world, notice_id="attacker-notice")
    assert policy(world)["state"] == "active"


@pytest.mark.parametrize("policy_subject,policy_version", [
    ("example/other-sdk", VERSION),
    (SUBJECT, "9.9"),
])
def test_wrong_subject_or_pinned_version_cannot_trigger_policy(sim_world, policy_subject, policy_version):
    world = sim_world
    propose_review(world)
    register_policy(world, subject=policy_subject, version=policy_version)
    with pytest.raises(Exception, match="exact policy scope"):
        apply(world)
    assert policy(world)["state"] == "active"


def test_wrong_versionwake_address_fails_closed_without_policy_transition(sim_world):
    world = sim_world
    propose_review(world)
    register_policy(world, versionwake=world["addresses"]["missing_registry"])
    with pytest.raises(Exception):
        apply(world)
    assert policy(world)["state"] == "active"


@pytest.mark.parametrize("mode", ["pending", "cancelled"])
def test_pending_or_cancelled_notice_cannot_transition_policy(sim_world, mode):
    world = sim_world
    propose_review(world, review=mode != "pending", cancel=mode == "cancelled")
    register_policy(world)
    with pytest.raises(Exception):
        apply(world)
    assert policy(world)["state"] == "active"


@pytest.mark.parametrize("diagnostic_subtype", ["deprecation", "sunset"])
def test_lifecycle_subtypes_have_the_same_downstream_policy_consequence(sim_world, diagnostic_subtype):
    world = sim_world
    engine = world["engine"]
    live_baseline_url = "https://baseline.example.org/release/live.txt"
    live_notice_url = "https://notices.example.net/release/live.txt"
    live_baseline = (
        b"Controlled Versionwake lifecycle fixture VWK-LIVE-001. "
        b"Example Widget SDK version 1.0 supports the GET /v1/status endpoint."
    )
    live_notice = (
        b"Controlled Versionwake lifecycle fixture VWK-LIVE-001. "
        b"Example Widget SDK version 1.0 deprecates GET /v1/status and schedules its removal for 2025-01-01."
    )
    notice_id = "live-lifecycle-" + diagnostic_subtype
    engine.call_method(
        world["versionwake"],
        "submit_notice",
        [notice_id, SUBJECT, VERSION, live_baseline_url, digest(live_baseline), live_notice_url, digest(live_notice), "Pinned notice says deprecation with a scheduled removal date."],
        sender=world["proposer"],
    )
    engine.vm.mock_web(r"baseline\.example\.org/release/live\.txt", {"status": 200, "body": live_baseline})
    engine.vm.mock_web(r"notices\.example\.net/release/live\.txt", {"status": 200, "body": live_notice})
    engine.vm.mock_llm(
        r"Return a JSON object with exactly these keys",
        json.dumps({
            "target_match": "yes",
            "change_kind": diagnostic_subtype,
            "confidence": 91,
            "rationale": "The pinned endpoint is described as deprecated and scheduled for removal.",
        }),
    )
    engine.call_method(
        world["versionwake"], "review_notice", [notice_id, world["addresses"]["proposer"]], sender=world["proposer"]
    )
    row = engine.call_method(
        world["versionwake"], "get_notice", [notice_id, world["addresses"]["proposer"]], sender=world["proposer"]
    )
    assert row["status"] == "confirmed"
    assert row["change_kind"] == diagnostic_subtype
    assert row["consensus_class"] == "lifecycle_material"

    register_policy(world, policy_id="lifecycle-" + diagnostic_subtype)
    apply(world, policy_id="lifecycle-" + diagnostic_subtype, notice_id=notice_id)
    result = policy(world, policy_id="lifecycle-" + diagnostic_subtype)
    assert result["state"] == "review_required"
    assert result["last_change_kind"] == diagnostic_subtype
