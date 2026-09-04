# AI integration (Task 14)

Node.js is the authenticated application gateway. The Python FastAPI service at `AI_SERVICE_URL` (default `http://localhost:8000`) owns classification, extraction, verification, freshness, scoring, recommendations, and outreach generation. Gemini/OpenAI/Chroma credentials stay on the AI service.

## Configuration

```
AI_SERVICE_URL=http://localhost:8000
AI_SERVICE_TIMEOUT_MS=30000
```

## Product routes

Protected by `requireAuth` + `ADMIN` / `FUNDRAISING_STAFF`. Fundraising staff may score, recommend, and run outreach only on leads they created or are assigned to. Sending is never autonomous: Node requires an approved draft, records the approving user, and preserves AI `403` for unapproved send.

## Discovery limitation

`POST /api/companies/discover` calls AI document search and matches hits to existing MongoDB `Company` records by normalized name. It does not crawl the web, run CSV import, or create companies.

## Evidence

Evidence is stored only when the AI response includes the agreed fields (`company`, `financial_year`, `document_type`, `document_version`, `page`, `source_url`, `relevant_source_text`, `document_hash`). Missing evidence is not treated as proof that WASH focus was lost.
