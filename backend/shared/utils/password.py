"""Derivacion de contraseñas con solo biblioteca estandar (T-003, decision D10).

Formato del hash: `innov$<salt_hex>$<sha256(salt + clave)>`.

NOTA (plan D10): `hashlib.sha256` con salt cubre el alcance del MVP. Se deja
documentado como riesgo a reforzar en produccion (p. ej. bcrypt/argon2) si se
actualiza la politica de dependencias.
"""

import hashlib
import secrets

_SALTO_BYTES = 16
_HASH_ALGORITMO = "sha256"
_PREFIJO = "innov"


def hash_password(clave: str) -> str:
    """Deriva el hash (salt + sha256) de la clave."""
    salt = secrets.token_bytes(_SALTO_BYTES)
    derive = hashlib.new(_HASH_ALGORITMO)
    derive.update(salt)
    derive.update(clave.encode("utf-8"))
    return f"{_PREFIJO}${salt.hex()}${derive.hexdigest()}"


def verify_password(clave: str, hashed: str) -> bool:
    """Verifica la clave contra el hash; `False` ante formato inválido."""
    partes = hashed.split("$")
    if len(partes) != 3 or partes[0] != _PREFIJO:
        return False
    try:
        salt = bytes.fromhex(partes[1])
    except ValueError:
        return False
    derive = hashlib.new(_HASH_ALGORITMO)
    derive.update(salt)
    derive.update(clave.encode("utf-8"))
    return secrets.compare_digest(derive.hexdigest(), partes[2])


def generate_temp_password(length: int = 14) -> str:
    """Genera una contraseña temporal (RF-17) de alta entropia."""
    alfabeto = "abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    base = "".join(secrets.choice(alfabeto) for _ in range(length))
    return base + secrets.choice("!@#_-")
