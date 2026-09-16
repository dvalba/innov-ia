"""Stdlib-only password utility tests (T-003, decision D10)."""

from shared.utils.password import generate_temp_password, hash_password, verify_password


def test_hash_and_successful_verification() -> None:
    hashed = hash_password("secure-password")
    assert verify_password("secure-password", hashed) is True
    assert hashed != "secure-password"


def test_verification_with_wrong_password() -> None:
    hashed = hash_password("secure-password")
    assert verify_password("other-password", hashed) is False


def test_hash_is_not_deterministic_due_to_salt() -> None:
    assert hash_password("password") != hash_password("password")


def test_verification_rejects_malformed_hash() -> None:
    assert verify_password("anything", "no-prefix") is False
    assert verify_password("anything", "innov$") is False
    assert verify_password("anything", "innov$salto$") is False


def test_temp_password_usable_and_non_trivial() -> None:
    temporary = generate_temp_password()
    assert len(temporary) >= 12
    assert temporary.isalnum() or any(c in temporary for c in "!@#_-")
    hashed = hash_password(temporary)
    assert verify_password(temporary, hashed) is True
    assert temporary != generate_temp_password()
