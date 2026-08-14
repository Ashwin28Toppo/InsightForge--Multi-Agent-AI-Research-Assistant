"""Qdrant vector store: client factory, chunk indexing, and retrieval.

Built on ``qdrant-client`` + ``langchain-qdrant``. Supports local embedded
storage (``settings.qdrant_path``) or a remote server (``settings.qdrant_url``).

Everything is dependency-injectable (client + embeddings) so tests can use
``QdrantClient(":memory:")`` and ``FakeEmbeddings`` with no network access.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable

from langchain_core.embeddings import Embeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient, models

from backend.app.core.config import settings
from backend.app.rag.embeddings import get_embeddings
from backend.app.rag.schemas import Chunk

# QdrantVectorStore stores chunk metadata under the `metadata` payload key.
_METADATA_PREFIX = "metadata."


@lru_cache(maxsize=4)
def get_qdrant_client(url: str | None = None, path: str | None = None) -> QdrantClient:
    """Build a Qdrant client: remote (URL) or local embedded (path / memory).

    Cached per (url, path) because Qdrant local mode holds an exclusive file
    lock on its storage folder — only one client per path may exist in a
    process. Tests inject their own ``QdrantClient(":memory:")`` instead.
    """
    url = url if url is not None else settings.qdrant_url
    path = path if path is not None else settings.qdrant_path
    if url:
        return QdrantClient(url=url)
    return QdrantClient(path=path)


def _ensure_collection(
    client: QdrantClient, collection_name: str, vector_size: int
) -> None:
    """Idempotent collection creation — reuse existing, never destroy data."""
    if not client.collection_exists(collection_name):
        client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=vector_size,
                distance=models.Distance.COSINE,
            ),
        )


def get_vector_store(
    embeddings: Embeddings | None = None,
    client: QdrantClient | None = None,
    collection_name: str | None = None,
    vector_size: int | None = None,
) -> QdrantVectorStore:
    """Factory returning a configured vector store (collection ensured)."""
    embeddings = embeddings or get_embeddings()
    client = client or get_qdrant_client()
    collection_name = collection_name or settings.qdrant_collection
    vector_size = vector_size or settings.embedding_dim
    _ensure_collection(client, collection_name, vector_size)
    return QdrantVectorStore(
        client=client,
        collection_name=collection_name,
        embedding=embeddings,
    )


def _chunk_metadata(chunk: Chunk) -> dict:
    """Metadata stored on each vector point (enough for future citations)."""
    return {
        "document_id": chunk.document_id,
        "source_name": chunk.source_name,
        "source_type": chunk.source_type,
        "chunk_id": chunk.chunk_id,
        "chunk_index": chunk.chunk_index,
        "total_chunks": chunk.total_chunks,
        "page_number": chunk.page_number,
    }


def _document_filter(document_id: str) -> models.Filter:
    return models.Filter(
        must=[
            models.FieldCondition(
                key=f"{_METADATA_PREFIX}document_id",
                match=models.MatchValue(value=document_id),
            )
        ]
    )


def index_chunks(
    chunks: Iterable[Chunk],
    vector_store: QdrantVectorStore | None = None,
    *,
    client: QdrantClient | None = None,
    embeddings: Embeddings | None = None,
    collection_name: str | None = None,
) -> int:
    """Index chunks into Qdrant. Idempotent per document (delete-then-insert).

    Args:
        chunks: Chunks to index (each becomes one vector point).
        vector_store: Optional pre-built store (for tests/injection).

    Returns:
        The number of chunks indexed.

    Notes:
        - Empty/whitespace-only chunks are ignored defensively.
        - Empty input returns 0 without touching the collection.
        - Re-indexing a document first deletes only that document's previous
          points, then inserts the new ones (no duplicates, no cross-document
          deletion).
    """
    valid = [c for c in chunks if c.text.strip()]
    if not valid:
        return 0

    store = vector_store or get_vector_store(
        embeddings=embeddings, client=client, collection_name=collection_name
    )
    qclient = store.client
    collection = store.collection_name

    # Group by document so re-ingestion replaces only its own points.
    by_document: dict[str, list[Chunk]] = {}
    for chunk in valid:
        by_document.setdefault(chunk.document_id, []).append(chunk)

    inserted = 0
    for document_id, doc_chunks in by_document.items():
        qclient.delete(collection, points_selector=_document_filter(document_id))
        store.add_texts(
            texts=[c.text for c in doc_chunks],
            metadatas=[_chunk_metadata(c) for c in doc_chunks],
            ids=[c.chunk_id for c in doc_chunks],
        )
        inserted += len(doc_chunks)
    return inserted


@dataclass
class RetrievedChunk:
    """Application-level search result (no Qdrant objects leaked)."""

    text: str
    score: float
    document_id: str
    source_name: str
    source_type: str
    chunk_id: str
    chunk_index: int
    total_chunks: int
    page_number: int | None


def search_knowledge_base(
    query: str,
    vector_store: QdrantVectorStore | None = None,
    *,
    top_k: int | None = None,
    score_threshold: float | None = None,
    document_id: str | None = None,
    client: QdrantClient | None = None,
    embeddings: Embeddings | None = None,
    collection_name: str | None = None,
) -> list[RetrievedChunk]:
    """Similarity search over the knowledge base, ordered by relevance.

    Args:
        query: Search text (must be non-blank).
        vector_store: Optional pre-built store (for tests/injection).
        top_k: Max results; defaults to ``settings.retrieval_top_k``.
        score_threshold: Minimum similarity; defaults to
            ``settings.retrieval_score_threshold``.
        document_id: Optional filter to scope results to one document.

    Returns:
        List of :class:`RetrievedChunk`, best match first.

    Raises:
        ValueError: if the query is empty/blank.
    """
    if not query.strip():
        raise ValueError("query must not be empty")

    store = vector_store or get_vector_store(
        embeddings=embeddings, client=client, collection_name=collection_name
    )
    top_k = top_k if top_k is not None else settings.retrieval_top_k
    threshold = (
        score_threshold
        if score_threshold is not None
        else settings.retrieval_score_threshold
    )

    # Graceful when the collection has not been created (e.g. deleted).
    if not store.client.collection_exists(store.collection_name):
        return []

    qfilter = _document_filter(document_id) if document_id else None
    results = store.similarity_search_with_score(query, k=top_k, filter=qfilter)

    retrieved: list[RetrievedChunk] = []
    for doc, score in results:
        if score < threshold:
            continue
        meta = doc.metadata
        retrieved.append(
            RetrievedChunk(
                text=doc.page_content,
                score=score,
                document_id=meta.get("document_id", ""),
                source_name=meta.get("source_name", ""),
                source_type=meta.get("source_type", ""),
                chunk_id=meta.get("chunk_id", ""),
                chunk_index=meta.get("chunk_index", 0),
                total_chunks=meta.get("total_chunks", 0),
                page_number=meta.get("page_number"),
            )
        )

    # Qdrant already returns descending score order; keep the application
    # contract explicit and stable.
    retrieved.sort(key=lambda r: r.score, reverse=True)
    return retrieved
