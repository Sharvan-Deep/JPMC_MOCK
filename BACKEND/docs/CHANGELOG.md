# Backend Changelog

Concise log of backend changes. One entry per task.

---

## 2026-09-04 — Database models & CSV import foundation

**Feature:** Initial Mongoose schemas, DB config, and idempotent company CSV import.

**Files created:**
- `src/models/` — User, EmailOTP, Company, Lead, LeadNote, LeadActivity, CSRPolicy, Source, index.js
- `src/config/constants.js`, `src/config/database.js`
- `src/services/companyImportService.js`
- `src/validators/companyImportValidator.js`
- `src/utils/dataNormalization.js`, `src/utils/otpHash.js`
- `src/scripts/importCompanies.js`
- `src/app.js`, `src/server.js` (minimal shells)
- `package.json`, `.env.example`, `.gitignore`
- `data/03_company_ai_ready_summary.csv` (sample)

**Notes:**
- `companyNameKey` (normalized name) used for import dedup; exact match only.
- Multi-value CSV fields parsed as arrays (`|` / `;` / `,` delimiters).
- Partial unique index on Lead prevents multiple active leads per company.
- No auth controllers, API routes, or AI models implemented yet.

**Pending / assumptions:**
- Real `03_company_ai_ready_summary.csv` not in repo; sample CSV used for structure validation.
- Delimiter assumptions should be re-verified against production CSV.

---

## 2026-09-04 — Pushed to `origin/BACKEND`

**Feature:** Committed `BACKEND/` folder only to GitHub BACKEND branch.

**Files:** All files under `BACKEND/` (commit `aafc0a2`).

**Notes:** Root-level duplicate `package.json` / `.env.example` left untracked intentionally.

---

## 2026-09-04 — Development workflow rules

**Feature:** Established efficiency rules for incremental backend development.

**Files created:** `docs/CHANGELOG.md`

**Notes:** Future tasks should touch only relevant files, reuse existing architecture, and append to this log.

---

## 2026-09-04 — Company Management APIs

**Feature:** Company list, detail, and summary REST endpoints.

**Files created:**
- `src/controllers/companyController.js`
- `src/services/companyService.js`
- `src/routes/companyRoutes.js`
- `src/validators/companyQueryValidator.js`
- `src/utils/objectId.js`, `src/utils/asyncHandler.js`
- `src/middleware/errorHandler.js`

**Files modified:**
- `src/app.js` — registered `/api/companies` routes and error handler

**Notes:**
- List supports pagination, name search (case-insensitive regex), filters (`latestFinancialYear`, `state`, `csrSector`), and whitelisted sorting.
- `companyNameKey` excluded from API responses.
- Default: `page=1`, `limit=20` (max 100), `sortBy=company_name`, `sortOrder=desc`.
- No auth middleware applied (deferred to auth module).

**Testing status:** No automated test framework in project; verified app loads and routes register. Manual test with MongoDB required for full endpoint verification.

**Pending / assumptions:**
- MongoDB must be running with imported company data for live API calls.
