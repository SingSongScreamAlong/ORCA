# Publishing ORCA's Ontology into Foundry (guide)

How to take ORCA's exported ontology spec (`foundry/*.json`) and create the **first real ORCA
object type** in a Foundry tenant — so the read connector (v1.2) and read endpoints (v1.3)
surface *ORCA's* objects (`OrcaEntity`, `OrcaCase`, …) instead of Foundry's stock example
data. This is a **manual, validate-the-model-first** procedure; automate only after one type
round-trips cleanly.

> **Honest framing & safety.** ORCA's `foundry/*.json` is a **design spec**, not something
> Foundry imports directly — Foundry object types are **backed by datasets** and defined in
> **Ontology Manager**. Publishing therefore means pushing data *into* Foundry, which crosses
> ORCA's read-only boundary. Keep it strictly: **synthetic/demo data only** (never real case
> data), **metadata only** (never raw evidence bytes or hashes of real evidence), lawful, and
> **no CSAM** — exactly as in [`safety_and_handling.md`](safety_and_handling.md). ORCA's own
> connector stays read-only; this guide's writes happen in the Foundry UI, by you.

## Why `OrcaEntity` first

It's the simplest object type — 5 properties, all directly mapped — so it validates the whole
round-trip with minimal surface area:

| Dataset column | Foundry property (`apiName`) | Base type | Required | Notes |
| -------------- | ---------------------------- | --------- | -------- | ----- |
| `entityId`     | `entityId`                   | string    | ✅ | **Primary key** |
| `entityType`   | `entityType`                 | string    | ✅ | e.g. phone/email/username |
| `value`        | `value`                      | string    | ✅ | use as the **title** property |
| `confidence`   | `confidence`                 | double    | — | 0–1 |
| `createdAt`    | `createdAt`                  | timestamp | — | ISO-8601 |

A ready-made **synthetic** dataset is provided at
[`foundry/samples/orca_entity_sample.csv`](../foundry/samples/orca_entity_sample.csv) (5
harmless demo rows). The full property list for every type lives in
[`foundry/object_types.json`](../foundry/object_types.json).

## Steps

### 1. Get a synthetic dataset
Use the provided `foundry/samples/orca_entity_sample.csv` (recommended for the first run), or
export demo entities from ORCA later. **Do not** use real case data.

### 2. Upload it as a Foundry dataset
In Foundry: **Files / Datasets → New dataset** inside the **ORCA Osint** project (the same
Compass location that backs your ORCA Ontology). Import the CSV, and confirm the column types
are read as: `entityId/entityType/value` = string, `confidence` = double, `createdAt` =
timestamp. Note the dataset's RID.

### 3. Create the object type in Ontology Manager
**Ontology → Ontology Manager → New object type**, in the **ORCA Ontology**:
- **API name:** `OrcaEntity` · **Display name:** "Orca Entity" · **Title property:** `value`.
- **Backing dataset:** the dataset from step 2.
- **Primary key:** `entityId`.
- **Properties:** map each column to the property/type in the table above.
- Save and **publish** the object type.

### 4. Read it back through ORCA (closes the loop)
With your `.env` still pointed at the tenant:
```bash
cd backend
python -m app.foundry.discover            # OrcaEntity now appears next to the Example* types
ORCA_FOUNDRY_ONTOLOGY_API_NAME=ontology-66c920ed-cf62-4590-b62b-f7ee05124caf \
  python -c "from app.foundry.health import _load_dotenv as L; L(); from app.foundry.config import FoundryConfig as C; from app.foundry.client import build_foundry_client as B; import json; print(json.dumps(B(C.from_env()).list_demo_objects('OrcaEntity', limit=5), indent=2))"
```
Or, with the server running (`uvicorn app.main:app --env-file .env --reload`), as admin:
```bash
curl -s "localhost:8000/api/v1/integrations/foundry/objects/OrcaEntity?limit=5" -H "X-ORCA-User: admin" | python3 -m json.tool
```
Seeing your demo entities come back = the model is validated end to end.

## Scaling to the rest

Once `OrcaEntity` round-trips, repeat for the other 12 types. Suggested order (simplest →
richest), with primary keys:

`OrcaUser` (userId) · `OrcaCase` (caseId) · `OrcaSource` (sourceId) · `OrcaObservation`
(observationId) · `OrcaRelationship` (relationshipId) · `OrcaReviewDecision` (reviewItemId) ·
`OrcaTask` (taskId) · `OrcaReport` (reportId) · `OrcaReportPackage` (packageId) ·
`OrcaCaseMembership` (membershipId) · `OrcaAuditEvent` (auditId) · `OrcaEvidenceItem`
(evidenceId — **metadata + hashes only; never raw bytes**).

Then **link types** ([`foundry/link_types.json`](../foundry/link_types.json)) and, much later,
**action types** ([`foundry/action_types.json`](../foundry/action_types.json)) — actions are a
*write* surface and should call back into ORCA's services so RBAC/membership/audit still hold
(out of scope here).

## What this does and doesn't change

- **Does:** create real ORCA-shaped object types in Foundry, backed by synthetic datasets, so
  ORCA's read connector/endpoints return ORCA objects.
- **Doesn't:** make ORCA write to Foundry (the connector stays read-only), move any real or
  sensitive data, or wire actions. A future **guarded import** would bring Foundry objects
  back into ORCA as *proposed, analyst-reviewed* records (case-scoped, audited) — see
  [`v1.3_foundry_read_endpoints.md`](v1.3_foundry_read_endpoints.md).

## Automating later

Foundry exposes ontology/dataset APIs (and the OMS) for programmatic object-type creation.
Once the manual `OrcaEntity` round-trip confirms the mapping, a small generator could read
`foundry/object_types.json` and create datasets + object types via those APIs. Defer it until
the model is proven by hand, and confirm the write scopes/enrollment-plan support first (the
same client-credentials/plan considerations from
[`foundry_connection_setup.md`](foundry_connection_setup.md) apply to writes).
