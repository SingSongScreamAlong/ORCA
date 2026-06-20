# ORCA v1.0 — Demo Walkthrough

A full, reproducible demo path across every v1.0 capability, using the seeded demo data
and users. The in-memory backend needs no database, so the whole demo runs locally.

- Backend: `cd backend && pip install -e ".[dev]" && uvicorn app.main:app --reload`
- Frontend: `cd frontend && npm install && npm run dev` → http://localhost:3000
- Auth is dev-only: a request acts as the user in the `X-ORCA-User` header (UI: the user
  switcher in the top bar sets the `orca_user` cookie). Demo users: `admin`, `casey`
  (case_manager), `ana` (analyst), `rae` (reviewer), `vic` (viewer), `partner`
  (partner_export_viewer), `nomad` (unassigned analyst).

The seeded **demo case** ("Shared-phone advertisements") already has `casey`, `ana`, `rae`,
`vic`, and `partner` assigned, two approved observations linked by a shared phone, approved
evidence, an approved relationship, and one pending review item.

Below, each step lists the **UI** path and the equivalent **API** call. Set
`B=http://localhost:8000/api/v1` and `hdr() { echo "X-ORCA-User: $1"; }`.

## 1. Switch user / open an assigned case

- **UI:** use the user switcher (top bar) to act as `ana`; the case list shows only cases
  `ana` is assigned to. Open the demo case.
- **API:**
  ```bash
  curl -s $B/cases -H "$(hdr ana)" | jq '.[].title'          # only assigned cases
  CASE=$(curl -s $B/cases -H "$(hdr ana)" | jq -r '.[0].id')
  curl -s $B/cases/$CASE -H "$(hdr ana)" | jq '{title: .case.title, counts}'
  ```
  As `nomad` (unassigned), `GET /cases` is empty and `GET /cases/$CASE` returns a generic
  403 — it never reveals the case exists.

## 2. Add a source / observation / evidence

- **UI:** Case → **Observations** → "Add observation"; Case → **Evidence Locker** →
  "Upload a lawful file" (acknowledge the safety boundaries) or "Record metadata only".
- **API:** record an observation (enters the review queue as *proposed*), then upload a file:
  ```bash
  SRC=$(curl -s $B/sources -H "$(hdr ana)" | jq -r '.[0].id')
  E=$(curl -s $B/entities -H "$(hdr ana)" -H 'content-type: application/json' \
    -d '{"entity_type":"username","value":"demo_user"}' | jq -r .id)
  OBS=$(curl -s $B/observations -H "$(hdr ana)" -H 'content-type: application/json' -d "{
    \"case_id\":\"$CASE\",\"timestamp\":\"2026-01-01T00:00:00Z\",\"source_id\":\"$SRC\",
    \"collector\":\"ana\",\"notes\":\"demo observation\",\"confidence\":0.7,\"entity_ids\":[\"$E\"]}" | jq -r .id)
  echo "lawful demo evidence" > demo.txt
  EV=$(curl -s -X POST $B/cases/$CASE/evidence/upload -H "$(hdr ana)" \
    -F "file=@demo.txt;type=text/plain" -F "source_id=$SRC" -F "title=Demo upload" \
    -F "acknowledged=true" -F "observation_id=$OBS" | jq -r .id)
  ```

## 3. Review & approval

- **UI:** switch to `rae` (reviewer) → **Review** queue → Approve the proposed observation.
  (An analyst cannot approve; a reviewer cannot approve their own proposal without an
  audited admin override.)
- **API:**
  ```bash
  ITEM=$(curl -s "$B/review?case_id=$CASE" -H "$(hdr rae)" | jq -r ".[]|select(.subject_id==\"$OBS\")|.id")
  curl -s $B/review/$ITEM/decision -H "$(hdr rae)" -H 'content-type: application/json' \
    -d '{"decision":"approve"}' | jq .status                                  # approved
  curl -s $B/evidence/$EV/decision -H "$(hdr rae)" -H 'content-type: application/json' \
    -d '{"decision":"approve"}' | jq .status                                  # approved
  ```

