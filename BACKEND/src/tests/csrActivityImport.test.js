/**
 * CSR activity CSV import tests.
 * Requires MongoDB (MONGODB_URI).
 */
require('dotenv').config();

const { describe, it, before, after } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { connectDatabase, disconnectDatabase } = require('../config/database');
const { Company, CSRActivity, Source } = require('../models');
const {
  normalizeCsrActivityRow,
  importCsrActivitiesFromCsv,
} = require('../services/csrActivityImportService');
const csrService = require('../services/csrService');
const { createTestRun } = require('./helpers/testIsolation');

const run = createTestRun();
const CSV_HEADERS = [
  'Company Name',
  'Financial Year',
  'PSU/Non-PSU',
  'CSR State',
  'CSR Development Sector',
  'CSR Sub Development Sector',
  'Project Amount Spent (In INR Cr.)',
].join(',');

let matchedCompany;
let csvPath;

function writeCsv(rows) {
  fs.writeFileSync(csvPath, [CSV_HEADERS, ...rows].join('\n'), 'utf8');
}

before(async () => {
  await connectDatabase();

  matchedCompany = await Company.create({
    company_name: `CSR Import Co ${run.id}`,
    companyNameKey: `csr import co ${run.id}`,
  });

  csvPath = path.join(os.tmpdir(), `csr-activity-import-${run.id}.csv`);
});

after(async () => {
  if (matchedCompany?._id) {
    await CSRActivity.deleteMany({ company: matchedCompany._id });
    await Source.deleteMany({ company: matchedCompany._id });
    await Company.deleteMany({ _id: matchedCompany._id });
  }

  if (csvPath && fs.existsSync(csvPath)) {
    fs.unlinkSync(csvPath);
  }

  await disconnectDatabase();
});

describe('CSR activity CSV import', () => {
  it('parses numeric spend from a CSV row', () => {
    const doc = normalizeCsrActivityRow({
      'Company Name': 'Acme',
      'Financial Year': '2024-25',
      'PSU/Non-PSU': 'Non-PSU',
      'CSR State': 'Maharashtra',
      'CSR Development Sector': 'Health',
      'CSR Sub Development Sector': 'Sanitation',
      'Project Amount Spent (In INR Cr.)': '12.75',
    });

    assert.equal(doc.amountSpentCrore, 12.75);
    assert.equal(doc.companyNameKey, 'acme');
  });

  it('imports matched rows and skips unmatched companies', async () => {
    writeCsv([
      `"CSR Import Co ${run.id}",2024-25,Non-PSU,Maharashtra,Safe drinking water,Rural water,1.5`,
      `"Unknown Corp ${run.id}",2024-25,PSU,Karnataka,Sanitation,Toilets,2.25`,
      `"CSR Import Co ${run.id}",2023-24,Non-PSU,Gujarat,Hygiene,Handwash,0.5`,
    ]);

    const summary = await importCsrActivitiesFromCsv(csvPath);

    assert.equal(summary.totalRows, 3);
    assert.equal(summary.inserted, 2);
    assert.equal(summary.unmatched, 1);
    assert.equal(summary.unmatchedCompanies[`Unknown Corp ${run.id}`], 1);
    assert.equal(summary.failed, 0);

    const stored = await CSRActivity.find({ company: matchedCompany._id }).lean();
    assert.equal(stored.length, 2);
    assert.ok(stored.every((row) => row.company.toString() === matchedCompany._id.toString()));

    const sources = await Source.find({ company: matchedCompany._id, sourceType: 'CSV' }).lean();
    assert.equal(sources.length, 1);
    assert.equal(sources[0].sourceName, path.basename(csvPath));
  });

  it('is idempotent when the same CSV is imported twice', async () => {
    const before = await CSRActivity.countDocuments({ company: matchedCompany._id });
    const summary = await importCsrActivitiesFromCsv(csvPath);

    assert.equal(summary.inserted, 0);
    assert.equal(summary.updated, 2);
    assert.equal(summary.unmatched, 1);

    const after = await CSRActivity.countDocuments({ company: matchedCompany._id });
    assert.equal(after, before);
  });

  it('returns imported activities from the CSR overview API', async () => {
    const overview = await csrService.getCsrOverview(matchedCompany._id.toString());

    assert.equal(overview.activities.count, 2);
    assert.equal(overview.activities.totalSpendCrore, 2);
    assert.ok(overview.availableFinancialYears.includes('2024-25'));
    assert.ok(overview.activities.recent.some((row) => row.state === 'Maharashtra'));
    assert.equal(overview.activities.recent[0].passwordHash, undefined);
  });
});
