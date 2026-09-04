"""
Document intake and contract validation endpoints.
Provides the HTTP contract for receiving Task 2 documents for future processing.
"""

from fastapi import APIRouter, Depends
from ai_service.config import Settings, get_settings
from ai_service.schemas.document import DocumentInputSchema, DocumentValidationResponse
from ai_service.services.document_service import DocumentService

router = APIRouter(prefix="/api/v1/documents", tags=["Documents"])


def get_document_service(settings: Settings = Depends(get_settings)) -> DocumentService:
    return DocumentService(storage_base_path=settings.DOCUMENTS_STORAGE_PATH)


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
