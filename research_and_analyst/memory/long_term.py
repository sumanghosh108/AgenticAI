"""
Long-Term Memory — persistent vector store for cross-session knowledge.

Stores past queries, user preferences, domain knowledge, and agent learnings.
Uses ChromaDB for vector similarity search with LangChain embeddings.
"""

import os
import time
import uuid
from typing import Any, Dict, List, Optional

from research_and_analyst.logger import GLOBAL_LOGGER as log


class LongTermMemory:
    """
    Persistent vector-based memory using ChromaDB.

    Stores:
    - Past queries and their outcomes
    - User preferences
    - Domain knowledge snippets
    - Agent learning (what worked, what didn't)
    """

    def __init__(
        self,
        collection_name: str = "agenticai_memory",
        persist_directory: str = "./memory_store",
        embedding_function=None,
    ):
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self._collection = None
        self._client = None
        self._embedding_fn = embedding_function

    def _get_collection(self):
        """Lazy-initialize the ChromaDB collection."""
        if self._collection is not None:
            return self._collection

        try:
            import chromadb
            from chromadb.config import Settings

            self._client = chromadb.Client(Settings(
                chroma_db_impl="duckdb+parquet",
                persist_directory=self.persist_directory,
                anonymized_telemetry=False,
            ))
        except TypeError:
            # Newer ChromaDB versions use different init
            import chromadb

            self._client = chromadb.PersistentClient(path=self.persist_directory)

        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        log.info("Long-term memory initialized", collection=self.collection_name)
        return self._collection

    def store(
        self,
        content: str,
        metadata: Optional[Dict[str, str]] = None,
        memory_type: str = "knowledge",
        doc_id: Optional[str] = None,
    ) -> str:
        """
        Store a memory entry.

        Args:
            content: Text content to store.
            metadata: Additional metadata (source, domain, etc.).
            memory_type: Category (query, preference, knowledge, learning).
            doc_id: Optional custom ID.

        Returns:
            The document ID.
        """
        collection = self._get_collection()
        doc_id = doc_id or str(uuid.uuid4())

        meta = metadata or {}
        meta["memory_type"] = memory_type
        meta["timestamp"] = str(time.time())

        collection.add(
            documents=[content],
            metadatas=[meta],
            ids=[doc_id],
        )
        log.info("Long-term memory stored", id=doc_id, type=memory_type)
        return doc_id

    def recall(
        self,
        query: str,
        n_results: int = 5,
        memory_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search memory by semantic similarity.

        Args:
            query: Search query text.
            n_results: Max results to return.
            memory_type: Filter by memory type (optional).

        Returns:
            List of dicts with 'content', 'metadata', 'distance'.
        """
        collection = self._get_collection()

        where_filter = {"memory_type": memory_type} if memory_type else None

        try:
            results = collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_filter,
            )
        except Exception as e:
            log.warning("Long-term memory query failed", error=str(e))
            return []

        entries = []
        if results and results.get("documents"):
            docs = results["documents"][0]
            metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
            dists = results["distances"][0] if results.get("distances") else [0.0] * len(docs)

            for doc, meta, dist in zip(docs, metas, dists):
                entries.append({
                    "content": doc,
                    "metadata": meta,
                    "distance": dist,
                })

        log.info("Long-term memory recalled", query=query[:50], results=len(entries))
        return entries

    def store_query_outcome(self, query: str, decision: str, success: bool) -> str:
        """Store a past query and its outcome for future reference."""
        content = f"Query: {query}\nDecision: {decision}\nOutcome: {'Success' if success else 'Failure'}"
        return self.store(
            content=content,
            metadata={"query": query[:200], "decision": decision, "success": str(success)},
            memory_type="query",
        )

    def store_preference(self, preference: str, category: str = "general") -> str:
        """Store a user preference."""
        return self.store(
            content=preference,
            metadata={"category": category},
            memory_type="preference",
        )

    def get_relevant_context(self, query: str, n_results: int = 3) -> List[str]:
        """Get relevant past context as plain text strings."""
        entries = self.recall(query, n_results=n_results)
        return [e["content"] for e in entries]

    def count(self) -> int:
        """Return total number of stored memories."""
        collection = self._get_collection()
        return collection.count()
