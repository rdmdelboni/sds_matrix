from __future__ import annotations

import os
import uuid
from typing import Any

import chromadb
from chromadb.api import ClientAPI
from chromadb.utils.embedding_functions import (
    SentenceTransformerEmbeddingFunction,
)

from src.utils.logger import logger

class VectorStore:
    """
    Lightweight wrapper around ChromaDB with Sentence-Transformer embeddings.

    Responsibilities:
    - Manage a persistent Chroma collection
    - Add documents (with metadata) and perform semantic search
    - Convenience method to index text or files (PDF/TXT)
    """

    def __init__(
        self,
        persist_path: str = "data/vectorstore",
        collection_name: str = "fds",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        device: str = "cpu",
        normalize_embeddings: bool = True,
        metric: str = "cosine",
    ) -> None:
        self.persist_path = persist_path
        os.makedirs(self.persist_path, exist_ok=True)

        logger.info(
            "Initializing VectorStore at %s "
            "(collection=%s, model=%s, device=%s)",
            self.persist_path,
            collection_name,
            embedding_model,
            device,
        )

        self._client: ClientAPI = chromadb.PersistentClient(
            path=self.persist_path
        )
        self._embedding_fn = SentenceTransformerEmbeddingFunction(
            model_name=embedding_model,
            device=device,
            normalize_embeddings=normalize_embeddings,
        )

        # hnsw:space can be 'cosine' (default), 'l2', or 'ip'
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": metric},
            embedding_function=self._embedding_fn,
        )

    # ----------------------------- Public API ----------------------------- #
    def add_documents(
        self,
        texts: list[str],
        metadatas: list[dict[str, Any]] | None = None,
        ids: list[str] | None = None,
    ) -> int:
        if not texts:
            logger.warning(
                "add_documents called with empty texts list; skipping"
            )
            return 0

        # Clean and filter out empties
        cleaned: list[str] = []
        cleaned_meta: list[dict[str, Any]] = []
        cleaned_ids: list[str] = []

        for i, t in enumerate(texts):
            t2 = (t or "").strip()
            if not t2:
                continue
            cleaned.append(t2)
            if metadatas and i < len(metadatas):
                cleaned_meta.append(metadatas[i] or {})
            else:
                cleaned_meta.append({})
            if ids and i < len(ids) and ids[i]:
                cleaned_ids.append(ids[i])
            else:
                cleaned_ids.append(str(uuid.uuid4()))

        if not cleaned:
            logger.warning("No non-empty texts to add; skipping")
            return 0

        self._collection.add(
            documents=cleaned, metadatas=cleaned_meta, ids=cleaned_ids
        )
        logger.info(
            "Indexed %d documents into collection '%s'",
            len(cleaned),
            self._collection.name,
        )
        return len(cleaned)

    def search(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        q = (query or "").strip()
        if len(q) < 3:
            logger.warning("Query too short for search: '%s'", query)
            return []
        try:
            res = self._collection.query(
                query_texts=[q],
                n_results=max(1, k),
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            logger.exception("Chroma query failed: %s", e)
            return []
        results: list[dict[str, Any]] = []
        # Chroma returns lists per-query; we only sent one query
        docs = res.get("documents", [[]])[0] or []
        metas = res.get("metadatas", [[]])[0] or []
        dists = res.get("distances", [[]])[0] or []
        ids = res.get("ids", [[]])[0] if res.get("ids") else [None] * len(docs)

        for i, text in enumerate(docs):
            results.append(
                {
                    "id": ids[i] if i < len(ids) else None,
                    "text": text,
                    "metadata": metas[i] if i < len(metas) else {},
                    "distance": dists[i] if i < len(dists) else None,
                }
            )
        return results

    # --------------------------- Convenience API -------------------------- #
    def index_text(
        self,
        text: str,
        source: str | None = None,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> int:
        chunks = _chunk_text(
            text or "", chunk_size=chunk_size, overlap=chunk_overlap
        )
        metas = [
            {"source": source or "inline", "chunk_index": i, "type": "text"}
            for i in range(len(chunks))
        ]
        return self.add_documents(chunks, metas)

    def index_file(
        self,
        file_path: str,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> int:
        path = (file_path or "").strip()
        if not path or not os.path.exists(path):
            logger.warning("index_file path does not exist: %s", file_path)
            return 0
        ext = os.path.splitext(path)[1].lower()

        if ext == ".pdf":
            try:
                import pdfplumber  # lazy import

                text_parts: list[str] = []
                with pdfplumber.open(path) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text() or ""
                        if page_text:
                            text_parts.append(page_text)
                full_text = "\n".join(text_parts)
            except Exception as e:
                logger.exception(
                    "Failed to extract text from PDF %s: %s", path, e
                )
                return 0
        else:
            # Fallback for .txt and unknown files: try UTF-8 read
            try:
                with open(path, encoding="utf-8", errors="ignore") as f:
                    full_text = f.read()
            except Exception as e:
                logger.exception("Failed to read file %s: %s", path, e)
                return 0

        if not (full_text or "").strip():
            logger.warning(
                "No text extracted from %s; skipping indexing", path
            )
            return 0

        chunks = _chunk_text(
            full_text, chunk_size=chunk_size, overlap=chunk_overlap
        )
        metas = [
            {
                "source": os.path.abspath(path),
                "chunk_index": i,
                "type": ext.lstrip(".") or "text",
            }
            for i in range(len(chunks))
        ]
        return self.add_documents(chunks, metas)

def _chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[str]:
    """Simple character-based chunking with overlap.

        - chunk_size: target characters per chunk
        - overlap: characters overlapped between consecutive chunks
            (to reduce context loss)
    """
    t = (text or "").strip()
    if not t:
        return []
    if chunk_size <= 0:
        return [t]
    chunks: list[str] = []
    start = 0
    n = len(t)
    step = max(1, chunk_size - max(0, overlap))
    while start < n:
        end = min(n, start + chunk_size)
        chunks.append(t[start:end])
        start += step
    return chunks
