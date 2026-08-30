"""Modos de agente estilo Cursor: Agent, Plan, Debug, Multitask.

Mapean a la orquestación RAG existente sin romper hybrid/agentic/compare.
"""

from __future__ import annotations

from typing import Any, Literal

AgentMode = Literal["agent", "plan", "debug", "multitask"]
RagMode = Literal["hybrid", "agentic", "compare"]

AGENT_MODE_LABELS: dict[str, str] = {
    "agent": "Agent — ejecuta herramientas y responde",
    "plan": "Plan — diseña el enfoque antes de responder",
    "debug": "Debug — grade, rewrite y traza completa",
    "multitask": "Multitask — híbrido y agéntico en paralelo",
}


def normalize_agent_mode(value: str | None) -> AgentMode:
    raw = (value or "agent").strip().lower()
    if raw in {"agent", "plan", "debug", "multitask"}:
        return raw  # type: ignore[return-value]
    # Compatibilidad con rag_mode antiguo
    if raw == "compare":
        return "multitask"
    if raw == "hybrid":
        return "agent"
    if raw == "agentic":
        return "agent"
    return "agent"


def agent_mode_to_rag_mode(mode: AgentMode) -> RagMode:
    if mode == "multitask":
        return "compare"
    return "agentic"


def resolve_chat_modes(
    *,
    agent_mode: str | None = None,
    rag_mode: str | None = None,
) -> dict[str, Any]:
    """Unifica agent_mode (nuevo) y rag_mode (legacy) en un contrato único."""
    if agent_mode:
        mode = normalize_agent_mode(agent_mode)
    elif rag_mode:
        mode = normalize_agent_mode(rag_mode)
    else:
        mode = "agent"
    return {
        "agent_mode": mode,
        "rag_mode": agent_mode_to_rag_mode(mode),
        "label": AGENT_MODE_LABELS[mode],
        "debug": mode == "debug",
        "plan_only_style": mode == "plan",
        "multitask": mode == "multitask",
    }
