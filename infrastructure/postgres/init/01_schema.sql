-- ORCA relational schema (PostgreSQL) — canonical DDL.
--
-- This mirrors the ORM models in backend/app/models and the ontology in
-- ontology/schema. Enum labels use the lowercase ontology values. The Alembic
-- migration backend/migrations/versions/0001_initial.py creates the same objects.
--
-- This is the Phase 1 / v0.2 target schema. The default skeleton backend is in-memory
-- and does not require this to run.

BEGIN;

-- --- Enumerated types -------------------------------------------------------

CREATE TYPE source_type        AS ENUM ('website', 'dataset', 'manual_upload', 'tip', 'document');
CREATE TYPE source_reliability AS ENUM ('unknown', 'low', 'medium', 'high');
CREATE TYPE evidence_type      AS ENUM ('screenshot', 'document', 'image', 'video', 'web_archive',
                                        'analyst_note', 'partner_file', 'other');
CREATE TYPE evidence_status    AS ENUM ('proposed', 'approved', 'rejected', 'needs_more_review', 'quarantined');
CREATE TYPE entity_type        AS ENUM ('phone_number', 'alias', 'account', 'username',
                                        'location', 'vehicle', 'image', 'advertisement', 'tattoo_marker');
CREATE TYPE relationship_type  AS ENUM ('shared_phone', 'shared_image', 'shared_location',
                                        'shared_account', 'appears_with', 'analyst_confirmed');
CREATE TYPE origin             AS ENUM ('system_proposed', 'analyst_created', 'imported');
-- v0.2 approval lifecycle (replaces v0.1 'confirmed'/'needs_review').
CREATE TYPE review_status      AS ENUM ('proposed', 'approved', 'rejected', 'needs_more_review');
CREATE TYPE cluster_status     AS ENUM ('proposed', 'active', 'archived', 'rejected');
CREATE TYPE case_status        AS ENUM ('open', 'active', 'on_hold', 'closed');
CREATE TYPE report_status      AS ENUM ('draft', 'in_review', 'final');
CREATE TYPE review_item_type   AS ENUM ('proposed_observation', 'proposed_relationship',
                                        'proposed_cluster', 'flagged_observation');
CREATE TYPE orca_role          AS ENUM ('admin', 'case_manager', 'analyst', 'reviewer',
                                        'viewer', 'partner_export_viewer');
-- v0.6 per-case authorization: a user's role within a specific case, and the
-- lifecycle of that membership.
CREATE TYPE case_role          AS ENUM ('case_manager', 'analyst', 'reviewer',
                                        'viewer', 'partner_export_viewer');
CREATE TYPE membership_status  AS ENUM ('active', 'inactive', 'revoked');

-- --- Core objects -----------------------------------------------------------

