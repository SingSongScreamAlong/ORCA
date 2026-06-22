# ORCA v1.0 — Known Limitations

ORCA v1.0 is a credible, reviewable **prototype** — a working vertical slice with enforced
safety properties, not a production system. This document is deliberately explicit about
what it is *not* yet, so technical, security, and partner reviewers can calibrate.

## Authentication & identity

- **Dev auth only.** A request acts as the user named in the `X-ORCA-User` header (the UI
  sets it via a cookie); the default is `admin`. There is **no production identity
  provider** (OIDC/SSO), no passwords, no sessions, no MFA.
- The authorization stack behind auth (roles, capabilities, case membership, separation of
  duties, audit) is real and enforced; only the *authentication* step is a stub. Production
  replaces `resolve_principal` with real credential verification without changing the rest.

## Palantir / Foundry

- **Read-only connection verified; no sync.** v0.9 is a local ontology **specification and
  export** (`foundry/*.json`). v1.1 added read-only connection **scaffolding**; v1.2 adds a
  real, **read-only** httpx **REST connector** (`RestFoundryClient`) over Foundry's v2 API.
  This has been **verified against the live ORCA tenant** (`orca.usw-23.palantirfoundry.com`):
  with a Foundry user token it authenticated and listed ontology metadata (`ok: true`,
  2 ontologies incl. the ORCA Ontology). Caveats that remain: it is **disabled by default and
  read-only**; the **client-credentials grant is not available on the tenant's current
  enrollment plan**, so the verified path uses a **user token** (`ORCA_FOUNDRY_TOKEN`) — the
  connector supports client-credentials and will use it once the plan allows, no code change;
  reading individual **object records** depends on object types being published into the
  ontology and is unit-tested but not yet confirmed against live objects. There is **no
  production write path, no full sync, and no data movement**. An OSDK-based path remains a
  selectable placeholder (`ORCA_FOUNDRY_CLIENT=sdk`).
- **No live AIP integration.** v1.0's Copilot runs on a local, deterministic **mock
  provider**; AIP is a future provider behind the `AiProvider` seam.

## AI Copilot

- Suggestions are **proposed-only** and require human review; determinism is guaranteed
  only for the mock provider. A real provider would need its own evaluation, prompt
  governance, and redaction review before use.
- The mock's extraction/suggestion logic is intentionally simple (pattern-based), for
  demonstration — not a production NLP/entity-resolution system.

## Deployment & operations

- **No production deployment hardening.** No TLS termination config, secret management,
  rate limiting, backups/restore drills, monitoring, or scale testing are included here.
- Default backend is the **in-memory store**; PostgreSQL is implemented and integration-
  tested but the schema lives in a single squashed migration suited to a fresh prototype DB.
- The Neo4j graph projection is optional and off by default; graph queries read the
  authoritative relational record.

## Legal, policy & data

- **No legal review completed.** Handling/legal flags are governance placeholders that
  record analyst judgement; they do not implement jurisdiction-specific policy.
- **Demo data only.** The seeded case/users are illustrative. No real personal data ships
  with the repo.
- **Raw evidence policy needs partner-specific approval.** The default is conservative
  (raw bytes restricted to mutating roles; viewers metadata-only; partners none). Any
  broadening (e.g. `EVIDENCE_ALLOW_VIEWER_DOWNLOAD`) must be agreed per engagement.

## Functional scope

- Collection ("Hunting Grounds") is an **interface only** — no scraping, dark-web
  collection, or autonomous hunting, by design.
- `closeCase` / `archiveCase` exist in the Foundry action mapping but the corresponding
  case-lifecycle endpoint is a planned ORCA addition.
- File upload stores bytes locally (in-memory dev store, or filesystem content store for
  PostgreSQL); there is no object-store/S3 integration yet.

## What is solid at v1.0

For balance: the analyst loop, RBAC + separation of duties, per-case need-to-know with
non-leaking 403s, SHA-256 evidence integrity + verification, the safe-by-default upload
policy, approved-only reports/graph/packages, the append-only audit log, and the
propose-only Copilot are implemented and covered by 151 passing backend tests plus a
guarded PostgreSQL integration test.
