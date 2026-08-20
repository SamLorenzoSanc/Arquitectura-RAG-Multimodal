import pytest

from services.agent_graph import (
    compile_agentic_graph,
    heuristic_grade,
    needs_document_grade,
    parse_binary_grade,
    route_after_retrieve,
    route_on_plan,
)

pytestmark = pytest.mark.unit


def test_parse_binary_grade_reads_json_and_fences():
    assert parse_binary_grade('{"binary_score":"yes"}') == "yes"
    assert parse_binary_grade("```json\n{\"binary_score\": \"no\"}\n```") == "no"
    assert parse_binary_grade("no es json") is None


def test_route_on_plan_skips_retrieval_without_tools():
    assert route_on_plan({"plan": []}) == "generate_answer"
    assert route_on_plan({"plan": [{"tool": "search_knowledge_base"}]}) == "retrieve"


def test_route_after_retrieve_rewrites_until_cap(monkeypatch):
    monkeypatch.setattr("services.agent_graph.MAX_REWRITES", 1)
    assert (
        route_after_retrieve({"grade": "no", "rewrite_count": 0}) == "rewrite_question"
    )
    assert (
        route_after_retrieve({"grade": "no", "rewrite_count": 1}) == "generate_answer"
    )
    assert route_after_retrieve({"grade": "yes", "rewrite_count": 0}) == "generate_answer"


def test_heuristic_grade_uses_chunk_count():
    assert heuristic_grade(3, "") == "yes"
    assert heuristic_grade(0, "Sin fragmentos relevantes.") == "no"


def test_route_after_retrieve_fast_path_does_not_loop(monkeypatch):
    monkeypatch.setattr("services.agent_graph.MAX_REWRITES", 0)
    assert (
        route_after_retrieve({"grade": "no", "rewrite_count": 0}) == "generate_answer"
    )


def test_sql_only_plan_does_not_need_document_grade():
    assert needs_document_grade([{"tool": "query_operational_sql"}]) is False
    assert needs_document_grade([{"tool": "search_knowledge_base"}]) is True


@pytest.mark.asyncio
async def test_compiled_graph_answers_directly_without_retrieve():
    class Fake:
        async def graph_generate_query_or_respond(self, state):
            return {"plan": [], "intent": "chitchat"}

        async def graph_retrieve(self, state):
            raise AssertionError("no debía recuperar")

        async def graph_rewrite_question(self, state):
            raise AssertionError("no debía reescribir")

        async def graph_generate_answer(self, state):
            return {"answer": "Hola, ¿en qué te ayudo?"}

    out = await compile_agentic_graph(Fake()).ainvoke(
        {"question": "hola", "model": "x", "tenant_id": "t"}
    )
    assert "Hola" in out["answer"]


@pytest.mark.asyncio
async def test_compiled_graph_rewrites_when_grade_is_no(monkeypatch):
    monkeypatch.setattr("services.agent_graph.MAX_REWRITES", 1)
    calls = {"retrieve": 0, "rewrite": 0}

    class Fake:
        async def graph_generate_query_or_respond(self, state):
            return {
                "plan": [{"tool": "search_knowledge_base"}],
                "intent": "lookup",
                "active_question": state.get("active_question") or state["question"],
            }

        async def graph_retrieve(self, state):
            calls["retrieve"] += 1
            return {
                "grade": "no" if calls["retrieve"] == 1 else "yes",
                "tool_blocks": ["ctx"],
                "chunks": [],
                "trace": [],
            }

        async def graph_rewrite_question(self, state):
            calls["rewrite"] += 1
            return {
                "active_question": "tipos de ayudas POSEI al plátano",
                "rewrite_count": 1,
                "plan": [],
            }

        async def graph_generate_answer(self, state):
            return {"answer": "anclado al corpus"}

    out = await compile_agentic_graph(Fake()).ainvoke(
        {
            "question": "POSEI",
            "model": "x",
            "tenant_id": "t",
            "rewrite_count": 0,
            "plan": [],
        }
    )
    assert calls["rewrite"] == 1
    assert calls["retrieve"] == 2
    assert out["answer"] == "anclado al corpus"
