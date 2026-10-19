"""Ideas domain: field completeness and contact-format rules (T-017, RNF-5, case 12).

Pure domain rules over the dict of the 6 idea fields (schema §2.2). They are
the single source of "the idea is complete" that capture (RF-6/RF-7), manual
forms and versions (RF-8/RF-13) share, so no idea is ever registered with an
empty or omitted field (RNF-5).
"""

import re

from shared.contracts.idea_ledger import IDEA_FIELDS

# Scalar fields of the 6 that must hold a non-empty text (schema §2.2).
_TEXT_FIELDS: tuple[str, ...] = (
    "title",
    "description",
    "problem",
    "expectedBenefit",
    "strategicAlignment",
)

# Sub-parts of the object field (schema §2.2).
_PROPOSER_PARTS: tuple[str, ...] = ("name", "area", "contact")

# Case 12: the contact is an e-mail or a phone number, never empty.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_CHARS_RE = re.compile(r"[\s\-().]+")


def _is_blank(value: object) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def contacto_valido(contact: object) -> bool:
    """True when `contact` is a well-formed e-mail or phone number (case 12).

    Phone numbers keep their digits after removing blanks, dashes, dots,
    parentheses and an optional leading `+` (7–15 digits).
    """
    if not isinstance(contact, str):
        return False
    value = contact.strip()
    if not value:
        return False
    if _EMAIL_RE.match(value):
        return True
    digits = _PHONE_CHARS_RE.sub("", value).lstrip("+")
    return digits.isdigit() and 7 <= len(digits) <= 15


def campos_incompletos(fields: dict) -> list[str]:
    """Names of the 6 fields that are missing, null or empty (RNF-5).

    The object field `proponent` is incomplete when any of its sub-parts is
    empty.
    """
    missing: list[str] = []
    for name, value in fields.items():
        if name not in IDEA_FIELDS:
            continue
        if name == "proponent":
            if not isinstance(value, dict) or any(_is_blank(value.get(part)) for part in _PROPOSER_PARTS):
                missing.append(name)
        elif _is_blank(value):
            missing.append(name)
    for name in IDEA_FIELDS:  # omitted keys are empty too
        if name not in fields:
            missing.append(name)
    return missing


def campos_completos(fields: dict) -> bool:
    """True when the idea holds all 6 non-empty fields (RNF-5)."""
    return not campos_incompletos(fields)


def validar_campos(fields: dict) -> list[str]:
    """All completeness problems of `fields`: the 6-field check (RNF-5) plus
    the proponent contact format (case 12), as a list of field names."""
    problems = campos_incompletos(fields)
    proponent = fields.get("proponent")
    contact_is_invalid = (
        isinstance(proponent, dict)
        and not _is_blank(proponent.get("contact"))
        and not contacto_valido(proponent["contact"])
    )
    if contact_is_invalid and "proponent" not in problems:
        problems.append("proponent")
    return problems
