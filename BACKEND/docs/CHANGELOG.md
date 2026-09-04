# Changelog

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
