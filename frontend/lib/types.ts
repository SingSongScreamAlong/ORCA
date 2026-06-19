// TypeScript types mirroring the ORCA API contract (backend/app/schemas).
// Kept in sync with ontology/schema and docs/ontology_v0.1.md.

export type Origin = "system_proposed" | "analyst_created" | "imported";

export type ReviewStatus = "proposed" | "confirmed" | "rejected" | "needs_review";

export type ConfidenceBand = "unverified" | "low" | "medium" | "high" | "confirmed";

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

export type ReviewItemType =
  | "proposed_relationship"
  | "proposed_cluster"
  | "flagged_observation";

export interface Observation {
  id: string;
  timestamp: string;
  source_id: string;
  collector: string;
  location: string | null;
  notes: string | null;
  confidence: number;
  entity_ids: string[];
  evidence_ids: string[];
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

export interface ReviewItem {
  id: string;
  item_type: ReviewItemType;
  subject_type: string;
  subject_id: string;
  rationale: string;
  confidence: number;
  evidence_ids: string[];
  status: ReviewStatus;
  decided_by: string | null;
  decided_at: string | null;
  created_at: string;
}

export interface Source {
  id: string;
  source_type: string;
  name: string;
  identifier: string | null;
  reliability: "unknown" | "low" | "medium" | "high";
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
  };
  recent_observations: Observation[];
  recent_relationships: Relationship[];
  review_queue: ReviewItem[];
  system_health: {
    status: string;
    storage_backend: string;
  };
}

export type ReviewDecision = "approve" | "reject" | "needs_review";
