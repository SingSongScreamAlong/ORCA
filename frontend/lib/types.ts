// TypeScript types mirroring the ORCA API contract (backend/app/schemas).
// Kept in sync with ontology/schema and docs/ontology_v0.1.md.

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
  evidence_ids: string[];
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

export interface Evidence {
  id: string;
  evidence_type: string;
  sha256: string;
  storage_uri: string;
  content_type: string | null;
  captured_at: string;
  source_id: string | null;
  description: string | null;
  created_at: string;
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
