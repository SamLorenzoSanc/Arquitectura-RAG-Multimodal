import pytest

from catalog.adapters.inbound.documents import _chunk_overlap
from rag.adapters.outbound.pgvector import STORAGE_VECTOR_DIM, prepare_query_vectors
from services.agentic_rag_service import (
    AgenticRAGService,
    chat_retrieval_strategy,
    classify_intent,
    parse_agent_plan,
)

pytestmark = pytest.mark.unit


def test_prepare_query_vectors_pads_nomic_to_storage_dim():
    nomic = [0.1] * 768
    padded, index_query, index_dim = prepare_query_vectors(nomic, index_dim=2000)
    assert len(padded) == STORAGE_VECTOR_DIM
    assert padded[:768] == nomic
    assert padded[768:] == [0.0] * (STORAGE_VECTOR_DIM - 768)
    assert index_dim == 2000
    assert len(index_query) == 2000
    assert index_query == padded[:2000]


def test_plan_tools_lists_documents_for_inventory_questions():
    service = AgenticRAGService.__new__(AgenticRAGService)
    tools = [step["tool"] for step in service.plan_tools("¿Qué documentos hay indexados y de qué tratan?")]
    assert "list_indexed_documents" in tools


def test_plan_tools_uses_regulation_and_diagnosis_agents():
    service = AgenticRAGService.__new__(AgenticRAGService)
    pac = [step["tool"] for step in service.plan_tools("Resume la normativa PAC o POSEI del corpus.")]
    crop = [step["tool"] for step in service.plan_tools("Las hojas se están poniendo amarillas: ¿qué puede ser?")]
    assert classify_intent("Resume la normativa PAC o POSEI del corpus.") == "regulation"
    assert "search_regulations" in pac
    assert "diagnose_crop" in crop


def test_classify_intent_matches_user_question_type():
    assert classify_intent("¿Qué documentos hay indexados?") == "inventory"
    assert classify_intent("¿Cuáles son las ayudas POSEI por hectárea?") == "regulation"
    assert classify_intent("¿Qué usos autorizados tiene el glifosato según el vademécum?") == "lookup"
    assert classify_intent("Las hojas se están poniendo amarillas: ¿qué puede ser?") == "diagnostic"
    assert classify_intent("hola") == "chitchat"


def test_lookup_questions_do_not_force_diagnosis_tool():
    service = AgenticRAGService.__new__(AgenticRAGService)
    tools = [step["tool"] for step in service.plan_tools(
        "¿Qué dosis y cultivos autorizados aparecen en el vademécum de Canarias?"
    )]
    assert tools == ["search_knowledge_base"]


def test_chat_retrieval_strategy_is_full_hybrid():
    assert chat_retrieval_strategy(use_reranking=False) == "hybrid_expansion_rrf"
    assert chat_retrieval_strategy(use_reranking=True) == "hybrid_expansion_rrf_rerank"


def test_parse_agent_plan_reads_sql_and_memory_tools():
    raw = """```json
    {"reason":"combinar",
     "tools":[
       {"name":"search_knowledge_base","query":"POSEI plátano"},
       {"name":"query_operational_sql","sql":"SELECT filename FROM documents WHERE tenant_id = :tenant_id"},
       {"name":"recall_conversation","query":"plátano"}
     ]}
    ```"""
    plan = parse_agent_plan(raw)
    assert plan is not None
    assert [step["tool"] for step in plan] == [
        "search_knowledge_base",
        "query_operational_sql",
        "recall_conversation",
    ]


def test_parse_agent_plan_allows_no_tools_and_rejects_garbage():
    assert parse_agent_plan('{"reason":"saludo","tools":[]}') == []
    assert parse_agent_plan("no es json") is None


def test_plan_tools_skips_chitchat_and_uses_sql_for_notebook():
    service = AgenticRAGService.__new__(AgenticRAGService)
    assert service.plan_tools("hola") == []
    tools = [step["tool"] for step in service.plan_tools("Anota un riego en el cuaderno")]
    assert "query_operational_sql" in tools


def test_chunk_overlap_detects_shared_tail():
    previous = "texto previo " + ("solape-de-fragmentos-agricolas-" * 3)
    current = ("solape-de-fragmentos-agricolas-" * 3) + " continuación del chunk"
    assert _chunk_overlap(previous, current) >= 20
    assert _chunk_overlap("corto", "otro") == 0
