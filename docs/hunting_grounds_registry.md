# Hunting Grounds — Source / NAI Registry

The **executable gate** described by [`hunting_grounds_charter.md`](hunting_grounds_charter.md).
Before any collector exists, this registry makes the charter's *authorization-first* rule real
in code: a source cannot be monitored until a human authorizes it, and it cannot be authorized
without a recorded lawful basis. **No part of this monitors or collects anything** — it governs
*which* sources may ever be monitored.

## Lifecycle

```
proposed ──authorize──▶ authorized ──monitor──▶ monitored
   │                        │  ▲                    │
   └──reject──▶ rejected    │  └──── monitor ───────┤
                            └──── suspend ◀──────────┘
   authorized / monitored / suspended ──retire──▶ retired
```

Enforced invariants (in `HuntingRegistryService`, not by convention):

- **Discovery only proposes.** A discovery job or an operator can create a source only as
  `proposed`. Auto-discovery never enrolls a site into monitoring. See
  [`hunting_grounds_discovery.md`](hunting_grounds_discovery.md) for the autonomous engine.
- **Authorization requires a lawful-basis record.** A source moves `proposed → authorized`
  **only** with a complete record: `lawful_basis`, `access_method`, and `jurisdiction` (all
  required; an optional legal-review note is captured too). The authorizer is recorded.
- **Monitoring requires prior authorization.** A source reaches `monitored` only from
  `authorized` (or `suspended`) — never straight from `proposed`.
- **Every transition is recorded.** Each source carries an append-only `history` of
  `{from, to, by, at, note}` entries.

## API (`/api/v1/hunting/sources`)

| Method & path | Who | Action |
| ------------- | --- | ------ |
| `GET /hunting/sources?status=&aor=` | analyst+ | list / filter sources |
| `POST /hunting/sources` | analyst+ | **propose** a candidate (enters `proposed`) |
| `GET /hunting/sources/{id}` | analyst+ | get one (incl. history) |
| `POST /hunting/sources/{id}/authorize` | **admin** | authorize (body: lawful basis / access method / jurisdiction) |
| `POST /hunting/sources/{id}/reject` | **admin** | reject a proposal (body: reason) |
| `POST /hunting/sources/{id}/monitor` | **admin** | begin monitoring an authorized source |
| `POST /hunting/sources/{id}/suspend` | **admin** | suspend (body: reason) |
| `POST /hunting/sources/{id}/retire` | **admin** | retire (body: reason) |

Proposing is an operator action (`CREATE_OBSERVATION`); **every lifecycle decision is
admin-only** — the human + legal gate. In practice that's a two-person split: an analyst
proposes, an administrator authorizes. Invalid transitions return `422`; an authorize call
missing any required field is rejected by schema validation (`422`).

## Storage

The registry and the escalation channel are persisted **through the unit of work**, like every
other ORCA object: the in-memory development store (`uow.hunting_sources` / `uow.hunting_escalations`,
reset between tests) or **PostgreSQL** as the system of record. On PostgreSQL each record is a row
keyed by `id` with indexed `status`/`aor` columns and a JSONB `document` holding the full read
model — including the append-only `history` — so proposals and authorizations survive a restart.
See the `hunting_sources` / `hunting_escalations` tables in `backend/db/sql/schema.sql` and
migration `0002_hunting_grounds`. Privileged actions are also written to the central append-only
audit log.

## What's next (gated on this)

- **AOR picture** over the entity/relationship graph.
- **Lead → review** wiring (propose-only).
- **Per-source collectors** — discovery first, then monitoring — each shipped **only** after
  its source has passed this gate and a CSAM-safe fetch design is in place.

See the charter for the full envelope, the CSAM hard-stop, and the trauma-minimization
requirements that every later step inherits.
