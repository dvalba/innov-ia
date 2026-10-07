"""Shared idea contract and layering rule tests (T-008 + G10/T-034).

The `IdeaLedger` contract resolves coupling between the `assistant`/
`validation` features and `ideas` (plan §1.2 coupling note). G10/T-034 adds a
documented exception: the spec mandates the `validation` feature to reuse
`ideas`' `approve_idea`/`reject_idea` (preserving the audit trail and the
emission points), so `validation` may import ONLY `ideas`. The `assistant`
feature stays fully isolated, and neither may import `auth`, `capture`,
`users` or `notifications`.
"""

import inspect
import pathlib

BACKEND_ROOT = pathlib.Path(__file__).resolve().parents[3]
PROTECTED = ("assistant", "validation")

# Per-feature allow-list of cross-feature imports (G10/T-034 mandates
# `validation` reusing the `ideas` publication use cases). Empty for the
# `assistant`, which remains fully isolated.
ALLOWED_FEATURE_IMPORTS: dict[str, frozenset[str]] = {
    "assistant": frozenset(),
    "validation": frozenset({"ideas"}),
}


def test_contract_exposed_in_shared() -> None:
    from shared.contracts.idea_ledger import IdeaLedger

    expected = {"get", "list_by_state", "list_by_origin", "save_current_fields", "get_version"}
    defined = {name for name, _ in inspect.getmembers(IdeaLedger, predicate=inspect.isfunction)}
    assert expected.issubset(defined)


def test_contract_does_not_import_features() -> None:
    text = (BACKEND_ROOT / "shared" / "contracts" / "idea_ledger.py").read_text(encoding="utf-8")
    assert "from features" not in text
    assert "import features" not in text


def test_protected_features_do_not_import_external_features() -> None:
    """Enforces that `assistant`/`validation` only import allowed features.

    `assistant`: no cross-feature import at all.
    `validation`: only `features.ideas` (G10/T-034 mandated reuse).
    Both: never `auth`, `capture`, `users`, `notifications`.
    """
    violations = []
    for protected in PROTECTED:
        allowed = ALLOWED_FEATURE_IMPORTS[protected]
        root = BACKEND_ROOT / "features" / protected
        for path in root.rglob("*.py"):
            if path.name == "__init__.py":
                continue
            content = path.read_text(encoding="utf-8")
            for line in content.splitlines():
                stripped = line.strip()
                if not stripped.startswith(("import ", "from ")):
                    continue
                for other in ("auth", "capture", "ideas", "users", "notifications"):
                    if f"features.{other}" in stripped and other not in allowed:
                        violations.append(f"{protected}: {path.name} -> {stripped}")
    assert not violations, "\n".join(violations)
