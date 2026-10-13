"""Assistant availability use case (T-061, RF-7/RNF-1).

Probes the assistant through its `ping` contract (the reference
`OllamaClient` already performs the single transparent retry of RNF-3 and only
reports available when the configured model is loaded) and reduces the result
to the two states the platform exposes: `OK` or `UNAVAILABLE`. It is the
shared probe behind `GET /capture/assistant-status` and the first gate of the
refinement queue (plan §4.4 `ASISTENTE_DISPONIBLE`).
"""

from shared.contracts.assistant_client import AssistantClient


def check_availability(assistant: AssistantClient) -> dict:
    """Returns `{"status": "OK" | "UNAVAILABLE"}` for the assistant."""
    return {"status": "OK" if assistant.ping() else "UNAVAILABLE"}
