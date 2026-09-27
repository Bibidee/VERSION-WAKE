# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
"""VersionGuard: deterministic dependency policy reactions to Versionwake results."""

import re
from dataclasses import dataclass

from genlayer import *


VERSION = "0.1.0"
ACTIVE = "active"
REVIEW_REQUIRED = "review_required"
MIGRATION_REQUIRED = "migration_required"
MAX_POLICY_ID = 96
MAX_SUBJECT = 160
MAX_VERSION = 96
MAX_POLICIES_PER_OWNER_LIFETIME = 64
CONFIRMED = "confirmed"
MATERIAL_CHANGE_KINDS = ("breaking", "deprecation", "sunset")


@allow_storage
@dataclass
class DependencyPolicy:
    policy_id: str
    owner: Address
    subject: str
    pinned_version: str
    versionwake_address: Address
    trusted_proposer: Address
    state: str
    last_notice_id: str
    last_change_kind: str


class PolicyRegistered(gl.Event):
    def __init__(self, policy_id: str, owner: Address, subject: str, /, **blob): ...


class PolicyTransitioned(gl.Event):
    def __init__(self, policy_id: str, owner: Address, state: str, /, **blob): ...


@gl.contract_interface
class VersionwakeRegistry:
    class View:
        def get_info(self) -> dict: ...

        def get_notice(self, notice_id: str, proposer: Address) -> dict: ...

        def is_confirmed_for(self, notice_id: str, proposer: Address, subject: str, version_ref: str) -> bool: ...

    class Write:
        pass


def clean_text(value: str) -> str:
    return " ".join(str(value).replace("\x00", " ").split())


def bounded_text(value: str, label: str, limit: int) -> str:
    result = clean_text(value)
    if len(result) == 0 or len(result) > limit:
        raise gl.vm.UserError("[EXPECTED] Invalid " + label)
    return result


def valid_policy_id(value: str) -> str:
    result = str(value).strip()
    if len(result) == 0 or len(result) > MAX_POLICY_ID or not re.match(r"^[A-Za-z0-9._:-]+$", result):
        raise gl.vm.UserError("[EXPECTED] Invalid policy_id")
    return result


def canonical_address_hex(value) -> str:
    if isinstance(value, bytes):
        return "0x" + value.hex()
    return value.as_hex.lower()


def nonzero_address(value, label: str) -> str:
    address_hex = canonical_address_hex(value)
    if address_hex == "0x" + "0" * 40:
        raise gl.vm.UserError("[EXPECTED] Zero " + label)
    return address_hex


