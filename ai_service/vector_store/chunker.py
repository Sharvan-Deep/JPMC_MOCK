"""
Document Chunking Module for Task 7.
Divides cleaned Task 5 text and structured CSR project records into semantic chunks:
- Enforces strict page boundary preservation
- Creates paragraph/sliding-window narrative text chunks (500-800 chars)
- Creates dedicated semantic chunks for individual CSR project records
- Generates deterministic, deduplicated chunk identifiers
- Attaches rich, ChromaDB-compliant primitive metadata
"""

import re
from typing import Any, Dict, List
from ai_service.schemas.preprocessing import CSRPreprocessingResult
from ai_service.schemas.vector_store import DocumentChunk


class CSRDocumentChunker:
    """Chunks preprocessed CSR documents with context and page boundary preservation."""

    def __init__(self, target_chunk_size: int = 600, chunk_overlap: int = 80):
        self.target_chunk_size = target_chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_document(self, processed_doc: CSRPreprocessingResult) -> List[DocumentChunk]:
        """
        Creates semantic chunks from a preprocessed CSR document.
        Produces both narrative text chunks and structured CSR project chunks.
        """
        doc_meta = processed_doc.document_metadata or {}
        cleaned_data = processed_doc.cleaned_data

        company = cleaned_data.canonical_company_name or doc_meta.get("company_name", "UNKNOWN")
        doc_type = doc_meta.get("document_type", "annual_report")
        fy = cleaned_data.normalized_financial_year or doc_meta.get("financial_year", "2023-24")
        version = int(doc_meta.get("version", 1))
        is_latest = bool(doc_meta.get("is_latest", True))
        sha256 = doc_meta.get("sha256", "0" * 64)
        source = doc_meta.get("source", "LOCAL")
        source_url = doc_meta.get("source_url") or ""
        file_name = doc_meta.get("file_name") or ""
        comp_id = doc_meta.get("company_identifier") or ""

        # Sanitize company name for ID prefix
        clean_company_id = re.sub(r"[^a-zA-Z0-9]+", "_", company).strip("_").upper()[:30]
        hash8 = sha256[:8]

        chunks: List[DocumentChunk] = []
        chunk_idx = 0

        # Base metadata common to all chunks
        base_metadata: Dict[str, Any] = {
            "company_name": company,
            "canonical_company_name": cleaned_data.canonical_company_name or company,
            "company_identifier": comp_id,
            "financial_year": fy,
            "document_type": doc_type,
            "document_version": version,
            "is_latest": is_latest,
            "sha256": sha256,
            "source": source,
            "source_url": source_url,
            "original_file_name": file_name,
        }

        # 1. Chunk structured project records (from tables or extraction)
        for proj in cleaned_data.records:
            proj_page = proj.page_number or 1
            chunk_idx += 1
            chunk_id = f"{clean_company_id}_{doc_type}_{fy}_v{version}_{hash8}_p{proj_page}_c{chunk_idx}"

            # Format semantically rich, dense text representation of the project
            proj_text = (
                f"Company: {company} | Financial Year: {fy} | Page: {proj_page}\n"
                f"Project: {proj.project_name or 'CSR Project'}\n"
                f"Sector/Category: {proj.category or 'Unspecified'}\n"
                f"Location: {proj.location or 'Not specified'}\n"
                f"Amount Spent: {proj.raw_amount_spent or 'N/A'}"
                + (f" (Normalized: {proj.normalized_amount_spent_crore} Cr)" if proj.normalized_amount_spent_crore is not None else "")
                + (f"\nOutlay: {proj.raw_amount_allocated}" if proj.raw_amount_allocated else "")
                + (f"\nBeneficiaries: {proj.beneficiaries}" if proj.beneficiaries else "")
                + (f"\nMode: {proj.implementation_mode}" if proj.implementation_mode else "")
            )

            proj_meta = dict(base_metadata)
            proj_meta.update({
                "page_number": proj_page,
                "chunk_index": chunk_idx,
                "chunk_type": "csr_project_record",
                "project_name": proj.project_name or "",
                "category": proj.category or "",
                "location": proj.location or "",
                "amount_spent": proj.raw_amount_spent or "",
                "normalized_amount_spent_crore": float(proj.normalized_amount_spent_crore or 0.0),
            })

            chunks.append(DocumentChunk(chunk_id=chunk_id, text=proj_text, metadata=proj_meta))

        # 2. Chunk narrative text by page (preserving page boundaries)
        for page_num, page_text in processed_doc.cleaned_text_by_page.items():
            if not page_text or len(page_text.strip()) == 0:
                continue

            page_int = int(page_num)
            page_chunks = self._split_page_text(page_text)

            for p_chunk_text in page_chunks:
                chunk_idx += 1
                chunk_id = f"{clean_company_id}_{doc_type}_{fy}_v{version}_{hash8}_p{page_int}_c{chunk_idx}"

                text_header = f"Company: {company} | Financial Year: {fy} | Page: {page_int}\n"
                full_chunk_text = text_header + p_chunk_text

                narrative_meta = dict(base_metadata)
                narrative_meta.update({
                    "page_number": page_int,
                    "chunk_index": chunk_idx,
                    "chunk_type": "narrative_text",
                    "project_name": "",
                    "category": "",
                    "location": "",
                    "amount_spent": "",
                    "normalized_amount_spent_crore": 0.0,
                })

                chunks.append(
                    DocumentChunk(chunk_id=chunk_id, text=full_chunk_text, metadata=narrative_meta)
                )

        return chunks

    def _split_page_text(self, text: str) -> List[str]:
        """Splits page text into paragraphs or overlapping windows."""
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [text.strip()]

        chunks: List[str] = []
        current_chunk = ""

        for para in paragraphs:
            if len(current_chunk) + len(para) + 2 <= self.target_chunk_size:
                current_chunk = f"{current_chunk}\n\n{para}".strip()
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                if len(para) > self.target_chunk_size:
                    # Split long paragraph by sentences
                    sentences = re.split(r"(?<=[.!?])\s+", para)
                    sub_chunk = ""
                    for s in sentences:
                        if len(sub_chunk) + len(s) + 1 <= self.target_chunk_size:
                            sub_chunk = f"{sub_chunk} {s}".strip()
                        else:
                            if sub_chunk:
                                chunks.append(sub_chunk)
                            sub_chunk = s
                    if sub_chunk:
                        chunks.append(sub_chunk)
                    current_chunk = ""
                else:
                    current_chunk = para

        if current_chunk:
            chunks.append(current_chunk)

        return chunks
