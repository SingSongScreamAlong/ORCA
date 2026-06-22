// TypeScript types mirroring the ORCA API contract (backend/app/schemas).
// Kept in sync with ontology/schema and docs/ontology_v0.1.md.

export type Role =
  | "admin"
  | "case_manager"
  | "analyst"
  | "reviewer"
  | "viewer"
  | "partner_export_viewer";

export interface User {
  id: string;
  username: string;
  display_name: string;
  role: Role;
  created_at: string;
}

export interface CurrentUser {
  id: string;
  username: string;
  display_name: string;
  role: Role;
  capabilities: string[];
}

// v0.6 per-case authorization.
export type CaseRole =
  | "case_manager"
  | "analyst"
  | "reviewer"
  | "viewer"
  | "partner_export_viewer";

export type MembershipStatus = "active" | "inactive" | "revoked";

export interface CaseMember {
  id: string; // membership id
  case_id: string;
  user_id: string;
  username: string;
  display_name: string;
  global_role: Role;
  case_role: CaseRole;
  status: MembershipStatus;
  assigned_by: string;
  assigned_at: string;
  notes: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export type Origin = "system_proposed" | "analyst_created" | "imported";

// v0.2 approval lifecycle (the status badges).
export type ReviewStatus = "proposed" | "approved" | "rejected" | "needs_more_review";

export type ConfidenceBand = "unverified" | "low" | "medium" | "high" | "confirmed";

export type CaseStatus = "open" | "active" | "on_hold" | "closed";

export type EntityType =
  | "phone_number"
  | "alias"
  | "account"
  | "username"
  | "location"
  | "vehicle"
  | "image"
  | "advertisement"
  | "tattoo_marker";

export type RelationshipType =
  | "shared_phone"
  | "shared_image"
  | "shared_location"
  | "shared_account"
  | "appears_with"
  | "analyst_confirmed";

export type SourceType = "website" | "dataset" | "manual_upload" | "tip" | "document";
export type SourceReliability = "unknown" | "low" | "medium" | "high";

export type EvidenceType =
  | "screenshot"
  | "document"
  | "image"
  | "video"
  | "web_archive"
  | "analyst_note"
  | "partner_file"
  | "other";

export type EvidenceStatus =
  | "proposed"
  | "approved"
  | "rejected"
  | "needs_more_review"
  | "quarantined";

export type EvidenceDecision = "approve" | "reject" | "needs_more_review" | "quarantine";

export type ReviewItemType =
  | "proposed_observation"
  | "proposed_relationship"
  | "proposed_cluster"
  | "flagged_observation";

export type ReviewDecision = "approve" | "reject" | "needs_more_review";

export interface Handling {
  lawful_basis: string | null;
  requires_legal_review: boolean;
  sensitive: boolean;
  notes: string | null;
}

export interface Observation {
  id: string;
  case_id: string | null;
  timestamp: string;
  source_id: string;
  collector: string;
  location: string | null;
  notes: string | null;
  confidence: number;
  status: ReviewStatus;
  entity_ids: string[];
  handling: Handling;
  decided_by: string | null;
  decided_at: string | null;
  created_at: string;
}

export interface Entity {
  id: string;
  entity_type: EntityType;
  value: string;
  confidence: number;
  created_at: string;
}

export interface Relationship {
  id: string;
  case_id: string | null;
  source_entity_id: string;
  target_entity_id: string;
  relationship_type: RelationshipType;
  confidence: number;
  origin: Origin;
  status: ReviewStatus;
  observation_ids: string[];
  created_at: string;
  updated_at: string;
}

export interface Cluster {
  id: string;
  title: string;
  status: "proposed" | "active" | "archived" | "rejected";
  confidence: number;
  origin: Origin;
  entity_ids: string[];
  observation_ids: string[];
  created_at: string;
}

export interface Case {
  id: string;
  title: string;
  status: CaseStatus;
  owner: string;
  summary: string | null;
  legal_notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface CaseCounts {
  observations_total: number;
  observations_approved: number;
  observations_pending: number;
  relationships: number;
}

export interface CaseDetail {
  case: Case;
  counts: CaseCounts;
}

export interface ReviewItem {
  id: string;
  item_type: ReviewItemType;
  subject_type: string;
  subject_id: string;
  case_id: string | null;
  rationale: string;
  confidence: number;
  evidence_ids: string[];
  status: ReviewStatus;
  decided_by: string | null;
  decided_at: string | null;
  created_at: string;
}

export interface Report {
  id: string;
  case_id: string;
  title: string;
  author: string;
  status: "draft" | "in_review" | "final";
  body: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReportPackageCounts {
  approved_observations: number;
  approved_relationships: number;
  cited_evidence: number;
}

export interface ReportPackageSummary {
  id: string;
  case_id: string;
  title: string;
  status: "draft" | "in_review" | "final";
  handling_level: string;
  generated_by: string;
  counts: ReportPackageCounts;
  caveats: string[];
  report_sha256: string;
  manifest_sha256: string;
  created_at: string;
}

// v1.0 Analyst Copilot (propose-only AI assistance).
export interface AiMeta {
  generated_by_ai: boolean;
  provider: string;
  generated_at: string;
  source_material_ids: string[];
  status: string;
  requires_human_review: boolean;
}

export interface AiSuggestion {
  kind: string;
  text: string;
  rationale: string | null;
}

export interface AiProposedEntity {
  entity_type: string;
  value: string;
  confidence: number;
  rationale: string;
  source_observation_ids: string[];
  possible_duplicate_of: string | null;
}

export interface AiProposedRelationship {
  relationship_type: string;
  source_value: string;
  target_value: string;
  confidence: number;
  rationale: string;
  supporting_observation_ids: string[];
}

export interface AiReportDraftSuggestion {
  section_title: string;
  draft_markdown: string;
  cited_observation_ids: string[];
}

export interface AiCitationGap {
  location: string;
  claim: string;
  issue: string;
}

export interface AiUnsupportedClaimFlag {
  claim: string;
  reason: string;
}

export interface AiAssistResult {
  case_id: string;
  assist_type: string;
  meta: AiMeta;
  summary: string | null;
  suggestions: AiSuggestion[];
  proposed_entities: AiProposedEntity[];
  proposed_relationships: AiProposedRelationship[];
  report_draft: AiReportDraftSuggestion | null;
  citation_gaps: AiCitationGap[];
  unsupported_claims: AiUnsupportedClaimFlag[];
  notes: string[];
}

export type TimelineEventKind =
  | "observation_approved"
  | "relationship_created"
  | "relationship_approved";

export interface TimelineEvent {
  timestamp: string;
  kind: TimelineEventKind;
  summary: string;
  ref_type: string;
  ref_id: string;
}

export interface AuditEntry {
  id: string;
  actor_id: string;
  action: string;
  target_type: string;
  target_id: string;
  case_id: string | null;
  context: Record<string, unknown>;
  created_at: string;
}

export interface Source {
  id: string;
  source_type: SourceType;
  name: string;
  identifier: string | null;
  reliability: SourceReliability;
  description: string | null;
  created_at: string;
}

export interface LegalFlags {
  lawful_basis: string | null;
  requires_legal_review: boolean;
  sensitive: boolean;
  partner_approved: boolean;
}

export interface EvidenceItem {
  id: string;
  case_id: string;
  source_id: string;
  observation_id: string | null;
  title: string;
  description: string | null;
  evidence_type: EvidenceType;
  storage_uri: string | null;
  original_filename: string | null;
  mime_type: string | null;
  size_bytes: number | null;
  sha256: string | null;
  captured_at: string | null;
  captured_by: string | null;
  access_method: string;
  legal_flags: LegalFlags;
  handling_notes: string | null;
  status: EvidenceStatus;
  has_bytes: boolean;
  created_by: string;
  created_at: string;
}

export interface EvidenceVerifyResult {
  evidence_id: string;
  has_bytes: boolean;
  recorded_sha256: string | null;
  computed_sha256: string | null;
  verified: boolean | null;
  message: string;
}

export interface GraphNode {
  id: string;
  entity_type: EntityType;
  value: string;
}

export interface GraphEdge {
  id: string;
  source_entity_id: string;
  target_entity_id: string;
  relationship_type: RelationshipType;
  confidence: number;
}

export interface GraphView {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface DashboardSummary {
  counts: {
    observations: number;
    relationships: number;
    pending_review: number;
    cases: number;
  };
  recent_observations: Observation[];
  recent_relationships: Relationship[];
  review_queue: ReviewItem[];
  system_health: {
    status: string;
    storage_backend: string;
  };
}

// --- Foundry integration (admin-only, read-only previews) ----------------------

export interface FoundryOntology {
  apiName: string;
  displayName?: string;
  description?: string;
  rid?: string;
}

export interface FoundryObjectType {
  apiName: string;
  displayName?: string;
  description?: string;
  primaryKey?: string;
}

export interface FoundryDiscover {
  mode: "mock" | "real";
  ontologies: FoundryOntology[];
  object_types?: FoundryObjectType[];
}

export interface FoundryObjectsResult {
  mode: "mock" | "real";
  object_type: string;
  count: number;
  objects: Record<string, unknown>[];
}

export interface FoundryImportResult {
  mode: "mock" | "real";
  object_type: string;
  entity_type: string;
  value_property: string;
  read: number;
  created: number;
  resolved_existing: number;
  skipped: number;
  entities: Entity[];
}

// --- Hunting Grounds source/NAI registry ---------------------------------------

export type HuntingSourceStatus =
  | "proposed"
  | "authorized"
  | "monitored"
  | "suspended"
  | "retired"
  | "rejected";

export type HuntingSourceCategory =
  | "escort_listing"
  | "classified"
  | "forum"
  | "social"
  | "aggregator"
  | "other";

export interface HuntingTransition {
  from_status: HuntingSourceStatus | null;
  to_status: HuntingSourceStatus;
  by: string;
  at: string;
  note: string | null;
}

export interface HuntingSource {
  id: string;
  name: string;
  url: string;
  category: HuntingSourceCategory;
  aor: string;
  status: HuntingSourceStatus;
  discovery_method: string;
  discovery_notes: string | null;
  proposed_by: string;
  proposed_at: string;
  lawful_basis: string | null;
  access_method: string | null;
  jurisdiction: string | null;
  legal_review_note: string | null;
  authorized_by: string | null;
  authorized_at: string | null;
  last_decision_reason: string | null;
  updated_at: string;
  history: HuntingTransition[];
}

export interface HuntingAorSummary {
  aor: string;
  total: number;
  monitored: number;
  by_status: Record<string, number>;
}

export interface HuntingSummary {
  aors: HuntingAorSummary[];
  totals: HuntingAorSummary;
}

export interface HuntingDiscoveryResult {
  aor: string;
  proposed: HuntingSource[];
  skipped_existing: number;
  provider: string | null;
}

export interface HuntingDiscoverySweepResult {
  aors: string[];
  results: HuntingDiscoveryResult[];
  total_proposed: number;
  total_skipped: number;
  provider: string | null;
}

export interface HuntingDiscoveryStatus {
  provider: string; // "disabled" | "mock" | "http"
  enabled: boolean;
  configured: boolean;
  lawful_basis_recorded: boolean;
  host: string | null;
  category: HuntingSourceCategory;
  aors: string[]; // standing AOR watchlist a sweep covers by default
}

export interface HuntingDiscoveryScheduleStatus {
  enabled: boolean;
  interval_minutes: number;
  limit_per_aor: number;
  paused: boolean;
  running: boolean;
  runs: number;
  last_run_at: string | null;
  last_error: string | null;
  last_total_proposed: number | null;
  last_total_skipped: number | null;
  last_aors: string[];
}

export type HuntingEscalationStatus = "open" | "reported" | "closed" | "dismissed";

export interface HuntingEscalationTransition {
  from_status: HuntingEscalationStatus | null;
  to_status: HuntingEscalationStatus;
  by: string;
  at: string;
  note: string | null;
}

export interface HuntingEscalation {
  id: string;
  source_id: string | null;
  url: string | null;
  aor: string;
  concern: string;
  status: HuntingEscalationStatus;
  raised_by: string;
  raised_at: string;
  ncmec_reference: string | null;
  reported_by: string | null;
  reported_at: string | null;
  resolution: string | null;
  updated_at: string;
  history: HuntingEscalationTransition[];
}
