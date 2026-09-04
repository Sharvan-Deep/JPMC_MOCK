"""
Vector Knowledge Layer with ChromaDB.
Exposes ChromaDBManager, CSRDocumentChunker, CSRIndexingService,
CSRSemanticSearchService, and embedding providers.
"""

from ai_service.vector_store.chunker import CSRDocumentChunker
from ai_service.vector_store.client import ChromaDBManager
from ai_service.vector_store.embeddings import (
    BaseEmbeddingProvider,
    GeminiEmbeddingProvider,
    MockEmbeddingProvider,
    get_embedding_provider,
)
from ai_service.vector_store.indexer import CSRIndexingService
from ai_service.vector_store.retriever import CSRSemanticSearchService

__all__ = [
    "ChromaDBManager",
    "CSRDocumentChunker",
    "CSRIndexingService",
    "CSRSemanticSearchService",
    "BaseEmbeddingProvider",
    "GeminiEmbeddingProvider",
    "MockEmbeddingProvider",
    "get_embedding_provider",
]
