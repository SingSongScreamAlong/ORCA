-- ORCA relational schema (PostgreSQL) — canonical DDL.
--
-- This mirrors the ORM models in backend/app/models and the ontology in
-- ontology/schema. Enum labels use the lowercase ontology values. The Alembic
-- migration backend/migrations/versions/0001_initial.py creates the same objects.
--
-- This is the Phase 1 target schema. The default skeleton backend is in-memory and
-- does not require this to run.

BEGIN;

-- --- Enumerated types -------------------------------------------------------

CREATE TYPE source_type        AS ENUM ('website', 'dataset', 'manual_upload', 'tip', 'document');
CREATE TYPE source_reliability AS ENUM ('unknown', 'low', 'medium', 'high');
CREATE TYPE evidence_type      AS ENUM ('screenshot', 'archived_page', 'image', 'file', 'text');
CREATE TYPE entity_type        AS ENUM ('phone_number', 'alias', 'account', 'username',
                                        'location', 'vehicle', 'image', 'advertisement', 'tattoo_marker');
CREATE TYPE relationship_type  AS ENUM ('shared_phone', 'shared_image', 'shared_location',
                                        'shared_account', 'appears_with', 'analyst_confirmed');
CREATE TYPE origin             AS ENUM ('system_proposed', 'analyst_created', 'imported');
CREATE TYPE review_status      AS ENUM ('proposed', 'confirmed', 'rejected', 'needs_review');
CREATE TYPE cluster_status     AS ENUM ('proposed', 'active', 'archived', 'rejected');
CREATE TYPE case_status        AS ENUM ('open', 'active', 'on_hold', 'closed');
CREATE TYPE report_status      AS ENUM ('draft', 'in_review', 'final');
CREATE TYPE review_item_type   AS ENUM ('proposed_relationship', 'proposed_cluster', 'flagged_observation');

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

CREATE TABLE evidence (
    id           UUID PRIMARY KEY,
    evidence_type evidence_type NOT NULL,
    sha256       VARCHAR(64) NOT NULL,          -- integrity anchor; verified on read
    storage_uri  VARCHAR(2048) NOT NULL,
    content_type VARCHAR(255),
    captured_at  TIMESTAMPTZ NOT NULL,
    source_id    UUID REFERENCES sources(id),
    description  TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_evidence_sha256 ON evidence (sha256);

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

CREATE TABLE observations (
    id         UUID PRIMARY KEY,
    timestamp  TIMESTAMPTZ NOT NULL,               -- observed time (collector-supplied)
    source_id  UUID NOT NULL REFERENCES sources(id),
    collector  VARCHAR(255) NOT NULL,
    location   VARCHAR(512),
    notes      TEXT,
    confidence DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE relationships (
    id                UUID PRIMARY KEY,
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

CREATE TABLE clusters (
    id         UUID PRIMARY KEY,
    title      VARCHAR(512) NOT NULL,
    status     cluster_status NOT NULL DEFAULT 'proposed',
    confidence DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    origin     origin NOT NULL DEFAULT 'system_proposed',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE cases (
    id         UUID PRIMARY KEY,
    title      VARCHAR(512) NOT NULL,
    status     case_status NOT NULL DEFAULT 'open',
    owner      VARCHAR(255) NOT NULL,
    summary    TEXT,
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

CREATE TABLE review_items (
    id           UUID PRIMARY KEY,
    item_type    review_item_type NOT NULL,
    subject_type VARCHAR(64) NOT NULL,
    subject_id   UUID NOT NULL,
    rationale    TEXT NOT NULL,                  -- why surfaced; never null
    confidence   DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    evidence_ids UUID[] NOT NULL DEFAULT '{}',
    status       review_status NOT NULL DEFAULT 'proposed',
    decided_by   VARCHAR(255),
    decided_at   TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Append-only audit log. No UPDATE/DELETE path by policy.
CREATE TABLE audit_log (
    id          UUID PRIMARY KEY,
    actor_id    VARCHAR(255) NOT NULL,
    action      VARCHAR(128) NOT NULL,
    target_type VARCHAR(64) NOT NULL,
    target_id   VARCHAR(64) NOT NULL,
    context     JSONB NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- --- Association tables (many-to-many) --------------------------------------

CREATE TABLE observation_entities (
    observation_id UUID NOT NULL REFERENCES observations(id) ON DELETE CASCADE,
    entity_id      UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    PRIMARY KEY (observation_id, entity_id)
);

CREATE TABLE observation_evidence (
    observation_id UUID NOT NULL REFERENCES observations(id) ON DELETE CASCADE,
    evidence_id    UUID NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
    PRIMARY KEY (observation_id, evidence_id)
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