CREATE TABLE sources (
    id          UUID PRIMARY KEY,
    source_type source_type NOT NULL,
    name        VARCHAR(512) NOT NULL,
    identifier  VARCHAR(2048),
    reliability source_reliability NOT NULL DEFAULT 'unknown',
    description TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE entities (
    id          UUID PRIMARY KEY,
    entity_type entity_type NOT NULL,
    value       VARCHAR(1024) NOT NULL,
    confidence  DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_entity_type_value UNIQUE (entity_type, value)
);
CREATE INDEX ix_entities_value ON entities (value);

-- Cases are created before observations/relationships/review_items, which reference them.
CREATE TABLE cases (
    id          UUID PRIMARY KEY,
    title       VARCHAR(512) NOT NULL,
    status      case_status NOT NULL DEFAULT 'open',
    owner       VARCHAR(255) NOT NULL,
    summary     TEXT,
    legal_notes TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE observations (
    id         UUID PRIMARY KEY,
    case_id    UUID REFERENCES cases(id) ON DELETE SET NULL,
    timestamp  TIMESTAMPTZ NOT NULL,               -- observed time (collector-supplied)
    source_id  UUID NOT NULL REFERENCES sources(id),
    collector  VARCHAR(255) NOT NULL,
    location   VARCHAR(512),
    notes      TEXT,
    confidence DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    status     review_status NOT NULL DEFAULT 'proposed',
    decided_by VARCHAR(255),
    decided_at TIMESTAMPTZ,
    handling   JSONB NOT NULL DEFAULT '{}',        -- legal/handling placeholder metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_observations_case ON observations (case_id);
CREATE INDEX ix_observations_status ON observations (status);

-- Evidence Locker (v0.3). Bytes (when held) live in the content store, keyed by sha256.
CREATE TABLE evidence_items (
    id                UUID PRIMARY KEY,
    case_id           UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    source_id         UUID NOT NULL REFERENCES sources(id),
    observation_id    UUID REFERENCES observations(id) ON DELETE SET NULL,
    title             VARCHAR(512) NOT NULL,
    description       TEXT,
    evidence_type     evidence_type NOT NULL,
    storage_uri       VARCHAR(2048),
    original_filename VARCHAR(1024),
    mime_type         VARCHAR(255),
    size_bytes        BIGINT,
    sha256            VARCHAR(64),                 -- integrity anchor; re-hashed on verify
    captured_at       TIMESTAMPTZ,
    captured_by       VARCHAR(255),
    access_method     VARCHAR(64) NOT NULL DEFAULT 'manual_upload',
    legal_flags       JSONB NOT NULL DEFAULT '{}',
    handling_notes    TEXT,
    status            evidence_status NOT NULL DEFAULT 'proposed',
    has_bytes         BOOLEAN NOT NULL DEFAULT false,
    created_by        VARCHAR(255) NOT NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_evidence_items_case ON evidence_items (case_id);
CREATE INDEX ix_evidence_items_observation ON evidence_items (observation_id);
CREATE INDEX ix_evidence_items_sha256 ON evidence_items (sha256);

CREATE TABLE relationships (
    id                UUID PRIMARY KEY,
    case_id           UUID REFERENCES cases(id) ON DELETE SET NULL,
    source_entity_id  UUID NOT NULL REFERENCES entities(id),
    target_entity_id  UUID NOT NULL REFERENCES entities(id),
    relationship_type relationship_type NOT NULL,
    confidence        DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    origin            origin NOT NULL DEFAULT 'system_proposed',
    status            review_status NOT NULL DEFAULT 'proposed',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_relationship_distinct_endpoints CHECK (source_entity_id <> target_entity_id)
);
CREATE INDEX ix_relationships_case ON relationships (case_id);

CREATE TABLE clusters (
    id         UUID PRIMARY KEY,
    title      VARCHAR(512) NOT NULL,
    status     cluster_status NOT NULL DEFAULT 'proposed',
    confidence DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    origin     origin NOT NULL DEFAULT 'system_proposed',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE reports (
    id         UUID PRIMARY KEY,
    case_id    UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    title      VARCHAR(512) NOT NULL,
    author     VARCHAR(255) NOT NULL,
    status     report_status NOT NULL DEFAULT 'draft',
    body       TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Partner-ready export snapshots (v0.8). Approved material only; report + manifest are
-- stored inline with content hashes. Raw evidence bytes are never bundled.
CREATE TABLE report_packages (
    id              UUID PRIMARY KEY,
    case_id         UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    title           VARCHAR(512) NOT NULL,
    status          report_status NOT NULL DEFAULT 'final',
    handling_level  VARCHAR(64) NOT NULL,
    generated_by    VARCHAR(255) NOT NULL,
    report_markdown TEXT NOT NULL,
    manifest        JSONB NOT NULL DEFAULT '{}',
    report_sha256   VARCHAR(64) NOT NULL,
    manifest_sha256 VARCHAR(64) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_report_packages_case ON report_packages (case_id);

CREATE TABLE review_items (
    id           UUID PRIMARY KEY,
    item_type    review_item_type NOT NULL,
    subject_type VARCHAR(64) NOT NULL,
    subject_id   UUID NOT NULL,
    case_id      UUID REFERENCES cases(id) ON DELETE SET NULL,
    created_by   VARCHAR(255),                   -- proposer, for self-review checks
    rationale    TEXT NOT NULL,                  -- why surfaced; never null
    confidence   DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    evidence_ids UUID[] NOT NULL DEFAULT '{}',
    status       review_status NOT NULL DEFAULT 'proposed',
    decided_by   VARCHAR(255),
    decided_at   TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_review_items_status ON review_items (status);

-- Append-only audit log. No UPDATE/DELETE path by policy.
CREATE TABLE audit_log (
    id          UUID PRIMARY KEY,
    actor_id    VARCHAR(255) NOT NULL,
    action      VARCHAR(128) NOT NULL,
    target_type VARCHAR(64) NOT NULL,
    target_id   VARCHAR(64) NOT NULL,
    case_id     UUID,
    context     JSONB NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_audit_log_case ON audit_log (case_id);

-- --- Users & case membership (v0.4 Auth/RBAC) -------------------------------

CREATE TABLE users (
    id           UUID PRIMARY KEY,
    username     VARCHAR(128) NOT NULL UNIQUE,
    display_name VARCHAR(255) NOT NULL,
    role         orca_role NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_users_username ON users (username);

-- A user's membership in a case (v0.6). One row per (case, user); re-adding a removed
-- member reactivates the same row, so there is at most one — let alone one active.
CREATE TABLE case_members (
    id          UUID PRIMARY KEY,
    case_id     UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    case_role   case_role NOT NULL,
    status      membership_status NOT NULL DEFAULT 'active',
    assigned_by VARCHAR(128) NOT NULL,
    assigned_at TIMESTAMPTZ NOT NULL,
    notes       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_case_member UNIQUE (case_id, user_id)
);
CREATE INDEX ix_case_members_user ON case_members (user_id);
CREATE INDEX ix_case_members_case ON case_members (case_id);

-- --- Association tables (many-to-many) --------------------------------------

CREATE TABLE observation_entities (
    observation_id UUID NOT NULL REFERENCES observations(id) ON DELETE CASCADE,
    entity_id      UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    PRIMARY KEY (observation_id, entity_id)
);

CREATE TABLE relationship_observations (
    relationship_id UUID NOT NULL REFERENCES relationships(id) ON DELETE CASCADE,
    observation_id  UUID NOT NULL REFERENCES observations(id) ON DELETE CASCADE,
    PRIMARY KEY (relationship_id, observation_id)
);

CREATE TABLE cluster_entities (
    cluster_id UUID NOT NULL REFERENCES clusters(id) ON DELETE CASCADE,
    entity_id  UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    PRIMARY KEY (cluster_id, entity_id)
);

CREATE TABLE cluster_observations (
    cluster_id     UUID NOT NULL REFERENCES clusters(id) ON DELETE CASCADE,
    observation_id UUID NOT NULL REFERENCES observations(id) ON DELETE CASCADE,
    PRIMARY KEY (cluster_id, observation_id)
);

-- A case is a VIEW over evidence: deleting a case removes references (CASCADE on the
-- case side only), never the referenced observations / entities / clusters.
CREATE TABLE case_observations (
    case_id        UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    observation_id UUID NOT NULL REFERENCES observations(id) ON DELETE CASCADE,
    PRIMARY KEY (case_id, observation_id)
);

CREATE TABLE case_entities (
    case_id   UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    PRIMARY KEY (case_id, entity_id)
);

CREATE TABLE case_clusters (
    case_id    UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    cluster_id UUID NOT NULL REFERENCES clusters(id) ON DELETE CASCADE,
    PRIMARY KEY (case_id, cluster_id)
);

COMMIT;
