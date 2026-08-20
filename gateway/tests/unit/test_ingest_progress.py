from services.ingest_progress import clear_progress, get_progress, set_progress


def test_progress_hub_updates_and_clamps_percent():
    document_id = "doc-test"
    clear_progress(document_id)
    snap = set_progress(
        document_id,
        stage="embed",
        percent=140,
        message="Embeddings 3/8…",
        status="running",
        embedded=3,
        total=8,
    )
    assert snap["percent"] == 100
    stored = get_progress(document_id)
    assert stored is not None
    assert stored["embedded"] == 3
    clear_progress(document_id)
    assert get_progress(document_id) is None
