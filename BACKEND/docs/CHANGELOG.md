# Changelog

Concise log of backend changes. One entry per task.

---

## 2026-09-04 — Task 14: Node.js ↔ Python AI service integration

**Feature:** Authenticated Node gateway/orchestrator for the FastAPI AI service. MongoDB remains the structured system of record. AI algorithms stay in Python.

**Files created:**
- `src/config/ai.js`
- `src/services/aiService.js`, `aiContextService.js`, `companyAiService.js`, `leadScoringService.js`, `recommendationService.js`, `outreachService.js`
- `src/models/aiEvidenceSchema.js`, `CompanyFreshnessHistory.js`, `CompanyLeadScore.js`, `CompanyRecommendation.js`, `OutreachDraft.js`, `OutreachSendAudit.js`
- `src/controllers/companyAiController.js`, `leadAiController.js`, `outreachController.js`
- `src/routes/outreachRoutes.js`
- `src/validators/aiIntegrationValidator.js`
- `src/utils/aiErrors.js`, `aiEvidence.js`
- `src/config/swagger/aiPaths.js`
- `src/tests/aiService.test.js`, `companyAi.test.js`, `leadScoring.test.js`, `recommendation.test.js`, `outreach.test.js`, `helpers/httpRequest.js`
- `docs/AI-INTEGRATION.md`

**Files modified:**
- `src/app.js`, `src/models/Company.js`, `src/models/index.js`, `src/config/constants.js`
- `src/routes/companyRoutes.js`, `src/routes/leadRoutes.js`
- `src/services/companyService.js` — exclude bulky `aiReadySummary` from list
- `src/utils/errors.js`, `src/middleware/errorHandler.js`
- `src/config/swagger.js`, `src/config/swagger/schemas.js`, `src/tests/swagger.test.js`
- `package.json`, `.env.example`

**Integration summary:** Node calls `AI_SERVICE_URL` (default `http://localhost:8000`) with timeout handling. Product routes wrap documents, freshness, scoring, copilot, and outreach. Scores/recommendations/freshness/drafts/send audits persist in MongoDB. Lead.priority is not overwritten by AI. Sending requires human approval in Node and preserves AI 403.

**Pending limitations:**
- `POST /api/companies/discover` searches the AI index and matches existing companies by name; it does not crawl, import CSVs, or create companies.
- Document extract/preprocess/index are available on the internal client but analyze uses validate + classify + search against stored CSR facts (no file-upload pipeline in Node yet).
- Python request field names may still 422 if FastAPI models differ; errors are translated, not guessed.

**Testing:** `npm run test:ai`, `npm run test:swagger`, plus existing backend suites. AI HTTP is mocked.

---

## 2026-09-04 — Company API route mounting fix

**Feature:** Mount existing Company Management routes so runtime matches Swagger.

**Root cause:** `companyRoutes` module was not registered in `app.js`; only CSR sub-routes were mounted under `/api/companies/:companyId`.

**Files created:**
- `src/routes/companyRoutes.js`
- `src/controllers/companyController.js`
- `src/services/companyService.js`
- `src/validators/companyQueryValidator.js`
- `src/utils/objectId.js`
- `src/tests/company.test.js`

**Files modified:**
- `src/app.js` — mounted `companyRoutes` at `/api/companies` before CSR nested router
- `package.json` — added `test:companies` script

**Routes now mounted:**
- `GET /api/companies`
- `GET /api/companies/:companyId`
- `GET /api/companies/:companyId/summary`

**Notes:** `/:companyId/summary` is registered before `/:companyId`. CSR routes remain on `/api/companies/:companyId/*`. Swagger paths unchanged.

**Testing:** `npm run test:companies`, `npm run test:csr`, `npm run test:swagger`

---

## 2026-09-04 — Swagger / OpenAPI documentation

**Feature:** Interactive Swagger UI and OpenAPI 3.0 JSON for all existing backend endpoints.

**Files created:**
- `src/config/swagger.js`
- `src/config/swagger/schemas.js`
- `src/config/swagger/paths.js`
- `src/tests/swagger.test.js`

**Files modified:**
- `src/app.js` — mounted `/api-docs` and `/api-docs.json`
- `package.json` — added `swagger-ui-express`, `test:swagger` script

**Notes:**
- `bearerAuth` JWT scheme applied to protected routes; login, refresh, forgot/reset password, invitation verify/activate remain public.
- Refresh/logout documented as cookie-based (`refreshToken` on `/api/auth` path).

