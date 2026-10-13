"""Shared assistant client contract (T-024, plan §5).

Resolves the same coupling the `IdeaLedger` contract resolves for ideas
(plan §1.2, coupling note): the `ideas` feature orchestrates the AI
improvement (`improve_idea`) without importing the `assistant` feature —
it depends only on this Protocol, injected via dependency composition.

The reference implementation is `features.assistant.infrastructure.ollama_client`
(`OllamaClient`, T-059); the test double is `tests.conftest.OllamaMock`.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class AssistantClient(Protocol):
    """Availability probe + generation, consumed by the AI use cases.

    `ping` returns `False` after the transparent retry (RNF-3, case 3)
    instead of raising; available also means the configured model is loaded,
    not only that the service answers. `generate` raises
    `AssistantUnavailable` when the second attempt also fails ("fallo de IA",
    spec case 14).
    """

    def ping(self) -> bool:
        """Probes availability; `False` when the service is down or the model
        is not loaded."""
        ...

    def generate(self, prompt: str) -> str:
        """Generates a reply; raises `AssistantUnavailable` after the retry."""
        ...
