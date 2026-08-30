"""Unit tests for the evidence layer (web/RAG conversion + merging).

No external APIs: fake web results, hand-built RAG chunks, and in-memory
Qdrant + FakeEmbeddings are used throughout.
"""
from __future__ import annotations

import uuid

import pytest
from langchain_core.embeddings import FakeEmbeddings
from qdrant_client import QdrantClient

from backend.app.agents.evidence import (
    DEFAULT_MAX_EVIDENCE_ITEMS,
    merge_evidence,
    rag_chunk_to_evidence,
    retrieve_rag_evidence,
    web_results_to_evidence,
)
from backend.app.rag.schemas import Chunk
from backend.app.rag.vectorstore import (
    RetrievedChunk,
    get_vector_store,
    index_chunks,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def web_result(title="T", url="https://example.com", content="some content", score=0.8):
    return {"title": title, "url": url, "content": content, "score": score}


def make_rag_chunk(
    text="chunk text",
    score=0.87,
    document_id="doc-1",
    source_name="report.pdf",
    page_number=2,
    chunk_index=3,
):
    return RetrievedChunk(
        text=text,
        score=score,
        document_id=document_id,
        source_name=source_name,
        source_type="pdf",
        chunk_id=str(uuid.uuid4()),
        chunk_index=chunk_index,
        total_chunks=10,
        page_number=page_number,
    )


def make_store_chunks(chunks: list[Chunk], collection: str = "test_evidence"):
    client = QdrantClient(":memory:")
    store = get_vector_store(
        embeddings=FakeEmbeddings(size=768), client=client, collection_name=collection
    )
    index_chunks(chunks, vector_store=store)
    return store


def make_chunks(document_id="doc-1", count=3, prefix="chunk "):
    return [
        Chunk(
            chunk_id=str(uuid.uuid4()),
            document_id=document_id,
            source_name="a.txt",
            source_type="txt",
            chunk_index=i,
            total_chunks=count,
            page_number=i + 1,
            text=f"{prefix}{i}: " + "lorem ipsum dolor sit amet. " * 10,
        )
        for i in range(count)
    ]


# ── Web conversion ───────────────────────────────────────────────────────────

def test_web_results_to_evidence_basic():
    items = web_results_to_evidence([web_result(title="Alpha", url="https://a.com", content="body", score=0.9)])
    assert len(items) == 1
    it = items[0]
    assert it["source_type"] == "web"
    assert it["text"] == "body"
    assert it["title"] == "Alpha"
    assert it["url"] == "https://a.com"
    assert it["document_id"] is None
    assert it["page"] is None
    assert it["chunk_index"] is None
    assert it["score"] == 0.9
    assert it["id"].startswith("E")


def test_web_results_to_evidence_missing_score_defaults_zero():
    items = web_results_to_evidence([{"title": "T", "url": "https://a.com", "content": "x"}])
    assert items[0]["score"] == 0.0


def test_web_results_to_evidence_skips_empty_text():
    results = [
        {"title": "T", "url": "https://a.com", "content": "   "},
        {"title": "T2", "url": "https://b.com", "content": "real content"},
    ]
    items = web_results_to_evidence(results)
    assert len(items) == 1
    assert items[0]["text"] == "real content"


def test_web_results_to_evidence_skips_non_dict():
    items = web_results_to_evidence(["not a dict", 42, web_result(content="ok")])
    assert len(items) == 1
    assert items[0]["text"] == "ok"


def test_web_results_to_evidence_deterministic_ids():
    a = web_results_to_evidence([web_result()])
    b = web_results_to_evidence([web_result()])
    assert a[0]["id"] == b[0]["id"]


# ── RAG conversion ───────────────────────────────────────────────────────────

def test_rag_chunk_to_evidence_preserves_provenance():
    item = rag_chunk_to_evidence(make_rag_chunk())
    assert item["source_type"] == "rag"
    assert item["text"] == "chunk text"
    assert item["title"] == "report.pdf"  # source_name -> title
    assert item["url"] is None
    assert item["document_id"] == "doc-1"
    assert item["page"] == 2  # page_number -> page
    assert item["chunk_index"] == 3
    assert item["score"] == 0.87


def test_rag_chunk_to_evidence_deterministic_id():
    a = rag_chunk_to_evidence(make_rag_chunk())
    b = rag_chunk_to_evidence(make_rag_chunk())
    assert a["id"] == b["id"]


# ── RAG retrieval helper ─────────────────────────────────────────────────────

def test_retrieve_rag_evidence_blank_query_raises():
    with pytest.raises(ValueError, match="query"):
        retrieve_rag_evidence("   ")


def test_retrieve_rag_evidence_returns_empty_when_no_results():
    store = make_store_chunks([])
    assert retrieve_rag_evidence("anything", vector_store=store, score_threshold=-1.0) == []


def test_retrieve_rag_evidence_returns_items_with_provenance():
    store = make_store_chunks(make_chunks(document_id="doc-1", count=3))
    items = retrieve_rag_evidence(
        "lorem", vector_store=store, top_k=10, score_threshold=-1.0
    )
    assert len(items) == 3
    for it in items:
        assert it["source_type"] == "rag"
        assert it["document_id"] == "doc-1"
        assert it["title"] == "a.txt"
        assert it["page"] in {1, 2, 3}
        assert it["chunk_index"] in {0, 1, 2}


def test_retrieve_rag_evidence_respects_top_k():
    store = make_store_chunks(make_chunks(count=5))
    items = retrieve_rag_evidence("lorem", vector_store=store, top_k=2, score_threshold=-1.0)
    assert len(items) == 2


def test_retrieve_rag_evidence_respects_document_id_filter():
    store = make_store_chunks(make_chunks(document_id="doc-1", count=2))
    index_chunks(make_chunks(document_id="doc-2", count=2), vector_store=store)
    items = retrieve_rag_evidence(
        "lorem", vector_store=store, top_k=10, score_threshold=-1.0, document_id="doc-2"
    )
    assert len(items) == 2
    assert all(it["document_id"] == "doc-2" for it in items)


# ── Merging ──────────────────────────────────────────────────────────────────

def test_merge_combines_web_and_rag():
    web = web_results_to_evidence([web_result(title="A", url="https://a.com", content="web text")])
    rag = [rag_chunk_to_evidence(make_rag_chunk())]
    merged = merge_evidence(web, rag)
    assert len(merged) == 2
    assert {it["source_type"] for it in merged} == {"web", "rag"}


def test_merge_removes_exact_duplicates():
    web = web_results_to_evidence([web_result(), web_result()])  # identical -> same id
    merged = merge_evidence(web, [])
    assert len(merged) == 1


def test_merge_does_not_remove_similar_text_chunks():
    # Two different chunks (different provenance) with identical text.
    rag = [
        rag_chunk_to_evidence(make_rag_chunk(text="same words here", document_id="doc-1", chunk_index=0)),
        rag_chunk_to_evidence(make_rag_chunk(text="same words here", document_id="doc-2", chunk_index=0)),
    ]
    merged = merge_evidence([], rag)
    assert len(merged) == 2


def test_merge_assigns_deterministic_ids_when_missing():
    items = merge_evidence(
        [{"source_type": "web", "text": "hello", "title": "T", "url": "https://a.com", "score": 0.5}],
        [],
    )
    assert items[0]["id"].startswith("E")
    again = merge_evidence(
        [{"source_type": "web", "text": "hello", "title": "T", "url": "https://a.com", "score": 0.5}],
        [],
    )
    assert items[0]["id"] == again[0]["id"]


def test_merge_deterministic_ordering():
    web = web_results_to_evidence(
        [web_result(url="https://a.com", content="aa", score=0.5), web_result(url="https://b.com", content="bb", score=0.9)]
    )
    first = merge_evidence(web, [])
    second = merge_evidence(list(reversed(web)), [])
    assert [it["url"] for it in first] == [it["url"] for it in second]


def test_merge_sorted_by_score_descending():
    web = web_results_to_evidence(
        [web_result(url="https://low.com", content="low", score=0.2), web_result(url="https://high.com", content="high", score=0.9)]
    )
    merged = merge_evidence(web, [])
    assert [it["url"] for it in merged] == ["https://high.com", "https://low.com"]


def test_merge_renumbers_ids_readably():
    web = web_results_to_evidence([
        web_result(url="https://high.com", content="high", score=0.9),
        web_result(url="https://low.com", content="low", score=0.2),
    ])
    merged = merge_evidence(web, [])
    assert [it["id"] for it in merged] == ["E1", "E2"]
    assert all(it["id"].startswith("E") for it in merged)


def test_merge_max_items_limit():
    web = web_results_to_evidence([web_result(url=f"https://{i}.com", content=f"c{i}", score=i) for i in range(5)])
    merged = merge_evidence(web, [], max_items=2)
    assert len(merged) == 2


def test_merge_default_limit_applies():
    web = web_results_to_evidence([web_result(url=f"https://{i}.com", content=f"c{i}", score=i) for i in range(30)])
    merged = merge_evidence(web, [])
    assert len(merged) == DEFAULT_MAX_EVIDENCE_ITEMS


def test_merge_web_only():
    web = web_results_to_evidence([web_result(), web_result(title="B", url="https://b.com", content="two")])
    merged = merge_evidence(web, None)
    assert len(merged) == 2
    assert all(it["source_type"] == "web" for it in merged)


def test_merge_rag_only():
    rag = [rag_chunk_to_evidence(make_rag_chunk()), rag_chunk_to_evidence(make_rag_chunk(document_id="doc-2"))]
    merged = merge_evidence(None, rag)
    assert len(merged) == 2
    assert all(it["source_type"] == "rag" for it in merged)


def test_merge_empty_inputs():
    assert merge_evidence([], []) == []
    assert merge_evidence(None, None) == []


def test_merge_skips_malformed_entries():
    merged = merge_evidence(
        ["not a dict", {"source_type": "web", "text": "   ", "title": "empty"}],
        [],
    )
    assert merged == []


def test_merge_preserves_provenance_through_round_trip():
    rag = [rag_chunk_to_evidence(make_rag_chunk(document_id="doc-9", chunk_index=4, page_number=5))]
    merged = merge_evidence([], rag)
    it = merged[0]
    assert it["document_id"] == "doc-9"
    assert it["chunk_index"] == 4
    assert it["page"] == 5


def test_merge_negative_max_items_raises():
    with pytest.raises(ValueError, match="max_items"):
        merge_evidence([web_result()], [], max_items=0)
