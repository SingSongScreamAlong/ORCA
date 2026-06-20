# ORCA v1.0 — Threat Model

This document states the threats ORCA is designed to resist, how the current
implementation mitigates each, and the boundaries (non-goals) that bound the system. It
complements [`security.md`](security.md) and [`safety_and_handling.md`](safety_and_handling.md).
"Mitigated" describes the v1.0 prototype; production hardening is tracked in
[`known_limitations.md`](known_limitations.md) and [`roadmap.md`](roadmap.md).

## Assets

- Observations, evidence (metadata + bytes + SHA-256), entities, relationships.
- Cases and their need-to-know membership.
- The append-only audit log.
- Report packages shared with partners.

## Threats & mitigations

### 1. Unauthorized case access
A user views or acts on a case they are not assigned to.
- **Mitigation.** RBAC capability checks on every endpoint plus per-case membership
  (v0.6): non-admins need an active membership, gated by case role. Case-keyed reads use
  `require_case_material_read`; mutations/reviews/exports re-check in the service layer.
  Verified by `test_case_membership.py`.

### 2. Raw evidence exposure
Someone obtains evidence bytes they should not see.
- **Mitigation.** Raw download (`GET /evidence/{id}/download`) is restricted to admins and
  mutating roles (case_manager / analyst / reviewer); viewers get metadata only; partners
  get neither. Report packages reference evidence by metadata + SHA-256 and never bundle
  bytes. Verified by `test_evidence_upload.py` and `test_report_package.py`.

### 3. Partner overexposure
A partner export viewer sees more than approved deliverables.
- **Mitigation.** `partner_export_viewer` holds only `view_approved_reports`; every raw
  surface (`/cases/{id}/evidence`, `/graph`, `/audit`, `/observations`, and the Copilot)
  requires `read_case_material`, which partners lack → 403. Packages are scoped to assigned
  cases and contain approved material only.

### 4. AI hallucination / unsupported claims
An AI suggestion is mistaken for fact, or an asserted claim lacks support.
- **Mitigation.** The Copilot is **propose-only**: results carry `generated_by_ai` and
  `requires_human_review`, have no write path into case material, and reason over approved
  material only. The citation checker flags unsupported claims and missing citations.
  Reports/packages cite approved evidence only. Verified by `test_ai_copilot.py`.

### 5. Evidence tampering
Stored evidence is altered after the fact.
- **Mitigation.** Content is addressed by SHA-256; `verify` re-hashes the stored bytes and
  surfaces any mismatch rather than hiding it. Evidence is write-once (corrections are new
  items); observations are append-only.

### 6. Unsafe uploads
A dangerous or prohibited file is uploaded.
- **Mitigation.** A mandatory safety acknowledgement; a safe-by-default policy that rejects
  executable/script extensions (never stored), quarantines unknown types pending review,
  and caps size. ORCA never executes, decodes, or renders content. CSAM is prohibited by
  policy and never to be handled.

### 7. Audit bypass
A consequential action leaves no trace, or the trail is altered.
- **Mitigation.** Every privileged action writes an append-only `AuditEntry` (no update or
  delete path). Admin overrides are recorded as distinct events. The case audit log is
  itself access-controlled (`view_audit`).

### 8. Role misuse / privilege escalation
A user performs an action above their role, or approves their own proposal.
- **Mitigation.** Capability matrix per role; separation of duties forbids self-review
  without an audited admin override (admin only); membership management is restricted to a
  case's manager (or admin). Verified by `test_rbac.py` and `test_case_membership.py`.

### 9. Data leakage through error messages
A 403/404 reveals a case's existence, title, counts, or contents.
- **Mitigation.** Per-case denials return a single generic 403 — a non-member receives the
  **same** response for a real and a non-existent case id, so the API cannot be used to
  enumerate cases. Verified by `test_case_membership.py`.

### 10. Supply-chain / external dependency on AI or Palantir
A required external service introduces risk or a credential dependency.
- **Mitigation.** The Copilot's default provider is an offline deterministic mock (no
  credentials, no network). The Foundry layer is a local specification/export only — no
  live Palantir calls, sync, or production writes.

## Non-goals (out of scope by mission)

ORCA does **not** and will not implement: offensive collection or scraping; dark-web
browsing; autonomous hunting; face recognition/matching; offender/victim targeting; bulk
social monitoring; direct-contact workflows; live Palantir sync or production Foundry
writes; autonomous AI conclusions or AI-generated evidence; and **no CSAM storage or
handling** under any circumstance. See [`safety_and_handling.md`](safety_and_handling.md).

## Residual risk

This is a prototype: dev-only auth (no production IdP), no completed legal review, no
production deployment hardening, and AI determinism is guaranteed only for the mock
provider. See [`known_limitations.md`](known_limitations.md).
