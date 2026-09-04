const fs = require('fs');
const path = require('path');
const { parse } = require('csv-parse/sync');
const { Company, CSRActivity, Source } = require('../models');
const { CSR_ACTIVITY_CSV_HEADERS } = require('../config/constants');
const {
  validateCsrActivityCsvHeaders,
  validateCsrActivityDocument,
} = require('../validators/csrActivityImportValidator');
const {
  buildCompanyNameKey,
  parseNumeric,
  parseText,
} = require('../utils/dataNormalization');

const SOURCE_TYPE = 'CSV';

/**
 * Build a deterministic uniqueness key for one imported CSR activity row.
 * The detailed CSV has no project identifier, so identity is the combination
 * of matched company + remaining activity fields.
 *
 * @param {string} companyId
 * @param {object} fields
 */
function buildUniquenessKey(companyId, fields) {
  const amount = Number(fields.amountSpentCrore || 0).toFixed(6);

  return [
    companyId,
    fields.financialYear || '',
    fields.psuStatus || '',
    fields.state || '',
    fields.developmentSector || '',
    fields.subDevelopmentSector || '',
    amount,
  ]
    .map((part) => String(part).trim().toLowerCase())
    .join('|');
}

/**
 * @param {Record<string, string>} row
 * @param {string} field
 */
function getRowValue(row, field) {
  const target = field.trim().toLowerCase();
  const key = Object.keys(row).find((k) => k.trim().toLowerCase() === target);
  return key ? row[key] : undefined;
}

/**
 * @param {Record<string, string>} row
 */
function normalizeCsrActivityRow(row) {
  const companyName = parseText(getRowValue(row, 'Company Name'));
  const amountRaw = getRowValue(row, 'Project Amount Spent (In INR Cr.)');

  return {
    companyName,
    companyNameKey: buildCompanyNameKey(companyName),
    financialYear: parseText(getRowValue(row, 'Financial Year')),
    psuStatus: parseText(getRowValue(row, 'PSU/Non-PSU')),
    state: parseText(getRowValue(row, 'CSR State')),
    developmentSector: parseText(getRowValue(row, 'CSR Development Sector')),
    subDevelopmentSector: parseText(getRowValue(row, 'CSR Sub Development Sector')),
    amountSpentCrore: parseNumeric(amountRaw, 0),
  };
}

/**
 * @param {string} filePath
 */
function parseCsrActivityCsv(filePath) {
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

  const headers = records.length > 0 ? Object.keys(records[0]) : CSR_ACTIVITY_CSV_HEADERS;

  return { rows: records, headers, absolutePath };
}

/**
 * Import detailed CSR activity rows and attach them to existing Company records.
 *
 * Unmatched company names are reported and skipped; no fake companies are created.
 *
 * @param {string} filePath
 * @param {{ dryRun?: boolean }} [options]
 */
async function importCsrActivitiesFromCsv(filePath, options = {}) {
  const { dryRun = false } = options;
  const sourceName = path.basename(filePath);

  const summary = {
    totalRows: 0,
    inserted: 0,
    updated: 0,
    unmatched: 0,
    failed: 0,
    unmatchedCompanies: {},
    errors: [],
  };

  const { rows, headers } = parseCsrActivityCsv(filePath);
  const headerValidation = validateCsrActivityCsvHeaders(headers);

  if (!headerValidation.valid) {
    throw new Error(
      `CSV header validation failed. Missing columns: ${headerValidation.missing.join(', ')}`
    );
  }

  summary.totalRows = rows.length;

  const companies = await Company.find({})
    .select('_id companyNameKey')
    .lean();
  const companiesByKey = new Map(
    companies.map((company) => [company.companyNameKey, company])
  );

  const matchedCompanyIds = new Set();

  for (let i = 0; i < rows.length; i += 1) {
    const rowNumber = i + 2;
    const rawRow = rows[i];

    try {
      const doc = normalizeCsrActivityRow(rawRow);
      const validation = validateCsrActivityDocument(doc);

      if (!validation.valid) {
        summary.failed += 1;
        summary.errors.push({
          row: rowNumber,
          company_name: doc.companyName || '(unknown)',
          errors: validation.errors,
        });
        continue;
      }

      const company = companiesByKey.get(doc.companyNameKey);

      if (!company) {
        summary.unmatched += 1;
        const name = doc.companyName;
        summary.unmatchedCompanies[name] = (summary.unmatchedCompanies[name] || 0) + 1;
        continue;
      }

      if (dryRun) {
        summary.inserted += 1;
        continue;
      }

      const uniquenessKey = buildUniquenessKey(company._id.toString(), doc);
      const payload = {
        company: company._id,
        financialYear: doc.financialYear,
        psuStatus: doc.psuStatus,
        state: doc.state,
        developmentSector: doc.developmentSector,
        subDevelopmentSector: doc.subDevelopmentSector,
        amountSpentCrore: doc.amountSpentCrore,
        uniquenessKey,
        sourceName,
      };

      const existing = await CSRActivity.findOne({ uniquenessKey }).select('_id').lean();

      if (existing) {
        await CSRActivity.updateOne({ _id: existing._id }, { $set: payload });
        summary.updated += 1;
      } else {
        await CSRActivity.create(payload);
        summary.inserted += 1;
      }

      matchedCompanyIds.add(company._id.toString());
    } catch (err) {
      summary.failed += 1;
      summary.errors.push({
        row: rowNumber,
        company_name:
          rawRow['Company Name'] || rawRow.company_name || '(unknown)',
        errors: [err.message],
      });
    }
  }

  if (!dryRun) {
    const retrievedAt = new Date();

    await Promise.all(
      [...matchedCompanyIds].map((companyId) =>
        Source.updateOne(
          {
            company: companyId,
            sourceType: SOURCE_TYPE,
            sourceName,
          },
          {
            $setOnInsert: {
              company: companyId,
              sourceType: SOURCE_TYPE,
              sourceName,
              retrievedAt,
            },
          },
          { upsert: true }
        )
      )
    );
  }

  return summary;
}

module.exports = {
  buildUniquenessKey,
  normalizeCsrActivityRow,
  parseCsrActivityCsv,
  importCsrActivitiesFromCsv,
};
