"""
CSR Document Indexing Service for Task 7.
Coordinates chunking, embedding generation, and idempotent upsert into ChromaDB.
"""

import time
from typing import Any, Dict, List, Optional, Union

from ai_service.logging_config import logger
from ai_service.schemas.preprocessing import CSRPreprocessingResult
from ai_service.schemas.vector_store import IndexingResult
from ai_service.vector_store.chunker import CSRDocumentChunker
from ai_service.vector_store.client import ChromaDBManager
from ai_service.vector_store.embeddings import BaseEmbeddingProvider, get_embedding_provider


class CSRIndexingService:
    """Indexes preprocessed CSR documents into the ChromaDB vector knowledge layer."""

    def __init__(
        self,
        chroma_manager: Optional[ChromaDBManager] = None,
        chunker: Optional[CSRDocumentChunker] = None,
        embedding_provider: Optional[BaseEmbeddingProvider] = None,
    ):
        self.chroma_manager = chroma_manager or ChromaDBManager()
        self.chunker = chunker or CSRDocumentChunker()
        self.embedding_provider = embedding_provider or get_embedding_provider()

    def index_document(
        self,
        processed_document: Union[CSRPreprocessingResult, Dict[str, Any]],
        collection_name: Optional[str] = None,
    ) -> IndexingResult:
        """
        Indexes a preprocessed CSR document into ChromaDB.

        Guarantees:
        1. Validates processed document structure.
        2. Generates page-bounded narrative chunks and structured project chunks.
        3. Generates vector embeddings via configured provider.
        4. Idempotent upsert preventing duplicate chunks upon re-indexing.
        5. Preserves document versioning and evidence metadata.
        """
        start_time = time.time()
        errors: List[str] = []

        # Parse dict into CSRPreprocessingResult if needed
        if isinstance(processed_document, dict):
            try:
                doc_obj = CSRPreprocessingResult(**processed_document)
            except Exception as e:
                err_msg = f"Invalid processed document payload: {str(e)}"
                logger.error(err_msg)
                return IndexingResult(
                    status="FAILED",
                    company_name="UNKNOWN",
                    financial_year="UNKNOWN",
                    document_version=1,
                    chunks_created=0,
                    collection_name=collection_name or self.chroma_manager.collection_name,
                    sha256="",
                    time_taken_seconds=round(time.time() - start_time, 4),
                    errors=[err_msg],
                )
        else:
            doc_obj = processed_document

        doc_meta = doc_obj.document_metadata or {}
        cleaned_data = doc_obj.cleaned_data

        company = cleaned_data.canonical_company_name or doc_meta.get("company_name", "UNKNOWN")
        fy = cleaned_data.normalized_financial_year or doc_meta.get("financial_year", "2023-24")
        version = int(doc_meta.get("version", 1))
        sha256 = doc_meta.get("sha256", "")
        target_collection_name = collection_name or self.chroma_manager.collection_name

        # Check for empty content
        total_text_len = sum(len(t.strip()) for t in doc_obj.cleaned_text_by_page.values())
        if total_text_len == 0 and not cleaned_data.records:
            err_msg = "Processed document contains no text and no CSR project records to index."
            logger.warning(err_msg)
            return IndexingResult(
                status="FAILED",
                company_name=company,
                financial_year=fy,
                document_version=version,
                chunks_created=0,
                collection_name=target_collection_name,
                sha256=sha256,
                time_taken_seconds=round(time.time() - start_time, 4),
                errors=[err_msg],
            )

        # 1. Generate chunks
        try:
            chunks = self.chunker.chunk_document(doc_obj)
        except Exception as chunk_exc:
            err_msg = f"Document chunking failed: {str(chunk_exc)}"
            logger.error(err_msg)
            return IndexingResult(
                status="FAILED",
                company_name=company,
                financial_year=fy,
                document_version=version,
                chunks_created=0,
                collection_name=target_collection_name,
                sha256=sha256,
                time_taken_seconds=round(time.time() - start_time, 4),
                errors=[err_msg],
            )

        if not chunks:
            err_msg = "Chunking yielded 0 chunks for indexing."
            return IndexingResult(
                status="FAILED",
                company_name=company,
                financial_year=fy,
                document_version=version,
                chunks_created=0,
                collection_name=target_collection_name,
                sha256=sha256,
                time_taken_seconds=round(time.time() - start_time, 4),
                errors=[err_msg],
            )

        # 2. Generate embeddings
        chunk_texts = [c.text for c in chunks]
        try:
            embeddings = self.embedding_provider.embed_documents(chunk_texts)
        except Exception as embed_exc:
            err_msg = f"Embedding generation failed: {str(embed_exc)}"
            logger.error(err_msg)
            return IndexingResult(
                status="FAILED",
                company_name=company,
                financial_year=fy,
                document_version=version,
                chunks_created=len(chunks),
                collection_name=target_collection_name,
                sha256=sha256,
                time_taken_seconds=round(time.time() - start_time, 4),
                errors=[err_msg],
            )

        # 3. Upsert into ChromaDB
        try:
            collection = self.chroma_manager.get_collection(target_collection_name)

            chunk_ids = [c.chunk_id for c in chunks]
            metadatas = [c.metadata for c in chunks]

            # Upsert ensures idempotent indexing (re-indexing will not multiply chunks)
            collection.upsert(
                ids=chunk_ids,
                documents=chunk_texts,
                embeddings=embeddings,
                metadatas=metadatas,
            )
            logger.info(
                f"Successfully upserted {len(chunks)} chunks into ChromaDB collection '{target_collection_name}' "
                f"for company='{company}', FY='{fy}', v{version}"
            )

        except Exception as chroma_exc:
            err_msg = f"ChromaDB storage operation failed: {str(chroma_exc)}"
            logger.error(err_msg)
            return IndexingResult(
                status="FAILED",
                company_name=company,
                financial_year=fy,
                document_version=version,
                chunks_created=len(chunks),
                collection_name=target_collection_name,
                sha256=sha256,
                time_taken_seconds=round(time.time() - start_time, 4),
                errors=[err_msg],
            )

        return IndexingResult(
            status="INDEXED",
            company_name=company,
            financial_year=fy,
            document_version=version,
            chunks_created=len(chunks),
            collection_name=target_collection_name,
            sha256=sha256,
            time_taken_seconds=round(time.time() - start_time, 4),
            errors=errors,
        )
