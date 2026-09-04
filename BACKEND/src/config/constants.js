/**
 * Application-wide constants and enum values.
 * Keep in sync with Mongoose schema enums.
 */

const USER_ROLES = Object.freeze({
  ADMIN: 'ADMIN',
  FUNDRAISING_STAFF: 'FUNDRAISING_STAFF',
});

const INVITATION_STATUSES = Object.freeze({
  PENDING: 'PENDING',
  ACCEPTED: 'ACCEPTED',
  EXPIRED: 'EXPIRED',
  REVOKED: 'REVOKED',
});

/** Default role assigned to admin-created invitations. */
const DEFAULT_INVITATION_ROLE = USER_ROLES.FUNDRAISING_STAFF;

/** Required CSV headers for bulk invitation import. */
const INVITATION_CSV_HEADERS = Object.freeze(['name', 'email']);

const LEAD_STATUSES = Object.freeze({
  NEW: 'NEW',
  CONTACTED: 'CONTACTED',
  FOLLOW_UP: 'FOLLOW_UP',
  PROPOSAL_SENT: 'PROPOSAL_SENT',
  WON: 'WON',
  LOST: 'LOST',
});

/** Active lead statuses — used to prevent duplicate open leads per company. */
const ACTIVE_LEAD_STATUSES = Object.freeze([
  LEAD_STATUSES.NEW,
  LEAD_STATUSES.CONTACTED,
  LEAD_STATUSES.FOLLOW_UP,
  LEAD_STATUSES.PROPOSAL_SENT,
]);

const LEAD_PRIORITIES = Object.freeze({
  HIGH: 'HIGH',
  MEDIUM: 'MEDIUM',
  LOW: 'LOW',
});

const LEAD_ACTIVITY_TYPES = Object.freeze({
  CONTACTED: 'CONTACTED',
  CALL: 'CALL',
  EMAIL: 'EMAIL',
  MEETING: 'MEETING',
  FOLLOW_UP: 'FOLLOW_UP',
  PROPOSAL_SENT: 'PROPOSAL_SENT',
  STATUS_CHANGED: 'STATUS_CHANGED',
  OTHER: 'OTHER',
});

/**
 * Expected headers for 03_company_ai_ready_summary.csv (authoritative company dataset).
 */
const COMPANY_CSV_HEADERS = Object.freeze([
  'company_name',
  'wash_record_count',
  'financial_years',
  'states',
  'csr_sectors',
  'total_wash_spend_crore',
  'latest_financial_year',
  'total_water_spend_crore',
  'total_sanitation_spend_crore',
  'water_active_years',
  'sanitation_active_years',
  'wash_focus_evidence',
  'source',
  'source_retrieved_date',
]);

module.exports = {
  USER_ROLES,
  INVITATION_STATUSES,
  DEFAULT_INVITATION_ROLE,
  INVITATION_CSV_HEADERS,
  LEAD_STATUSES,
  ACTIVE_LEAD_STATUSES,
  LEAD_PRIORITIES,
  LEAD_ACTIVITY_TYPES,
  COMPANY_CSV_HEADERS,
};