**Testing:** `npm run test:swagger` — verifies UI HTML, JSON spec, security metadata, and operation count.

---

## 2026-09-04 — CSR activity CSV import

**Feature:** Import detailed CSR activity rows into `CSRActivity` and expose them on the company CSR overview.

**Files created:**
- `src/models/CSRActivity.js`
- `src/services/csrActivityImportService.js`
- `src/validators/csrActivityImportValidator.js`
- `src/scripts/importCsrActivities.js`
- `src/tests/csrActivityImport.test.js`
- CSR API files restored onto this branch so `/api/companies/:companyId/csr` is available

**Files modified:**
- `src/models/index.js`
- `src/config/constants.js`
- `src/services/csrService.js` — overview includes imported activity totals
- `src/app.js` — mounted CSR routes
- `package.json` — `import:csr-activities`, `test:csr`, `test:csr-import`
- `.env.example` — `CSR_ACTIVITY_CSV_PATH`

**Notes:**
- Matching uses existing `companyNameKey` (trim + lowercase). Unmatched names are skipped; no fake companies are created.
- Idempotency uses a deterministic `uniquenessKey` of company + year + PSU + state + sector + sub-sector + spend.
- Source metadata is upserted as `sourceType=CSV` on the existing Source model.

**Pending:**
- Company names that do not exactly match imported Company records remain unmatched until names are aligned.
- The detailed CSV has no project ID, so identical rows collapse into one activity.

---

## 2026-09-04 — User Management

**Feature:** Admin-only user management for existing provisioned accounts.

**Files created:**
- `src/validators/userValidator.js`
- `src/services/userService.js`
- `src/controllers/userController.js`
- `src/routes/userRoutes.js`
- `src/tests/user.test.js`

**Files modified:**
- `src/app.js` — mounted `/api/users`
- `package.json` — added `test:users`

**Endpoints:**
- `GET /api/users` — list with pagination, search, role/active filters, sorting
- `GET /api/users/:userId` — safe user detail
- `PATCH /api/users/:userId` — update name only
- `PATCH /api/users/:userId/role` — change role
- `PATCH /api/users/:userId/status` — activate/deactivate

**Authorization:** All endpoints require `requireAuth` + `requireAdmin`.

**Tests:** `npm run test:users`; auth, invitation, password-reset, and lead regression suites.

**Assumptions:**
- No public signup or direct user creation endpoints.
- Admins cannot self-demote or self-deactivate; last active admin is protected.
- Deactivated users are blocked by existing auth/login/refresh checks.

---

## 2026-09-04 — Dashboard APIs

**Feature:** Read-only dashboard endpoints aggregating company, WASH, lead, and activity metrics.

**Files created:**
- `src/validators/dashboardValidator.js`
- `src/services/dashboardService.js`
- `src/controllers/dashboardController.js`
- `src/routes/dashboardRoutes.js`
- `src/tests/dashboard.test.js`

**Files modified:**
- `src/app.js` — mounted `/api/dashboard`
- `package.json` — added `test:dashboard`

**Endpoints:**
- `GET /api/dashboard/summary` — company, WASH, lead, and activity metrics
- `GET /api/dashboard/top-prospects` — active leads sorted by priority
- `GET /api/dashboard/recent-leads` — recently updated leads
- `GET /api/dashboard/follow-ups` — `FOLLOW_UP` leads oldest first

**Tests:** `npm run test:dashboard`; lead, auth, invitation, and password-reset regression suites.

**Assumptions:**
- `companiesWithWASH` counts companies with `wash_record_count > 0` or `total_wash_spend_crore > 0`.
- Follow-up queue uses `FOLLOW_UP` status ordered by `updatedAt` (no follow-up date field in schema).
- Recent activity count uses a 30-day window on `LeadActivity.createdAt`.
- Top prospects include only active (non-terminal) leads; priority sort uses stored `Lead.priority`.

---

## 2026-09-04 — Lead Management

**Feature:** Backend Lead Management module for fundraising prospect tracking (company-linked leads, notes, activities, assignment).

**Files created:**
- `src/validators/leadValidator.js`
- `src/services/leadService.js`
- `src/controllers/leadController.js`
- `src/routes/leadRoutes.js`
- `src/tests/lead.test.js`

**Files modified:**
- `src/app.js` — mounted `/api/leads`
- `package.json` — added `test:leads`

