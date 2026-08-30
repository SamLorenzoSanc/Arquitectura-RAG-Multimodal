from rag.domain.entities import RetrievedChunk
from rag.domain.related import (
    generate_related_questions,
    select_related_neighbors,
    topic_from_chunk,
)


def _chunk(cid: str, doc: str, source: str, headline: str = "") -> RetrievedChunk:
    return RetrievedChunk(
        page_content=f"Texto de {headline or source}",
        metadata={
            "chunk_id": cid,
            "document_id": doc,
            "source": source,
            "headline": headline,
            "distance": 0.1,
            "retrieval_source": "dense",
        },
    )


def test_topic_from_headline():
    chunk = _chunk("c1", "d1", "riego_tomate.pdf", "Riego de tomate")
    assert topic_from_chunk(chunk) == "Riego de tomate"


def test_knn_excludes_current_document_like_titan():
    used = [_chunk("c1", "doc-a", "tomate.pdf", "Tomate")]
    neighbors = [
        _chunk("c1", "doc-a", "tomate.pdf", "Tomate"),
        _chunk("c2", "doc-b", "pimiento.pdf", "Pimiento en invernadero"),
        _chunk("c3", "doc-c", "papa.pdf", "Papa de medianías"),
    ]
    picked = select_related_neighbors(
        neighbors,
        exclude_chunk_ids={"c1"},
        exclude_document_ids={"doc-a"},
        limit=2,
    )
    assert [c.metadata["document_id"] for c in picked] == ["doc-b", "doc-c"]


def test_related_questions_use_knn_neighbors_not_answer_chunks():
    used = [_chunk("c1", "doc-a", "tomate.pdf", "Cultivo de tomate")]
    neighbors = [
        _chunk("c1", "doc-a", "tomate.pdf", "Cultivo de tomate"),
        _chunk("c9", "doc-z", "platanera.md", "Deshijado de platanera"),
    ]
    questions = generate_related_questions(
        "¿Cómo riego el tomate?",
        used,
        max_questions=1,
        neighbors=neighbors,
    )
    assert len(questions) == 1
    assert "platanera" in questions[0].lower()
    assert "tomate" not in questions[0].lower()
