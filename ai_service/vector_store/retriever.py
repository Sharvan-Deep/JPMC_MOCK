"""
CSR Semantic Search Service for Task 7.
Performs nearest-neighbor vector retrieval on document chunks in ChromaDB:
- Generates query embeddings via configured provider
- Applies metadata filters (e.g. company, financial year, document version, is_latest)
- Returns structured search hits with similarity scores and evidence traceability
"""

import time
from typing import Any, Dict, List, Optional

from ai_service.logging_config import logger
from ai_service.schemas.vector_store import SearchResult, SearchResultItem
from ai_service.vector_store.client import ChromaDBManager
from ai_service.vector_store.embeddings import BaseEmbeddingProvider, get_embedding_provider


class CSRSemanticSearchService:
    """Semantic vector search engine for the CSR knowledge layer."""

    def __init__(
        self,
        chroma_manager: Optional[ChromaDBManager] = None,
        embedding_provider: Optional[BaseEmbeddingProvider] = None,
    ):
        self.chroma_manager = chroma_manager or ChromaDBManager()
        self.embedding_provider = embedding_provider or get_embedding_provider()

    def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 5,
        collection_name: Optional[str] = None,
    ) -> SearchResult:
        """
        Executes semantic vector search over CSR document chunks.

        Args:
            query: Natural language query string.
            filters: Optional metadata filters (e.g. {'company_name': '...', 'is_latest': True}).
            top_k: Number of nearest chunks to retrieve.
            collection_name: Optional collection override.

        Returns:
            SearchResult with matching chunks and evidence metadata.
        """
        start_time = time.time()
        target_collection_name = collection_name or self.chroma_manager.collection_name

        if not query or not query.strip():
            return SearchResult(
                query=query,
                total_results=0,
                results=[],
                filters_applied=filters,
                time_taken_seconds=round(time.time() - start_time, 4),
            )

        try:
            # 1. Embed query text
            query_vector = self.embedding_provider.embed_query(query.strip())

            # 2. Format ChromaDB metadata filter clause
            where_clause = self._build_where_clause(filters)

            # 3. Query ChromaDB collection
            collection = self.chroma_manager.get_collection(target_collection_name)
            query_params: Dict[str, Any] = {
                "query_embeddings": [query_vector],
                "n_results": top_k,
                "include": ["documents", "metadatas", "distances"],
            }
            if where_clause:
                query_params["where"] = where_clause

            raw_results = collection.query(**query_params)

            # 4. Parse results into structured schema
            hits: List[SearchResultItem] = []
            ids = raw_results.get("ids", [[]])[0]
            docs = raw_results.get("documents", [[]])[0]
            metas = raw_results.get("metadatas", [[]])[0]
            distances = raw_results.get("distances", [[]])[0]

            for idx in range(len(ids)):
                chunk_id = ids[idx]
                text = docs[idx] if idx < len(docs) else ""
                meta = metas[idx] if idx < len(metas) else {}
                dist = distances[idx] if idx < len(distances) else 0.0

                # Convert cosine distance into a 0.0 - 1.0 similarity score
                similarity_score = round(max(0.0, 1.0 - float(dist)), 4)

                hits.append(
                    SearchResultItem(
                        chunk_id=chunk_id,
                        text=text,
                        score=similarity_score,
                        metadata=meta,
                    )
                )

            return SearchResult(
                query=query,
                total_results=len(hits),
                results=hits,
                filters_applied=filters,
                time_taken_seconds=round(time.time() - start_time, 4),
            )

        except Exception as exc:
            logger.error(f"Semantic search query failed: {str(exc)}")
            return SearchResult(
                query=query,
                total_results=0,
                results=[],
                filters_applied=filters,
                time_taken_seconds=round(time.time() - start_time, 4),
            )

    def _build_where_clause(self, filters: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Converts user filter dictionary into ChromaDB $and syntax if multiple fields."""
        if not filters:
            return None

        # Clean out empty/None filter entries
        clean_filters = {k: v for k, v in filters.items() if v is not None and v != ""}
        if not clean_filters:
            return None

        if len(clean_filters) == 1:
            k, v = list(clean_filters.items())[0]
            return {k: v}

        return {"$and": [{k: v} for k, v in clean_filters.items()]}