**Endpoints:**
- `POST /api/leads` — create lead from company
- `GET /api/leads` — list with pagination, search, filters, sorting
- `GET /api/leads/:leadId` — detail with notes and activities
- `PATCH /api/leads/:leadId` — update status, priority, assignment (admin)
- `PATCH /api/leads/:leadId/assign` — assign to staff (admin)
- `DELETE /api/leads/:leadId` — archive active lead to LOST
- `POST/GET /api/leads/:leadId/notes`
- `POST/GET /api/leads/:leadId/activities`

**Tests:** `npm run test:leads`; auth, invitation, and password-reset suites re-run for regression.

**Assumptions:**
- New leads default `assignedTo` to creator (schema requires assignee).
- DELETE archives active leads to `LOST` instead of physical deletion.
- `STATUS_CHANGED` activities are system-generated on status updates.
- Staff may view all leads; updates/notes/activities require assigned-or-creator access.

---

## 2026-09-04 — Password Reset

**Feature:** Secure forgot-password and reset-password flow with one-time hashed tokens and session revocation.

**Files created:**
- `src/models/PasswordResetToken.js`
- `src/services/passwordResetService.js`, `passwordResetEmailService.js`
- `src/controllers/passwordResetController.js`
- `src/validators/passwordResetValidator.js`
- `src/utils/passwordResetHelpers.js`
- `src/tests/passwordReset.test.js`

**Files modified:**
- `src/routes/authRoutes.js` — `POST /forgot-password`, `POST /reset-password`
- `src/models/index.js`
- `.env.example` — `PASSWORD_RESET_EXPIRES_HOURS`, `PASSWORD_RESET_COOLDOWN_MINUTES`
- `package.json` — `test:password-reset`

**Security behavior:**
- SHA-256 hashed one-time reset tokens; generic forgot-password response
- Reset revokes refresh sessions and invalidates other reset tokens
- Cooldown prevents rapid reset-email requests

**Tests:** `npm run test:password-reset`, plus auth/invitation regression suites.

**Assumptions/blockers:** `FRONTEND_URL` required for reset links; user must log in again after reset.

---

## 2026-09-04 — Test data isolation for auth/invitation suites

**Feature:** Tests create unique per-run emails and delete only those records.

**Files changed:**
- `src/tests/helpers/testIsolation.js` (created)
- `src/tests/auth.test.js`
- `src/tests/invitation.test.js`

**Tests run:** `npm run test:auth`, `npm run test:invitations`

**Result:** Suites no longer wipe the users collection or remove development accounts such as `admin@jaldhaara.com`.

---

## 2026-09-04 — Login 500: missing JWT_ACCESS_SECRET

**Feature:** Debug/fix POST `/api/auth/login` Internal server error after successful password verification.

**Root cause:** Access-token signing required `JWT_ACCESS_SECRET`, but local `.env` only had legacy `JWT_SECRET`. Password check succeeded, then JWT creation threw.

**Files modified:**
- `src/config/jwt.js` — accept `JWT_ACCESS_SECRET` or fallback `JWT_SECRET`
- `.env` (local) — set `JWT_ACCESS_SECRET` / expiry vars

**Testing result:**
- Auth and invitation tests re-run after the fix

---

## 2026-09-04 — Development admin bootstrap/reset

**Feature:** Local-only CLI script to create or reset a development Admin account password.

**Files created:**
- `src/scripts/bootstrapAdmin.js`

**Files modified:**
- `package.json` — `bootstrap:admin` script
- `.env.example` — `ALLOW_ADMIN_BOOTSTRAP`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `ADMIN_NAME`

**Testing result:**
- Script exits when `ALLOW_ADMIN_BOOTSTRAP` is not `true`
- Script creates/updates Admin with bcrypt-hashed password; no password logged
- `POST /api/auth/login` works with bootstrapped credentials

**Security note:**
- Not exposed via HTTP; requires explicit `ALLOW_ADMIN_BOOTSTRAP=true`
- Credentials must be set only in local `.env`, never committed

---

## 2026-09-04 — JWT + email/password authentication

**Feature:** Short-lived access JWT, long-lived hashed refresh tokens in HttpOnly cookies, login/refresh/logout/me endpoints.

**Files created:**
- `src/models/RefreshToken.js`
- `src/services/authService.js`
- `src/controllers/authController.js`
- `src/middleware/requireAuth.js`, `requireRole.js`
- `src/validators/authValidator.js`
- `src/config/jwt.js`, `cors.js`, `cookies.js`
- `src/utils/userSerializer.js`
- `src/tests/auth.test.js`

