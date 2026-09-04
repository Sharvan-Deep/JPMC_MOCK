const fs = require('fs');
const path = require('path');
const { parse } = require('csv-parse/sync');
const { Company } = require('../models');
const { COMPANY_CSV_HEADERS } = require('../config/constants');
const {
  validateCompanyCsvHeaders,
  validateCompanyDocument,
} = require('../validators/companyImportValidator');
const {
  buildCompanyNameKey,
  parseNumeric,
  parseInteger,
  parseDelimitedArray,
  parseDate,
  parseText,
} = require('../utils/dataNormalization');

/**
 * Company CSV Import Service
 *
 * Imports 03_company_ai_ready_summary.csv into the Company collection.
 *
 * MATCHING KEY LIMITATION:
 *   company_name (normalized to companyNameKey) is the only deduplication key
 *   because the CSV provides no stable external identifier (e.g. CIN).
 *   Exact normalized name match only — no fuzzy merging.
 *
 * IDEMPOTENCY:
 *   Re-running the import updates existing records matched by companyNameKey
 *   and inserts new ones. Safe to run multiple times.
 */

/**
 * Map a raw CSV row object to a normalized Company document.
 * Header keys are matched case-insensitively.
 *
 * @param {Record<string, string>} row
 * @returns {object}
 */
function normalizeCompanyRow(row) {
  const get = (field) => {
    const key = Object.keys(row).find((k) => k.trim().toLowerCase() === field);
    return key ? row[key] : undefined;
  };

  const companyName = parseText(get('company_name'));

  return {
    company_name: companyName,
    companyNameKey: buildCompanyNameKey(companyName),
    wash_record_count: parseInteger(get('wash_record_count')),
    financial_years: parseDelimitedArray(get('financial_years')),
    states: parseDelimitedArray(get('states')),
    csr_sectors: parseDelimitedArray(get('csr_sectors')),
    total_wash_spend_crore: parseNumeric(get('total_wash_spend_crore')),
    latest_financial_year: parseText(get('latest_financial_year')),
    total_water_spend_crore: parseNumeric(get('total_water_spend_crore')),
    total_sanitation_spend_crore: parseNumeric(get('total_sanitation_spend_crore')),
    water_active_years: parseDelimitedArray(get('water_active_years')),
    sanitation_active_years: parseDelimitedArray(get('sanitation_active_years')),
    wash_focus_evidence: parseText(get('wash_focus_evidence')),
    source: parseText(get('source')),
    source_retrieved_date: parseDate(get('source_retrieved_date')),
  };
}

/**
 * Parse CSV file contents into an array of row objects.
 *
 * @param {string} filePath - Absolute or relative path to CSV file
 * @returns {{ rows: Record<string, string>[], headers: string[] }}
 */
function parseCompanyCsv(filePath) {
  const absolutePath = path.resolve(filePath);

  if (!fs.existsSync(absolutePath)) {
    throw new Error(`CSV file not found: ${absolutePath}`);
  }

  const fileContent = fs.readFileSync(absolutePath, 'utf8');

  const records = parse(fileContent, {
    columns: true,
    skip_empty_lines: true,
    trim: true,
    relax_column_count: true,
  });

  const headers = records.length > 0 ? Object.keys(records[0]) : COMPANY_CSV_HEADERS;

  return { rows: records, headers };
}

/**
 * Import companies from a CSV file into MongoDB.
 *
 * @param {string} filePath - Path to 03_company_ai_ready_summary.csv
 * @param {object} [options]
 * @param {boolean} [options.dryRun=false] - Parse and validate without writing
 * @returns {Promise<ImportSummary>}
 *
 * @typedef {object} ImportSummary
 * @property {number} totalRows
 * @property {number} inserted
 * @property {number} updated
 * @property {number} skipped
 * @property {number} failed
 * @property {Array<{ row: number, company_name: string, errors: string[] }>} errors
 */
async function importCompaniesFromCsv(filePath, options = {}) {
  const { dryRun = false } = options;

  const summary = {
    totalRows: 0,
    inserted: 0,
    updated: 0,
    skipped: 0,
    failed: 0,
    errors: [],
  };

  const { rows, headers } = parseCompanyCsv(filePath);

  const headerValidation = validateCompanyCsvHeaders(headers);
  if (!headerValidation.valid) {
    throw new Error(
      `CSV header validation failed. Missing columns: ${headerValidation.missing.join(', ')}`
    );
  }

  summary.totalRows = rows.length;

  for (let i = 0; i < rows.length; i++) {
    const rowNumber = i + 2; // 1-based, accounting for header row
    const rawRow = rows[i];

    try {
      const doc = normalizeCompanyRow(rawRow);
      const validation = validateCompanyDocument(doc);

      if (!validation.valid) {
        summary.failed += 1;
        summary.errors.push({
          row: rowNumber,
          company_name: doc.company_name || '(unknown)',
          errors: validation.errors,
        });
        continue;
      }

      if (!doc.companyNameKey) {
        summary.skipped += 1;
        summary.errors.push({
          row: rowNumber,
          company_name: doc.company_name || '(unknown)',
          errors: ['Empty company name after normalization'],
        });
        continue;
      }

      if (dryRun) {
        summary.inserted += 1;
        continue;
      }

      const existing = await Company.findOne({ companyNameKey: doc.companyNameKey })
        .select('_id')
        .lean();

      if (existing) {
        await Company.updateOne({ _id: existing._id }, { $set: doc });
        summary.updated += 1;
      } else {
        await Company.create(doc);
        summary.inserted += 1;
      }
    } catch (err) {
      summary.failed += 1;
      summary.errors.push({
        row: rowNumber,
        company_name: rawRow.company_name || rawRow.Company_Name || '(unknown)',
        errors: [err.message],
      });
    }
  }

  return summary;
}

module.exports = {
  normalizeCompanyRow,
  parseCompanyCsv,
  importCompaniesFromCsv,
};
