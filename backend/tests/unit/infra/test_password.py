"""Tests de la utilidad de contraseñas con stdlib (T-003, decision D10)."""

from shared.utils.password import generate_temp_password, hash_password, verify_password


def test_hash_y_verificacion_correcta() -> None:
    hashed = hash_password("clave-segura")
    assert verify_password("clave-segura", hashed) is True
    assert hashed != "clave-segura"


def test_verificacion_con_clave_incorrecta() -> None:
    hashed = hash_password("clave-segura")
    assert verify_password("otra-clave", hashed) is False


def test_hash_no_es_determinista_por_salt() -> None:
    assert hash_password("clave") != hash_password("clave")


def test_verificacion_rechaza_hash_mal_formado() -> None:
    assert verify_password("cualquiera", "sin-prefijo") is False
    assert verify_password("cualquiera", "innov$") is False
    assert verify_password("cualquiera", "innov$salto$") is False


def test_contraseña_temporal_usable_y_no_trivial() -> None:
    temporal = generate_temp_password()
    assert len(temporal) >= 12
    assert temporal.isalnum() or any(c in temporal for c in "!@#_-")
    hashed = hash_password(temporal)
    assert verify_password(temporal, hashed) is True
    assert temporal != generate_temp_password()
