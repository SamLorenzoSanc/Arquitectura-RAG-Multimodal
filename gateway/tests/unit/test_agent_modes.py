from services.agent_modes import (
    agent_mode_to_rag_mode,
    normalize_agent_mode,
    resolve_chat_modes,
)

pytestmark = __import__("pytest").mark.unit


def test_normalize_agent_mode_aliases():
    assert normalize_agent_mode("agent") == "agent"
    assert normalize_agent_mode("plan") == "plan"
    assert normalize_agent_mode("debug") == "debug"
    assert normalize_agent_mode("multitask") == "multitask"
    assert normalize_agent_mode("compare") == "multitask"
    assert normalize_agent_mode("agentic") == "agent"


def test_resolve_prefers_agent_mode_over_rag_mode():
    resolved = resolve_chat_modes(agent_mode="plan", rag_mode="compare")
    assert resolved["agent_mode"] == "plan"
    assert resolved["rag_mode"] == "agentic"
    assert resolved["plan_only_style"] is True


def test_multitask_maps_to_compare():
    assert agent_mode_to_rag_mode("multitask") == "compare"
    resolved = resolve_chat_modes(agent_mode="debug")
    assert resolved["debug"] is True
    assert resolved["rag_mode"] == "agentic"