class VersionGuard(gl.Contract):
    policies: TreeMap[str, DependencyPolicy]
    policy_counts_by_owner: TreeMap[str, u256]
    applied_notice_refs: TreeMap[str, str]

    def __init__(self):
        pass

    def _policy_key(self, policy_id: str, owner: Address) -> str:
        return canonical_address_hex(owner) + "|" + policy_id

    def _require_policy(self, policy_id: str, owner: Address) -> DependencyPolicy:
        normalized_id = valid_policy_id(policy_id)
        policy = self.policies.get(self._policy_key(normalized_id, owner))
        if policy is None:
            raise gl.vm.UserError("[EXPECTED] Policy not found")
        return policy

    @gl.public.write
    def register_policy(
        self,
        policy_id: str,
        subject: str,
        pinned_version: str,
        versionwake_address: Address,
        trusted_proposer: Address,
    ) -> None:
        normalized_id = valid_policy_id(policy_id)
        owner = gl.message.sender_address
        key = self._policy_key(normalized_id, owner)
        owner_key = canonical_address_hex(owner)
        used = self.policy_counts_by_owner.get(owner_key)
        used_count = int(used) if used is not None else 0
        if self.policies.get(key) is not None:
            raise gl.vm.UserError("[EXPECTED] Policy already exists or owner capacity reached")
        if used_count >= MAX_POLICIES_PER_OWNER_LIFETIME:
            raise gl.vm.UserError("[EXPECTED] Policy already exists or owner capacity reached")
        nonzero_address(versionwake_address, "Versionwake address")
        nonzero_address(trusted_proposer, "trusted proposer")
        subject_value = bounded_text(subject, "subject", MAX_SUBJECT)
        version_value = bounded_text(pinned_version, "pinned_version", MAX_VERSION)

        self.policies[key] = DependencyPolicy(
            normalized_id,
            owner,
            subject_value,
            version_value,
            versionwake_address,
            trusted_proposer,
            ACTIVE,
            "",
            "",
        )
        self.policy_counts_by_owner[owner_key] = u256(used_count + 1)
        # Keep events within GenVM's supported positional ABI. The getter is
        # authoritative for full policy details.
        PolicyRegistered(normalized_id, owner, subject_value).emit()

    @gl.public.write
    def apply_notice(self, policy_owner: Address, policy_id: str, notice_id: str) -> None:
        normalized_notice_id = str(notice_id).strip()
        if len(normalized_notice_id) == 0 or len(normalized_notice_id) > 96 or not re.match(r"^[A-Za-z0-9._:-]+$", normalized_notice_id):
            raise gl.vm.UserError("[EXPECTED] Invalid notice_id")
        policy = self._require_policy(policy_id, policy_owner)
        policy_key = self._policy_key(policy.policy_id, policy.owner)
        notice_ref_key = policy_key + "|" + canonical_address_hex(policy.trusted_proposer) + "|" + normalized_notice_id
        if self.applied_notice_refs.get(notice_ref_key) is not None:
            raise gl.vm.UserError("[EXPECTED] Notice already applied to policy")
        if policy.state != ACTIVE:
            raise gl.vm.UserError("[EXPECTED] Policy is terminal; register the new pinned version under a new policy ID")

        registry = VersionwakeRegistry(policy.versionwake_address).view()
        info = registry.get_info()
        if not isinstance(info, dict) or info.get("name") != "Versionwake":
            raise gl.vm.UserError("[EXPECTED] Configured contract is not a Versionwake registry")
        min_confidence = info.get("minimum_confidence")
        if isinstance(min_confidence, bool) or not isinstance(min_confidence, int) or min_confidence < 0 or min_confidence > 100:
            raise gl.vm.UserError("[EXPECTED] Invalid Versionwake confidence policy")

        notice = registry.get_notice(normalized_notice_id, policy.trusted_proposer)
        if not isinstance(notice, dict):
            raise gl.vm.UserError("[EXPECTED] Invalid Versionwake notice record")
        if (
            notice.get("notice_id") != normalized_notice_id
            or str(notice.get("proposer", "")).lower() != canonical_address_hex(policy.trusted_proposer)
            or notice.get("subject") != policy.subject
            or notice.get("version_ref") != policy.pinned_version
            or notice.get("status") != CONFIRMED
            or notice.get("outcome") != CONFIRMED
            or notice.get("target_match") != "yes"
        ):
            raise gl.vm.UserError("[EXPECTED] Notice is not confirmed for this exact policy scope")
        if registry.is_confirmed_for(
            normalized_notice_id,
            policy.trusted_proposer,
            policy.subject,
            policy.pinned_version,
        ) is not True:
            raise gl.vm.UserError("[EXPECTED] Versionwake exact-scope gate rejected notice")

        change_kind = notice.get("change_kind")
        if change_kind not in MATERIAL_CHANGE_KINDS:
            raise gl.vm.UserError("[EXPECTED] Notice has no actionable material change")
        confidence = notice.get("confidence")
        if isinstance(confidence, bool) or not isinstance(confidence, int) or confidence < min_confidence or confidence > 100:
            raise gl.vm.UserError("[EXPECTED] Notice confidence is below Versionwake policy threshold")

        next_state = MIGRATION_REQUIRED if change_kind == "breaking" else REVIEW_REQUIRED
        self.applied_notice_refs[notice_ref_key] = "1"
        policy.state = next_state
        policy.last_notice_id = normalized_notice_id
        policy.last_change_kind = change_kind
        PolicyTransitioned(policy.policy_id, policy.owner, next_state).emit()

    @gl.public.view
    def get_policy(self, policy_id: str, owner: Address) -> dict:
        policy = self._require_policy(policy_id, owner)
        return {
            "policy_id": str(policy.policy_id),
            "owner": canonical_address_hex(policy.owner),
            "subject": str(policy.subject),
            "pinned_version": str(policy.pinned_version),
            "versionwake_address": canonical_address_hex(policy.versionwake_address),
            "trusted_proposer": canonical_address_hex(policy.trusted_proposer),
            "state": str(policy.state),
            "last_notice_id": str(policy.last_notice_id),
            "last_change_kind": str(policy.last_change_kind),
        }

    @gl.public.view
    def get_policy_count(self, owner: Address) -> int:
        count = self.policy_counts_by_owner.get(canonical_address_hex(owner))
        return int(count) if count is not None else 0

    @gl.public.view
    def get_info(self) -> dict:
        return {
            "name": "VersionGuard",
            "version": VERSION,
            "max_policies_per_owner_lifetime": MAX_POLICIES_PER_OWNER_LIFETIME,
            "states": [ACTIVE, REVIEW_REQUIRED, MIGRATION_REQUIRED],
        }
