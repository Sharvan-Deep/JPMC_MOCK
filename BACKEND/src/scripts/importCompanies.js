/**
 * CLI script to import companies from 03_company_ai_ready_summary.csv.
 *
 * Usage:
 *   node src/scripts/importCompanies.js [path-to-csv]
 *   npm run import:companies
 *
 * Environment:
 *   MONGODB_URI       — MongoDB connection string (required)
 *   COMPANY_CSV_PATH  — Default CSV path if no argument provided
 */
require('dotenv').config();

const path = require('path');
const { connectDatabase, disconnectDatabase } = require('../config/database');
const { importCompaniesFromCsv } = require('../services/companyImportService');

async function main() {
  const csvPath =
    process.argv[2] ||
    process.env.COMPANY_CSV_PATH ||
    'data/03_company_ai_ready_summary.csv';

  const resolvedPath = path.resolve(csvPath);
  const dryRun = process.argv.includes('--dry-run');

  console.log(`Importing companies from: ${resolvedPath}`);
  if (dryRun) {
    console.log('DRY RUN — no database writes will be performed');
  }

  await connectDatabase();

  try {
    const summary = await importCompaniesFromCsv(resolvedPath, { dryRun });

    console.log('\n--- Import Summary ---');
    console.log(`Total rows:  ${summary.totalRows}`);
    console.log(`Inserted:    ${summary.inserted}`);
    console.log(`Updated:     ${summary.updated}`);
    console.log(`Skipped:     ${summary.skipped}`);
    console.log(`Failed:      ${summary.failed}`);

    if (summary.errors.length > 0) {
      console.log('\n--- Errors ---');
      for (const err of summary.errors) {
        console.log(`Row ${err.row} (${err.company_name}): ${err.errors.join('; ')}`);
      }
    }
  } finally {
    await disconnectDatabase();
  }
}

main().catch((err) => {
  console.error('Import failed:', err.message);
  process.exit(1);
});
