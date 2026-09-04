/**
 * CLI script to import detailed CSR activity rows and attach them to Company.
 *
 * Usage:
 *   node src/scripts/importCsrActivities.js [path-to-csv]
 *   npm run import:csr-activities
 *
 * Environment:
 *   MONGODB_URI              — MongoDB connection string (required)
 *   CSR_ACTIVITY_CSV_PATH    — Default CSV path if no argument provided
 *
 * Unmatched company names are skipped (no fake companies are created).
 */
require('dotenv').config();

const path = require('path');
const { connectDatabase, disconnectDatabase } = require('../config/database');
const { importCsrActivitiesFromCsv } = require('../services/csrActivityImportService');

async function main() {
  const csvPath =
    process.argv[2] ||
    process.env.CSR_ACTIVITY_CSV_PATH ||
    'data/csr_activities.csv';

  const resolvedPath = path.resolve(csvPath);
  const dryRun = process.argv.includes('--dry-run');

  console.log(`Importing CSR activities from: ${resolvedPath}`);
  if (dryRun) {
    console.log('DRY RUN — no database writes will be performed');
  }

  await connectDatabase();

  try {
    const summary = await importCsrActivitiesFromCsv(resolvedPath, { dryRun });

    console.log('\n--- Import Summary ---');
    console.log(`Total rows:   ${summary.totalRows}`);
    console.log(`Inserted:     ${summary.inserted}`);
    console.log(`Updated:      ${summary.updated}`);
    console.log(`Unmatched:    ${summary.unmatched}`);
    console.log(`Failed:       ${summary.failed}`);

    const unmatchedNames = Object.keys(summary.unmatchedCompanies);
    if (unmatchedNames.length > 0) {
      console.log('\n--- Unmatched companies ---');
      for (const name of unmatchedNames) {
        console.log(`${name}: ${summary.unmatchedCompanies[name]} row(s)`);
      }
    }

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
