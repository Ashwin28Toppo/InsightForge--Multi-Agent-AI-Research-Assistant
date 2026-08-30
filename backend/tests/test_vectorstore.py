"""Unit tests for the Qdrant vector store.

All tests use an in-memory Qdrant client and FakeEmbeddings — no network,
no Google/Groq/Tavily/external Qdrant.
"""
from __future__ import annotations

import threading
import uuid

import pytest
from langchain_core.embeddings import FakeEmbeddings
from qdrant_client import QdrantClient

from backend.app.rag.schemas import Chunk
from backend.app.rag.vectorstore import (
    get_qdrant_client,
    get_vector_store,
    index_chunks,
    search_knowledge_base,
)

COLLECTION = "test_coll"


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_chunks(
    document_id: str = "doc-1",
    source_name: str = "notes.txt",
    source_type: str = "txt",
    count: int = 3,
) -> list[Chunk]:
    return [
        Chunk(
            chunk_id=str(uuid.uuid4()),
            document_id=document_id,
            source_name=source_name,
            source_type=source_type,
            chunk_index=i,
            total_chunks=count,
            page_number=None,
            text=f"chunk {i}: " + "lorem ipsum dolor sit amet. " * 10,
        )
        for i in range(count)
    ]


def make_store(client: QdrantClient, collection_name: str = COLLECTION):
    return get_vector_store(
        embeddings=FakeEmbeddings(size=768),
        client=client,
        collection_name=collection_name,
    )


def search_all(store, top_k: int = 10):
    return search_knowledge_base("query", vector_store=store, top_k=top_k, score_threshold=-1.0)


# ── Collection lifecycle ─────────────────────────────────────────────────────

def test_collection_is_created():
    client = QdrantClient(":memory:")
    make_store(client)
    assert client.collection_exists(COLLECTION)


def test_collection_is_reused_without_destroying_data():
    client = QdrantClient(":memory:")
    store = make_store(client)
    index_chunks(make_chunks(count=2), vector_store=store)

    # Building a second store on the same collection must reuse it.
    store2 = make_store(client)
    assert client.collection_exists(COLLECTION)
    assert len(search_all(store2)) == 2


def test_vector_store_with_fake_embeddings_requires_no_api_key():
    client = QdrantClient(":memory:")
    store = get_vector_store(
        embeddings=FakeEmbeddings(size=768),
        client=client,
        collection_name="no_key_coll",
    )
    assert client.collection_exists("no_key_coll")


# ── Indexing ─────────────────────────────────────────────────────────────────

def test_index_returns_count_and_metadata_preserved():
    client = QdrantClient(":memory:")
    store = make_store(client)
    chunks = make_chunks(document_id="doc-1", source_name="notes.txt", source_type="txt", count=3)

    inserted = index_chunks(chunks, vector_store=store)
    assert inserted == 3

    results = search_all(store)
    assert len(results) == 3
    assert {r.text for r in results} == {c.text for c in chunks}

    r = results[0]
    assert r.document_id == "doc-1"
    assert r.source_name == "notes.txt"
    assert r.source_type == "txt"
    assert r.chunk_index in {0, 1, 2}
    assert r.total_chunks == 3
    assert r.page_number is None
    assert r.chunk_id in {c.chunk_id for c in chunks}
    assert isinstance(r.score, (int, float))


def test_empty_chunks_are_ignored():
    client = QdrantClient(":memory:")
    store = make_store(client)
    empty = Chunk(
        chunk_id=str(uuid.uuid4()), document_id="doc-x", source_name="x.txt",
        source_type="txt", chunk_index=0, total_chunks=2, page_number=None, text="   \n\n",
    )
    assert index_chunks([empty], vector_store=store) == 0
    assert search_all(store) == []

    # Mixed: valid chunks are indexed, empty ones are skipped.
    valid = make_chunks(document_id="doc-y", count=2)
    assert index_chunks([valid[0], empty, valid[1]], vector_store=store) == 2
    assert len(search_all(store)) == 2


def test_empty_input_handled_without_creating_collection():
    client = QdrantClient(":memory:")
    assert (
        index_chunks(
            [],
            client=client,
            embeddings=FakeEmbeddings(size=768),
            collection_name="never_created",
        )
        == 0
    )
    assert not client.collection_exists("never_created")


