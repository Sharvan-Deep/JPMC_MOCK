"""
Unit & Integration Tests for Task 7: Vector Knowledge Layer with ChromaDB.
Tests persistent ChromaDB initialization, page-aware chunking, deterministic chunk IDs,
idempotent deduplication, version awareness, semantic search, metadata filtering,
evidence traceability, and FastAPI API endpoints.
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from ai_service.config import Settings
from ai_service.main import app
from ai_service.schemas.preprocessing import (
    CleanedCSRData,
    CleanedCSRRecord,
    CSRPreprocessingResult,
)
from ai_service.schemas.vector_store import SearchQueryRequest
from ai_service.vector_store.chunker import CSRDocumentChunker
from ai_service.vector_store.client import ChromaDBManager
from ai_service.vector_store.embeddings import MockEmbeddingProvider
from ai_service.vector_store.indexer import CSRIndexingService
from ai_service.vector_store.retriever import CSRSemanticSearchService


@pytest.fixture
def test_chroma_setup(tmp_path):
    """Provides an isolated ChromaDB persistent manager and collection for testing."""
    test_settings = Settings(
        CHROMADB_STORAGE_PATH=str(tmp_path / "chromadb_test"),
        CHROMADB_COLLECTION="test_csr_collection",
        EMBEDDING_PROVIDER="mock",
    )
    manager = ChromaDBManager(settings=test_settings)
    manager.reset_client_for_testing()
    provider = MockEmbeddingProvider()
    chunker = CSRDocumentChunker(target_chunk_size=400, chunk_overlap=50)
    indexer = CSRIndexingService(
        chroma_manager=manager, chunker=chunker, embedding_provider=provider
    )
    retriever = CSRSemanticSearchService(chroma_manager=manager, embedding_provider=provider)
    return {
        "manager": manager,
        "indexer": indexer,
        "retriever": retriever,
        "chunker": chunker,
        "provider": provider,
        "collection_name": "test_csr_collection",
    }


@pytest.fixture
def sample_preprocessed_doc() -> CSRPreprocessingResult:
    """Provides a realistic preprocessed CSR document for indexing."""
    return CSRPreprocessingResult(
        status="SUCCESS",
        document_metadata={
            "company_name": "BHARAT INFRASTRUCTURE LIMITED",
            "document_type": "annual_report",
            "financial_year": "2023-24",
            "version": 1,
            "is_latest": True,
            "sha256": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            "source": "NSE",
            "source_url": "https://nseindia.com/reports/bharat.pdf",
            "file_name": "bharat_annual_report_2023_24_v1.pdf",
            "company_identifier": "BHARATINFRA",
        },
        cleaned_data=CleanedCSRData(
            canonical_company_name="Bharat Infrastructure",
            raw_company_name="BHARAT INFRASTRUCTURE LIMITED",
            normalized_financial_year="2023-24",
            raw_total_csr_amount="Rs. 24.50 Crores",
            normalized_total_csr_amount_crore=24.50,
            records=[
                CleanedCSRRecord(
                    project_name="Jaldhaara Clean Drinking Water Kiosks",
                    category="Safe Drinking Water",
                    location="Maharashtra (Palghar, Thane)",
                    raw_amount_spent="Rs. 8.50 Crores",
                    normalized_amount_spent_crore=8.50,
                    beneficiaries="50,000 rural residents",
                    implementation_mode="Through Implementing Agency",
                    page_number=3,
                ),
                CleanedCSRRecord(
                    project_name="Swachh Vidyalaya Sanitation Blocks",
                    category="Sanitation & Hygiene",
                    location="Gujarat (Navsari, Surat)",
                    raw_amount_spent="Rs. 6.20 Crores",
                    normalized_amount_spent_crore=6.20,
                    beneficiaries="12,000 school students",
                    implementation_mode="Direct",
                    page_number=4,
                ),
            ],
        ),
        cleaned_text_by_page={
            1: "Overview: Bharat Infrastructure committed Rs. 24.50 Crores toward corporate social responsibility.",
            3: "Page 3: Safe drinking water initiative installed 50 community RO kiosks across drought-prone rural clusters.",
            4: "Page 4: Constructed separate toilet complexes and handwashing hygiene stations across rural schools.",
        },
    )


# 1. ChromaDB initialization and collection creation
def test_chromadb_initialization_and_collection(test_chroma_setup):
    manager = test_chroma_setup["manager"]
    col = manager.get_collection()
    assert col is not None
    assert col.name == test_chroma_setup["collection_name"]
    assert col.count() == 0


# 2. Document chunking: narrative and structured record chunks
def test_document_chunking(sample_preprocessed_doc):
    chunker = CSRDocumentChunker(target_chunk_size=300)
    chunks = chunker.chunk_document(sample_preprocessed_doc)

    assert len(chunks) >= 5
    # Structured project chunks
    proj_chunks = [c for c in chunks if c.metadata.get("chunk_type") == "csr_project_record"]
    assert len(proj_chunks) == 2
    assert "Jaldhaara Clean Drinking Water Kiosks" in proj_chunks[0].text
    assert proj_chunks[0].metadata["page_number"] == 3

    # Narrative text chunks
    narrative_chunks = [c for c in chunks if c.metadata.get("chunk_type") == "narrative_text"]
    assert len(narrative_chunks) >= 3


# 3. Deterministic chunk IDs
def test_deterministic_chunk_ids(sample_preprocessed_doc):
    chunker = CSRDocumentChunker()
    chunks_1 = chunker.chunk_document(sample_preprocessed_doc)
    chunks_2 = chunker.chunk_document(sample_preprocessed_doc)

    ids_1 = [c.chunk_id for c in chunks_1]
    ids_2 = [c.chunk_id for c in chunks_2]
    assert ids_1 == ids_2
    assert "BHARAT_INFRASTRUCTURE" in ids_1[0]
    assert "_v1_" in ids_1[0]


# 4. Metadata primitive compliance (ChromaDB requirement)
def test_metadata_primitive_types(sample_preprocessed_doc):
    chunker = CSRDocumentChunker()
    chunks = chunker.chunk_document(sample_preprocessed_doc)

    for c in chunks:
        for k, v in c.metadata.items():
            assert isinstance(
                v, (str, int, float, bool)
            ), f"Metadata field '{k}' has invalid non-primitive type: {type(v)}"


# 5. Indexing service execution
def test_indexing_service(test_chroma_setup, sample_preprocessed_doc):
    indexer = test_chroma_setup["indexer"]
    res = indexer.index_document(sample_preprocessed_doc)

    assert res.status == "INDEXED"
    assert res.company_name == "Bharat Infrastructure"
    assert res.financial_year == "2023-24"
    assert res.chunks_created >= 5

    col = test_chroma_setup["manager"].get_collection()
    assert col.count() == res.chunks_created


# 6. Idempotent deduplication (re-indexing same document does not inflate collection)
def test_idempotent_reindexing(test_chroma_setup, sample_preprocessed_doc):
    indexer = test_chroma_setup["indexer"]
    col = test_chroma_setup["manager"].get_collection()

    # First run
    res1 = indexer.index_document(sample_preprocessed_doc)
    count_1 = col.count()

    # Second run with same document
    res2 = indexer.index_document(sample_preprocessed_doc)
    count_2 = col.count()

    assert count_1 == count_2
    assert res1.chunks_created == res2.chunks_created


# 7. Semantic search retrieval
def test_semantic_search_retrieval(test_chroma_setup, sample_preprocessed_doc):
    indexer = test_chroma_setup["indexer"]
    indexer.index_document(sample_preprocessed_doc)

    retriever = test_chroma_setup["retriever"]
    search_res = retriever.search("community drinking water kiosks and purification", top_k=3)

    assert search_res.total_results > 0
    top_hit = search_res.results[0]
    assert "drinking water" in top_hit.text.lower() or "water" in top_hit.text.lower()
    assert top_hit.score >= 0.0


# 8. Semantic search with metadata filtering
def test_semantic_search_metadata_filtering(test_chroma_setup, sample_preprocessed_doc):
    indexer = test_chroma_setup["indexer"]
    indexer.index_document(sample_preprocessed_doc)

    retriever = test_chroma_setup["retriever"]

    # Filter matching Bharat Infrastructure
    hit_bharat = retriever.search(
        "sanitation", filters={"company_name": "Bharat Infrastructure"}, top_k=3
    )
    assert hit_bharat.total_results > 0
    assert all(h.metadata["company_name"] == "Bharat Infrastructure" for h in hit_bharat.results)

    # Filter with non-matching company
    hit_other = retriever.search(
        "sanitation", filters={"company_name": "NonExistentCompany"}, top_k=3
    )
    assert hit_other.total_results == 0


# 9. Document version awareness and separation (v1 vs v2)
def test_version_awareness(test_chroma_setup, sample_preprocessed_doc):
    indexer = test_chroma_setup["indexer"]
    retriever = test_chroma_setup["retriever"]

    # Index Version 1
    indexer.index_document(sample_preprocessed_doc)

    # Create Version 2 with updated SHA256 and version number
    v2_doc = sample_preprocessed_doc.model_copy(deep=True)
    v2_doc.document_metadata["version"] = 2
    v2_doc.document_metadata["sha256"] = "9999999999999999999999999999999999999999999999999999999999999999"
    v2_doc.cleaned_text_by_page[3] = "Page 3: Version 2 added 20 new solar-powered water purification units."

    indexer.index_document(v2_doc)

    # Verify both v1 and v2 chunks exist
    col = test_chroma_setup["manager"].get_collection()
    assert col.count() >= 10  # Both versions stored

    # Query specifically for Version 1
    v1_results = retriever.search("drinking water", filters={"document_version": 1}, top_k=5)
    assert v1_results.total_results > 0
    assert all(h.metadata["document_version"] == 1 for h in v1_results.results)

    # Query specifically for Version 2
    v2_results = retriever.search("drinking water", filters={"document_version": 2}, top_k=5)
    assert v2_results.total_results > 0
    assert all(h.metadata["document_version"] == 2 for h in v2_results.results)


# 10. Evidence traceability
def test_evidence_traceability(test_chroma_setup, sample_preprocessed_doc):
    indexer = test_chroma_setup["indexer"]
    indexer.index_document(sample_preprocessed_doc)

    retriever = test_chroma_setup["retriever"]
    res = retriever.search("Swachh Vidyalaya school toilets", top_k=1)

    assert res.total_results == 1
    hit = res.results[0]
    meta = hit.metadata

    # Traceability checks
    assert meta["company_name"] == "Bharat Infrastructure"
    assert meta["financial_year"] == "2023-24"
    assert meta["page_number"] in [3, 4]
    assert meta["document_version"] == 1
    assert meta["source"] == "NSE"
    assert meta["sha256"] == "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"


# 11. Error handling: empty document input
def test_indexing_empty_document(test_chroma_setup):
    indexer = test_chroma_setup["indexer"]
    empty_doc = CSRPreprocessingResult(
        status="SUCCESS",
        document_metadata={"company_name": "EMPTY CORP"},
        cleaned_data=CleanedCSRData(),
        cleaned_text_by_page={},
    )
    res = indexer.index_document(empty_doc)
    assert res.status == "FAILED"
    assert res.chunks_created == 0


# 12. API endpoints POST /api/v1/documents/index and POST /api/v1/documents/search
def test_api_index_and_search_endpoints(sample_preprocessed_doc):
    client = TestClient(app)

    # 1. Index document via HTTP
    index_payload = sample_preprocessed_doc.model_dump()
    idx_resp = client.post("/api/v1/documents/index", json=index_payload)
    assert idx_resp.status_code == 200
    idx_data = idx_resp.json()
    assert idx_data["status"] == "INDEXED"
    assert idx_data["chunks_created"] >= 5

    # 2. Semantic search via HTTP
    search_payload = {
        "query": "community drinking water kiosks",
        "filters": {"company_name": "Bharat Infrastructure"},
        "top_k": 3,
    }
    search_resp = client.post("/api/v1/documents/search", json=search_payload)
    assert search_resp.status_code == 200
    search_data = search_resp.json()
    assert search_data["total_results"] > 0
    assert len(search_data["results"]) <= 3
    assert search_data["results"][0]["metadata"]["company_name"] == "Bharat Infrastructure"
