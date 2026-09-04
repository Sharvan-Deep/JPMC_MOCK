"""
Document intake and contract validation endpoints.
Provides the HTTP contract for receiving Task 2 documents for future processing.
"""

from fastapi import APIRouter, Depends
from ai_service.classification.service import CSRClassificationService
from ai_service.config import Settings, get_settings
from ai_service.extraction.service import CSRExtractorService
from ai_service.preprocessing.service import CSRPreprocessingService
from ai_service.schemas.classification import WASHClassificationResult
from ai_service.schemas.document import DocumentInputSchema, DocumentValidationResponse
from ai_service.schemas.extraction import CSRExtractionResult
from ai_service.schemas.preprocessing import CSRPreprocessingResult
from ai_service.services.document_service import DocumentService

router = APIRouter(prefix="/api/v1/documents", tags=["Documents"])


def get_document_service(settings: Settings = Depends(get_settings)) -> DocumentService:
    return DocumentService(storage_base_path=settings.DOCUMENTS_STORAGE_PATH)


def get_extractor_service(service: DocumentService = Depends(get_document_service)) -> CSRExtractorService:
    return CSRExtractorService(document_service=service)


def get_preprocessing_service() -> CSRPreprocessingService:
    return CSRPreprocessingService()


def get_classification_service() -> CSRClassificationService:
    return CSRClassificationService()


@router.post(
    "/validate",
    response_model=DocumentValidationResponse,
    summary="Validate document input contract",
    description=(
        "Validates that a document metadata payload conforming to Task 2 specifications "
        "is structurally valid and ready for downstream processing. Does NOT extract or analyze PDF content."
    ),
)
async def validate_document(
    document: DocumentInputSchema,
    service: DocumentService = Depends(get_document_service),
):
    """Validates document input contract."""
    return service.validate_document_contract(document)


@router.post(
    "/extract",
    response_model=CSRExtractionResult,
    summary="Extract CSR text and tables from validated PDF",
    description=(
        "Enforces Task 3 validation gate and executes Task 4 data extraction. "
        "Extracts raw text, table matrices, and identified CSR data (donor name, financial year, "
        "total amount spent, project details, locations, beneficiaries). Flags OCR-needed pages."
    ),
)
async def extract_document(
    document: DocumentInputSchema,
    extractor: CSRExtractorService = Depends(get_extractor_service),
):
    """Validates document and extracts raw CSR text, tables, and structured entities."""
    return extractor.extract_from_document(document)


@router.post(
    "/preprocess",
    response_model=CSRPreprocessingResult,
    summary="Clean and normalize raw extracted CSR data (Task 5)",
    description=(
        "Consumes Task 4 raw extraction output. Cleans text and table artifacts, "
        "normalizes currency amounts to Crores, standardizes financial years and company names, "
        "and removes extraction-duplicate rows while preserving raw values and page references."
    ),
)
async def preprocess_document(
    extraction_result: CSRExtractionResult,
    service: CSRPreprocessingService = Depends(get_preprocessing_service),
):
    """Preprocesses raw extraction data into clean, AI-ready data."""
    return service.preprocess(extraction_result)


@router.post(
    "/classify",
    response_model=WASHClassificationResult,
    summary="Classify preprocessed CSR data for WASH relevance (Task 6)",
    description=(
        "Consumes Task 5 cleaned CSR data. Distinguishes genuine community WASH "
        "(Safe Drinking Water, Community Sanitation, Hygiene) from industrial operational water. "
        "Returns evidence-first output with verbatim snippets, page numbers, and confidence."
    ),
)
async def classify_document(
    preprocessed_result: CSRPreprocessingResult,
    service: CSRClassificationService = Depends(get_classification_service),
):
    """Classifies preprocessed CSR data for community WASH relevance."""
    return service.classify_preprocessed_document(preprocessed_result)
