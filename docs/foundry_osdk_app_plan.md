# Foundry OSDK Application Plan

How a Foundry OSDK application would consume the ORCA ontology
([`v0.9_palantir_foundry_mapping.md`](v0.9_palantir_foundry_mapping.md)) while keeping ORCA
the system of record and the authorization authority. This is a **plan**, not an
implementation — no OSDK is generated and no Foundry calls are made in this milestone.

## Approach

1. **Publish the ontology** from the exported spec (`foundry/object_types.json`,
   `link_types.json`, `action_types.json`, `permissions.json`).
2. **Generate the OSDK** (TypeScript) from the published ontology.
3. **Build read views** bound to OSDK object sets, with object/property-level security
   matching [`foundry_permission_mapping.md`](foundry_permission_mapping.md).
4. **Wire actions** to the Foundry action types, which call back into ORCA's API so RBAC,
   case membership, separation of duties, and audit still apply. "AI proposes, analysts
   decide" is preserved — the UI records decisions; it never makes them.

## Screens (reference: the existing ORCA Next.js app)

| Screen | OSDK object sets | Notes |
| ------ | ---------------- | ----- |
| Case workspace | `OrcaCase` + `caseContains*` links | scoped to the viewer's `OrcaCaseMembership` |
| Review queue | `OrcaTask` (open) → `OrcaReviewDecision` | reviewer-gated; decisions via action types |
| Evidence locker | `OrcaEvidenceItem` | metadata for members; raw bytes for mutating roles only |
| Relationship graph | `OrcaEntity` + `OrcaRelationship` | **approved** relationships only |
| Report packages | `OrcaReportPackage` (+ manifest link) | partner export viewer's only window |
| Audit log | `OrcaAuditEvent` | append-only; case_manager / reviewer / admin |

## Actions in the UI

Analyst actions map 1:1 to the Foundry action types in
[`foundry_action_types.md`](foundry_action_types.md): create case, assign/revoke members,
create observation/evidence, upload evidence, verify hash, the review decisions, create
relationship, generate report draft / package, and download package. Each is shown only
when the viewer's role + case role permits it; the backend re-checks regardless.

## AIP (assistive, propose-only)

AIP may *suggest* — candidate relationships, candidate entity merges, summaries of approved
material, triage hints — and each suggestion enters the human review queue as a proposal.
AIP never approves, never asserts a finding about a person, never bypasses audit, and is
never autonomous (`aip_automation` is a forbidden workflow).

## Boundaries

The OSDK app introduces no capability ORCA lacks: no collection, no scraping, no autonomous
action, no raw evidence for partners, no cross-case access without membership. ORCA's
PostgreSQL remains the system of record; any write path routes through ORCA's services.

## Open questions

See §14 of [`v0.9_palantir_foundry_mapping.md`](v0.9_palantir_foundry_mapping.md) —
notably how ORCA's generic-403 non-leakage maps onto Foundry's security primitives, and
where the system of record lives in a deployed topology.
