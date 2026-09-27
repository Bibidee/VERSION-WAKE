GUARD_CONTRACT = "contracts/version_guard.py"
DIRECT_MODE_GENVM_VERSION = "v0.2.12"


def address_hex(value):
    return "0x" + value.hex()


def as_address(value):
    from genlayer.py.types import Address

    return Address(value)


def test_policy_registration_is_owner_scoped_and_trust_binding_is_explicit(direct_vm, direct_deploy, direct_alice, direct_bob, direct_charlie):
    direct_vm.sender = direct_alice
    guard = direct_deploy(GUARD_CONTRACT, sdk_version=DIRECT_MODE_GENVM_VERSION)
    guard.register_policy("widget-1", "example/widget-sdk", "1.0", as_address(direct_bob), as_address(direct_charlie))

    row = guard.get_policy("widget-1", as_address(direct_alice))
    assert row["owner"].lower() == address_hex(direct_alice).lower()
    assert row["subject"] == "example/widget-sdk"
    assert row["pinned_version"] == "1.0"
    assert row["versionwake_address"].lower() == address_hex(direct_bob).lower()
    assert row["trusted_proposer"].lower() == address_hex(direct_charlie).lower()
    assert row["state"] == "active"
    assert guard.get_policy_count(as_address(direct_alice)) == 1

    with direct_vm.prank(direct_bob):
        guard.register_policy("widget-1", "example/widget-sdk", "1.0", as_address(direct_bob), as_address(direct_charlie))
        assert guard.get_policy("widget-1", as_address(direct_bob))["state"] == "active"
        assert guard.get_policy_count(as_address(direct_bob)) == 1


def test_policy_duplicate_capacity_zero_addresses_and_bad_scope_are_rejected(direct_vm, direct_deploy, direct_alice, direct_bob, direct_charlie):
    direct_vm.sender = direct_alice
    guard = direct_deploy(GUARD_CONTRACT, sdk_version=DIRECT_MODE_GENVM_VERSION)
    guard.register_policy("widget-1", "example/widget-sdk", "1.0", as_address(direct_bob), as_address(direct_charlie))
    with direct_vm.expect_revert("Policy already exists"):
        guard.register_policy("widget-1", "example/other", "2.0", as_address(direct_bob), as_address(direct_charlie))
    with direct_vm.expect_revert("Zero Versionwake address"):
        guard.register_policy("widget-zero", "example/widget-sdk", "1.0", as_address(b"\x00" * 20), as_address(direct_charlie))
    with direct_vm.expect_revert("Zero trusted proposer"):
        guard.register_policy("widget-zero-trust", "example/widget-sdk", "1.0", as_address(direct_bob), as_address(b"\x00" * 20))
    with direct_vm.expect_revert("Invalid subject"):
        guard.register_policy("widget-empty", "  ", "1.0", as_address(direct_bob), as_address(direct_charlie))
    with direct_vm.expect_revert("Policy not found"):
        guard.get_policy("widget-1", as_address(direct_bob))


def test_policy_owner_lifetime_capacity_is_bounded_without_global_owner_exhaustion(direct_vm, direct_deploy, direct_alice, direct_bob, direct_charlie):
    direct_vm.sender = direct_alice
    guard = direct_deploy(GUARD_CONTRACT, sdk_version=DIRECT_MODE_GENVM_VERSION)
    for index in range(64):
        guard.register_policy(f"widget-{index}", "example/widget-sdk", "1.0", as_address(direct_bob), as_address(direct_charlie))
    assert guard.get_policy_count(as_address(direct_alice)) == 64
    with direct_vm.expect_revert("owner capacity reached"):
        guard.register_policy("widget-overflow", "example/widget-sdk", "1.0", as_address(direct_bob), as_address(direct_charlie))

    with direct_vm.prank(direct_bob):
        guard.register_policy("independent-owner", "example/widget-sdk", "1.0", as_address(direct_bob), as_address(direct_charlie))
    assert guard.get_policy_count(as_address(direct_bob)) == 1


def test_versionguard_info_is_explicit_and_narrow(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    guard = direct_deploy(GUARD_CONTRACT, sdk_version=DIRECT_MODE_GENVM_VERSION)
    info = guard.get_info()
    assert info["name"] == "VersionGuard"
    assert info["version"] == "0.1.0"
    assert info["max_policies_per_owner_lifetime"] == 64
    assert info["states"] == ["active", "review_required", "migration_required"]
