"""Tests del contrato compartido de ideas y la regla de capas (T-008).

El contrato `IdeaLedger` resuelve el acoplamiento entre las features
`assistant`/`validation` y `ideas` (nota de acoplamiento del plan §1.2).
"""

import inspect
import pathlib

BACKEND_ROOT = pathlib.Path(__file__).resolve().parents[3]
PROTEGIDAS = ("assistant", "validation")


def test_contrato_expuesto_en_shared() -> None:
    from shared.contracts.idea_ledger import IdeaLedger

    metodos = {"obtener", "listar_por_estado", "listar_por_origen", "guardar_campos_vigentes", "obtener_version"}
    nombres = {m for m, _ in inspect.getmembers(IdeaLedger, predicate=inspect.isfunction)}
    assert metodos.issubset(nombres)


def test_contrato_no_importa_de_features() -> None:
    texto = (BACKEND_ROOT / "shared" / "contracts" / "idea_ledger.py").read_text(encoding="utf-8")
    assert "from features" not in texto
    assert "import features" not in texto


def test_protegidas_no_importan_de_features_externos() -> None:
    infracciones = []
    for protegida in PROTEGIDAS:
        raiz = BACKEND_ROOT / "features" / protegida
        for archivo in raiz.rglob("*.py"):
            if archivo.name == "__init__.py":
                continue
            contenido = archivo.read_text(encoding="utf-8")
            for linea in contenido.splitlines():
                limpio = linea.strip()
                if limpio.startswith(("import ", "from ")):
                    for otra in ("auth", "capture", "ideas", "users", "notifications"):
                        if f"features.{otra}" in limpio:
                            infracciones.append(f"{protegida}: {archivo.name} -> {limpio}")
    assert not infracciones, "\n".join(infracciones)
