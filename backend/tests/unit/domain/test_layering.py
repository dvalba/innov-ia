"""Shared idea contract and layering rule tests (T-008).

The `IdeaLedger` contract resolves coupling between the `assistant`/
`validation` features and `ideas` (plan §1.2 coupling note).
"""

import inspect
import pathlib

BACKEND_ROOT = pathlib.Path(__file__).resolve().parents[3]
PROTECTED = ("assistant", "validation")


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
    violations = []
    for protected in PROTECTED:
        root = BACKEND_ROOT / "features" / protected
        for path in root.rglob("*.py"):
            if path.name == "__init__.py":
                continue
            content = path.read_text(encoding="utf-8")
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith(("import ", "from ")):
                    for other in ("auth", "capture", "ideas", "users", "notifications"):
                        if f"features.{other}" in stripped:
                            violations.append(f"{protected}: {path.name} -> {stripped}")
    assert not violations, "\n".join(violations)
