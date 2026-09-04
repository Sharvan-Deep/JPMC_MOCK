'use strict';

/**
 * Normalized Document Contract for Jaldhaara Foundation
 * CSR Document MCP Server & Source Retrieval Foundation.
 * Shared backend contract definitions.
 */

const DocumentType = Object.freeze({
  ANNUAL_REPORT: 'annual_report',
  CSR_POLICY: 'csr_policy',
  BRSR: 'brsr',
  DISCLOSURE: 'disclosure',
});

const DocumentSource = Object.freeze({
  NSE: 'NSE',
  BSE: 'BSE',
  COMPANY: 'COMPANY',
});

const DocumentStatus = Object.freeze({
  FOUND: 'FOUND',
  NOT_FOUND: 'NOT_FOUND',
  ERROR: 'ERROR',
});

function createNormalizedDocument({
  company_name,
  document_type,
  financial_year = null,
  title = null,
  source,
  url = null,
  published_date = null,
  retrieved_date = new Date().toISOString(),
  status = DocumentStatus.FOUND,
  error_message = null,
  not_found_reason = null,
  metadata = null,
}) {
  if (!company_name || typeof company_name !== 'string') {
    throw new Error('company_name is required and must be a non-empty string');
  }
  if (!document_type || !Object.values(DocumentType).includes(document_type)) {
    throw new Error(`Invalid document_type: "${document_type}"`);
  }
  if (!source || !Object.values(DocumentSource).includes(source)) {
    throw new Error(`Invalid source: "${source}"`);
  }
  if (!status || !Object.values(DocumentStatus).includes(status)) {
    throw new Error(`Invalid status: "${status}"`);
  }

  const doc = {
    company_name: company_name.trim(),
    document_type,
    financial_year: financial_year ? String(financial_year).trim() : null,
    title: title ? String(title).trim() : null,
    source,
    url: url ? String(url).trim() : null,
    published_date: published_date ? String(published_date).trim() : null,
    retrieved_date: retrieved_date ? String(retrieved_date).trim() : new Date().toISOString(),
    status,
  };

  if (status === DocumentStatus.ERROR) {
    doc.error_message = error_message ? String(error_message).trim() : 'Unknown error during document retrieval';
  } else if (error_message) {
    doc.error_message = String(error_message).trim();
  }

  if (status === DocumentStatus.NOT_FOUND) {
    doc.not_found_reason = not_found_reason
      ? String(not_found_reason).trim()
      : 'Document not found at source';
  }

  if (metadata && typeof metadata === 'object') {
    doc.metadata = metadata;
  }

  return doc;
}

function createNotFoundDocument({ company_name, document_type, financial_year = null, source, reason }) {
  return createNormalizedDocument({
    company_name,
    document_type,
    financial_year,
    source,
    status: DocumentStatus.NOT_FOUND,
    not_found_reason: reason || 'Document not found at source',
  });
}

function createErrorDocument({ company_name, document_type, financial_year = null, source, error_message }) {
  return createNormalizedDocument({
    company_name,
    document_type,
    financial_year,
    source,
    status: DocumentStatus.ERROR,
    error_message: error_message || 'An error occurred during retrieval',
  });
}

module.exports = {
  DocumentType,
  DocumentSource,
  DocumentStatus,
  createNormalizedDocument,
  createNotFoundDocument,
  createErrorDocument,
};