def test_reindexing_same_document_does_not_create_duplicates():
    client = QdrantClient(":memory:")
    store = make_store(client)
    chunks = make_chunks(document_id="doc-1", count=3)

    index_chunks(chunks, vector_store=store)
    index_chunks(chunks, vector_store=store)
    index_chunks(chunks, vector_store=store)

    assert len(search_all(store)) == 3


def test_reindexing_one_document_does_not_affect_another():
    client = QdrantClient(":memory:")
    store = make_store(client)
    index_chunks(make_chunks(document_id="doc-1", count=2), vector_store=store)
    index_chunks(make_chunks(document_id="doc-2", count=2), vector_store=store)

    # Re-index doc-1 with a different size; doc-2 must be untouched.
    index_chunks(make_chunks(document_id="doc-1", count=3), vector_store=store)

    d1 = search_knowledge_base(
        "q", vector_store=store, top_k=10, score_threshold=-1.0, document_id="doc-1"
    )
    d2 = search_knowledge_base(
        "q", vector_store=store, top_k=10, score_threshold=-1.0, document_id="doc-2"
    )
    assert len(d1) == 3
    assert len(d2) == 2


# ── Retrieval ────────────────────────────────────────────────────────────────

def test_similarity_search_returns_results_and_respects_top_k():
    client = QdrantClient(":memory:")
    store = make_store(client)
    index_chunks(make_chunks(count=10), vector_store=store)

    results = search_knowledge_base(
        "query", vector_store=store, top_k=3, score_threshold=-1.0
    )
    assert len(results) == 3


def test_score_threshold_respected():
    client = QdrantClient(":memory:")
    store = make_store(client)
    index_chunks(make_chunks(count=5), vector_store=store)

    # Cosine similarity of random vectors is < 1.0, so a 1.0 threshold yields none.
    assert search_knowledge_base("q", vector_store=store, score_threshold=1.0) == []
    # A very permissive threshold keeps everything.
    low = search_knowledge_base("q", vector_store=store, score_threshold=-1.0)
    assert len(low) == 5


def test_results_ordered_by_relevance():
    client = QdrantClient(":memory:")
    store = make_store(client)
    index_chunks(make_chunks(count=8), vector_store=store)

    results = search_all(store)
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)


def test_multiple_documents_remain_isolated():
    client = QdrantClient(":memory:")
    store = make_store(client)
    index_chunks(make_chunks(document_id="doc-1", count=2), vector_store=store)
    index_chunks(make_chunks(document_id="doc-2", count=2), vector_store=store)

    all_results = search_all(store)
    assert len(all_results) == 4

    doc1 = search_knowledge_base(
        "q", vector_store=store, top_k=10, score_threshold=-1.0, document_id="doc-1"
    )
    assert len(doc1) == 2
    assert all(r.document_id == "doc-1" for r in doc1)


def test_empty_query_raises_value_error():
    client = QdrantClient(":memory:")
    store = make_store(client)
    with pytest.raises(ValueError, match="query"):
        search_knowledge_base("   ", vector_store=store)


def test_missing_collection_returns_empty_gracefully():
    client = QdrantClient(":memory:")
    store = make_store(client)
    index_chunks(make_chunks(count=1), vector_store=store)

    client.delete_collection(COLLECTION)
    assert search_knowledge_base("q", vector_store=store, score_threshold=-1.0) == []


# ── Client factory (Phase 2F Step 10 regression) ─────────────────────────────

def test_get_qdrant_client_is_singleton_and_race_free(tmp_path):
    """Concurrent first calls for one storage path return ONE client.

    Regression for Phase 2F Step 10: local Qdrant holds an exclusive file
    lock per storage folder, so simultaneous calls must never construct two
    clients for the same path. The old ``lru_cache`` only deduplicated
    *completed* calls, so concurrent workers both constructed a client and
    the second crashed with "already accessed by another instance".
    """
    path = str(tmp_path / "qdrant")
    created: list[QdrantClient] = []

    def _open():
        created.append(get_qdrant_client(path=path))

    threads = [threading.Thread(target=_open) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Every caller got a client (none raised) and all are the SAME instance.
    assert len(created) == 4
    assert all(c is created[0] for c in created)
    assert get_qdrant_client(path=path) is created[0]