**Files modified:**
- `src/routes/authRoutes.js` — login, refresh, logout, me; `requireAuth` on admin invitation routes
- `src/middleware/requireAdmin.js` — uses `requireRole('ADMIN')`
- `src/app.js` — `cors`, `cookie-parser`
- `src/models/index.js` — export `RefreshToken`
- `src/utils/tokenHash.js` — refresh token helpers
- `.env.example` — JWT/cors/cookie vars
- `package.json` — `jsonwebtoken`, `cookie-parser`, `cors`, `test:auth`

**Key changes:**
- Access JWT payload: `{ sub, role }`; refresh tokens stored hashed with rotation/revocation
- Generic invalid-login responses; inactive users blocked
- CORS credentials with configurable `CORS_ORIGINS`

**Tests/checks:**
- `npm run test:auth` — 18 tests
- `npm run test:invitations` — regression

**Assumptions/blockers:**
- `JWT_ACCESS_SECRET` required at runtime
- Refresh token delivered only via HttpOnly cookie (not JSON)

---

## 2026-09-04 — Admin Invitation + Account Activation

**Feature:** Admin-provisioned user invitations with secure token hashing, email delivery, CSV bulk import, and account activation.

**Files created:**
- `src/models/Invitation.js`
- `src/controllers/invitationController.js`
- `src/routes/authRoutes.js`
- `src/services/invitationService.js`
- `src/services/invitationEmailService.js`
- `src/middleware/requireAdmin.js`
- `src/middleware/errorHandler.js`
- `src/validators/invitationValidator.js`
- `src/utils/tokenHash.js`, `email.js`, `password.js`, `errors.js`, `asyncHandler.js`, `invitationHelpers.js`
- `src/tests/invitation.test.js`

**Files modified:**
- `src/models/User.js` — added `passwordHash`, `isEmailVerified`
- `src/models/index.js` — export `Invitation`
- `src/config/constants.js` — invitation enums
- `src/app.js` — register `/api/auth` routes and error handler
- `.env.example` — `FRONTEND_URL`, invitation settings
- `package.json` — `bcryptjs`, `multer`, `test:invitations` script

**Key changes:**
- SHA-256 hashed invitation tokens; raw tokens only in email URLs
- Admin-only invite/list/resend/revoke/import via `requireAdmin`
- Public `verify` and `activate` endpoints
- Resend cooldown via `INVITATION_RESEND_COOLDOWN_MINUTES`

**Tests/checks:**
- `npm run test:invitations` (requires MongoDB)
- Server starts with auth routes registered

---

## 2026-09-04 — Mail service foundation

**Feature:** Reusable Nodemailer-based email service for future transactional emails (invitations, password reset, activation, etc.).

**Files created:**
- `src/config/mail.js`
- `src/services/mailService.js`
- `src/scripts/testMail.js`

**Files modified:**
- `.env.example` — added `MAIL_*` variables and optional `MAIL_TEST_RECIPIENT`
- `package.json` — added `test:mail` script

**Testing result:**
- Backend starts successfully (no mail integration at startup).
- Invalid/missing mail config returns a clear error from the test script.
- Live SMTP send requires valid Gmail app-password credentials in `.env` (not committed).

**Assumptions / blockers:**
- `MAIL_USER` is used as the SMTP login and the envelope "From" address; `MAIL_FROM_NAME` sets the display name only.
- Gmail requires an app password (not the account login password) when 2FA is enabled.
- No API endpoint added for mail testing; use `npm run test:mail`.

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
- Auth for these routes is applied by the later auth module (`requireAuth` + staff/admin roles).

**Pending / assumptions:**
- MongoDB must be running with imported company data for live API calls.

---

## 2026-09-04 — Development workflow rules

**Feature:** Established efficiency rules for incremental backend development.

**Files created:** `docs/CHANGELOG.md`

**Notes:** Future tasks should touch only relevant files, reuse existing architecture, and append to this log.

---

## 2026-09-04 — Pushed to `origin/BACKEND`

**Feature:** Committed `BACKEND/` folder only to GitHub BACKEND branch.

**Files:** All files under `BACKEND/` (commit `aafc0a2`).

**Notes:** Root-level duplicate `package.json` / `.env.example` left untracked intentionally.

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

**Pending / assumptions:**
- Real `03_company_ai_ready_summary.csv` not in repo; sample CSV used for structure validation.
- Delimiter assumptions should be re-verified against production CSV.
