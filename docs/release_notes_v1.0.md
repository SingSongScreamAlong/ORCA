# ORCA — Release Notes (v0.1 → v1.0)

ORCA v1.0 is a credible, reviewable, demoable prototype: a lawful, auditable
case-intelligence workspace where **AI proposes and analysts decide**. This summarises the
ten milestones that built it. Each milestone shipped with passing backend lint + tests, a
passing frontend typecheck + build, and (where relevant) a verified PostgreSQL path.

## Milestones

### v0.1 — Skeleton
Repository structure, ontology (machine-readable + narrative), FastAPI backend with a
layered architecture, a Next.js analyst UI (calm, evidence-first), local orchestration, and
Hunting Grounds defined as **interfaces only**.

### v0.2 — Analyst Loop MVP
One complete, auditable loop: case → observation intake → review queue (approve / reject /
needs-more-review) → relationship citing approved observations → timeline → draft report.
Production PostgreSQL persistence (SQLAlchemy unit of work + Alembic). → `docs/v0.2_analyst_loop.md`

### v0.3 — Evidence Locker + Integrity Layer
Case-scoped `EvidenceItem` with source attribution and file metadata, **SHA-256 hashing +
on-read verification** over a content store, quarantine, cross-case linking guard,
chain-of-custody audit, and approved-only report citations. → `docs/v0.3_evidence_locker.md`

### v0.4 — Auth/RBAC + Workspace Hardening
Real authenticated identities (dev `X-ORCA-User`), **six roles** with a capability matrix
on every endpoint (403/401), **separation of duties** on approvals with an audited admin
override, case membership/assignment, and report publishing. → `docs/v0.4_auth_rbac.md`

### v0.5 — Relationship Graph & Discovery
Graph queries over **approved** relationships — entity neighbourhoods, case subgraphs, and
shortest paths — with a calm, dependency-free node-link Graph tab. → `docs/v0.5_graph_discovery.md`

### v0.6 — Case Membership & Authorization Scoping
**Need-to-know:** non-admins see and act on only assigned cases, scoped by a per-case role;
an audited membership roster (add / role-change / revoke / reactivate); and generic 403s
that never leak a case's existence or contents. → `docs/v0.6_case_membership.md`

### v0.7 — Evidence File Upload + Storage Hardening
Real manual upload of lawful files (multipart) hashed and content-addressed; a
safe-by-default policy (reject executables, quarantine unknown types, size cap); role- and
case-scoped raw-byte download; a mandatory safety acknowledgement; audited
upload/download/verify. → `docs/v0.7_evidence_file_upload.md`

### v0.8 — Report Package Export
Partner-ready export packages from **approved material only**: a Markdown report + a JSON
evidence manifest (per-evidence SHA-256, source metadata, verification status) with content
hashes and an optional ZIP. Role-gated generation; case-scoped, partner-accessible download
with no raw evidence/graph/audit; audited. → `docs/v0.8_report_package_export.md`

### v0.9 — Palantir Foundry Ontology Mapping
A Foundry-ready ontology **specification and local mapping module**
(`backend/app/foundry_mapping/`, exported to `foundry/*.json`): 13 object types, 19 link
types, 20 action types, and permissions **derived from ORCA's real RBAC**. Mapping/spec
only — no live Palantir calls or sync. → `docs/v0.9_palantir_foundry_mapping.md`

### v1.0 — AIP-assisted Analyst Copilot (propose-only)
A local, provider-agnostic AI assistance layer (`backend/app/ai_assist/`): summarise
approved material, propose candidate entities/relationships, draft report sections, check
citations, flag review gaps. Every output is **proposed-only**, human-reviewed, case-
membership gated (partners excluded), and audited; default offline deterministic mock
provider (no credentials). → `docs/v1.0_aip_assisted_analyst_copilot.md`

## Invariants held across every milestone

- AI proposes, analysts decide — no autonomous conclusions.
- Relationships require approved supporting observations.
- Reports and packages cite approved evidence only.
- Evidence is case-scoped and hash-verifiable; bytes are never bundled into exports.
- Graph traversal uses approved relationships only.
- Case membership enforces need-to-know; denials never leak case existence.
- Partner export viewers receive approved report packages only.
- Privileged actions are audited (append-only).
- No scraping, dark-web collection, autonomous hunting, face search, offender/victim
  targeting, bulk monitoring, direct contact, or live Palantir/AIP integration — and **no
  CSAM storage or handling**, ever.

## Verification at v1.0

- Backend: `ruff` clean; 126 backend tests pass (in-memory) plus a guarded PostgreSQL
  integration test.
- Frontend: `typecheck` + `build` pass.
- Foundry mapping: `python -m app.foundry_mapping.export` regenerates `foundry/*.json`
  (a test asserts the committed export is in sync and deterministic).

## Release tags

| Tag | Milestone |
| --- | --------- |
| `v0.5.0-foundation` | v0.1–v0.5 foundation |
| `v0.6.0-case-membership` | Case membership & authorization scoping |
| `v0.7.0-evidence-upload` | Evidence file upload + storage hardening |
| `v0.8.0-report-package-export` | Report package export |
| `v0.9.0-palantir-foundry-mapping` | Palantir Foundry ontology mapping |
| `v1.0.0-aip-assisted-analyst-copilot` | AIP-assisted Analyst Copilot (propose-only) |

## Status & next

ORCA v1.0 is a prototype, not a production system — see
[`known_limitations.md`](known_limitations.md) (dev auth, no live Palantir/AIP, no
production hardening, no completed legal review) and [`threat_model.md`](threat_model.md).
For a guided demo, see [`demo_walkthrough.md`](demo_walkthrough.md); for Foundry framing,
[`palantir_pitch_notes.md`](palantir_pitch_notes.md).
