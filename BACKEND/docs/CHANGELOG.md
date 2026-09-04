# Changelog

## 2026-09-04 — Test data isolation for auth/invitation suites

**Feature:** Tests create unique per-run emails and delete only those records.

**Files changed:**
- `src/tests/helpers/testIsolation.js` (created)
- `src/tests/auth.test.js`
- `src/tests/invitation.test.js`

**Tests run:** `npm run test:auth`, `npm run test:invitations`

**Result:** Suites no longer wipe the users collection or remove development accounts such as `admin@jaldhaara.com`.

## 2026-09-04 — Login 500: missing JWT_ACCESS_SECRET

**Feature:** Debug/fix POST `/api/auth/login` Internal server error after successful password verification.

**Root cause:** Access-token signing required `JWT_ACCESS_SECRET`, but local `.env` only had legacy `JWT_SECRET`. Password check succeeded, then JWT creation threw.

**Files modified:**
- `src/config/jwt.js` — accept `JWT_ACCESS_SECRET` or fallback `JWT_SECRET`
- `.env` (local) — set `JWT_ACCESS_SECRET` / expiry vars

**Testing result:**
- Auth and invitation tests re-run after the fix

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
- Admin-only invite/list/resend/revoke/import via `requireAdmin` (expects `req.user` from future JWT module)
- Public `verify` and `activate` endpoints
- Resend cooldown via `INVITATION_RESEND_COOLDOWN_MINUTES`

**Tests/checks:**
- `npm run test:invitations` (requires MongoDB)
- Server starts with auth routes registered

**Assumptions/blockers:**
- JWT auth middleware not implemented; admin routes return 401 until `req.user` is attached
- `FRONTEND_URL` required when sending invitation emails

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