## 4. Relationship graph

- **UI:** Case → **Graph** tab — a calm node-link view of the case's **approved**
  relationships.
- **API:**
  ```bash
  curl -s $B/cases/$CASE/graph -H "$(hdr ana)" | jq '{nodes:(.nodes|length), edges:(.edges|length)}'
  ```

## 5. Evidence verification

- **UI:** Evidence Locker → "Verify hash" on an item; mutating roles also see "Download".
- **API:**
  ```bash
  curl -s -X POST $B/evidence/$EV/verify -H "$(hdr rae)" | jq '{verified, recorded_sha256}'
  curl -s $B/evidence/$EV/download -H "$(hdr rae)"        # raw bytes (mutating roles only)
  curl -s -o /dev/null -w "viewer download -> %{http_code}\n" $B/evidence/$EV/download -H "$(hdr vic)"  # 403
  ```

## 6. Report package generation

- **UI:** Case → **Export** tab → "Generate report package" (analyst/case_manager/admin).
- **API:**
  ```bash
  PKG=$(curl -s -X POST $B/cases/$CASE/report/package -H "$(hdr ana)" | jq -r .id)
  curl -s $B/report-packages/$PKG/report -H "$(hdr ana)" | head -5
  curl -s $B/report-packages/$PKG/manifest -H "$(hdr ana)" | jq '.counts'
  ```

## 7. Partner report access

- **UI:** switch to `partner` → **Reports** page shows the published packages for assigned
  cases (the partner cannot open the case workspace at all).
- **API:**
  ```bash
  curl -s $B/report-packages -H "$(hdr partner)" | jq '.[].title'             # the package
  curl -s -o /dev/null -w "partner evidence -> %{http_code}\n" $B/cases/$CASE/evidence -H "$(hdr partner)"  # 403
  curl -s -o /dev/null -w "partner graph    -> %{http_code}\n" $B/cases/$CASE/graph    -H "$(hdr partner)"  # 403
  ```

## 8. Analyst Copilot (proposed-only)

- **UI:** Case → **Copilot** tab — note the banner "AI suggestions are proposed only. Human
  review is required." Try Summarize, Suggest relationships, Check citations.
- **API:**
  ```bash
  curl -s -X POST $B/cases/$CASE/ai/summarize -H "$(hdr ana)" -H 'content-type: application/json' \
    -d '{}' | jq '{summary, meta:{generated_by_ai:.meta.generated_by_ai, status:.meta.status, review:.meta.requires_human_review}}'
  curl -s -o /dev/null -w "partner copilot -> %{http_code}\n" -X POST $B/cases/$CASE/ai/summarize \
    -H "$(hdr partner)" -H 'content-type: application/json' -d '{}'           # 403
  ```
  Copilot output is always `status: "proposed"` / `requires_human_review: true` and never
  writes case material.

## 9. Audit log review

- **UI:** Case → **Audit log** tab (case_manager / reviewer / admin).
- **API:**
  ```bash
  curl -s $B/cases/$CASE/audit -H "$(hdr admin)" | jq -r '.[].action' | sort | uniq -c
  ```
  Every step above appears: `observation.intake`, `review.approve`, `evidence.uploaded`,
  `evidence.verified`, `evidence.downloaded`, `report_package.generated`,
  `ai_assist.summarize`, and membership changes.

## What to point out during a demo

- Need-to-know: `nomad` sees nothing; the same 403 for a real and a fake case id.
- Separation of duties: analysts propose, reviewers decide, no self-approval.
- Integrity: SHA-256 on every uploaded file; verify re-hashes the stored bytes.
- Partner isolation: approved packages only, never raw evidence/graph/audit.
- AI is propose-only: nothing the Copilot produces is authoritative without human review.
- Everything consequential is in the append-only audit log.
