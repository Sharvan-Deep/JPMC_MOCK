"""
Pydantic Schemas for Task 7: Vector Knowledge Layer with ChromaDB.
Defines contracts for document chunks, indexing results, and semantic search queries/responses.
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class DocumentChunk(BaseModel):
    """A semantic chunk derived from cleaned text or structured CSR project records."""

    chunk_id: str = Field(..., description="Deterministic unique identifier for the chunk")
    text: str = Field(..., description="Text content to be embedded and searched")
    metadata: Dict[str, Union[str, int, float, bool]] = Field(
        default_factory=dict,
        description="Primitive metadata dictionary stored in ChromaDB",
    )


class IndexingResult(BaseModel):
    """Structured result returned upon indexing a processed CSR document into ChromaDB."""

    status: str = Field(..., description="Indexing status: INDEXED or FAILED")
    company_name: str = Field(..., description="Company name of the indexed document")
    financial_year: str = Field(..., description="Financial year of the indexed document")
    document_version: int = Field(1, description="Version number of the indexed document")
    chunks_created: int = Field(0, description="Total number of chunks created and upserted")
    collection_name: str = Field(..., description="ChromaDB collection storing the vectors")
    sha256: str = Field(..., description="SHA-256 hash of the underlying document")
    time_taken_seconds: float = Field(0.0, description="Duration of chunking and indexing in seconds")
    errors: List[str] = Field(default_factory=list, description="Any warnings or error details")


class SearchQueryRequest(BaseModel):
    """Request payload for semantic vector search."""

    query: str = Field(..., min_length=1, description="Natural language semantic search query")
    filters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata filter dictionary (e.g. {'company_name': '...', 'is_latest': True})",
    )
    top_k: int = Field(default=5, ge=1, le=50, description="Number of nearest chunks to retrieve")


class SearchResultItem(BaseModel):
    """An individual search hit with similarity score and evidence traceability metadata."""

    chunk_id: str = Field(..., description="Chunk identifier")
    text: str = Field(..., description="Verbatim chunk text")
    score: float = Field(..., description="Similarity score or distance metric")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata containing company, FY, version, page number, source, and SHA-256",
    )


class SearchResult(BaseModel):
    """Top-level semantic vector search response."""

    query: str = Field(..., description="Original search query string")
    total_results: int = Field(0, description="Number of retrieved matching chunks")
    results: List[SearchResultItem] = Field(
        default_factory=list, description="List of search hits ordered by relevance"
    )
    filters_applied: Optional[Dict[str, Any]] = Field(
        default=None, description="Metadata filters applied during the query"
    )
    time_taken_seconds: float = Field(0.0, description="Search query duration in seconds")
