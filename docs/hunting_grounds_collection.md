# Hunting Grounds — Automated Collection

Where [discovery](hunting_grounds_discovery.md) *finds* new venues, **collection** *pulls
candidate leads* from the venues ORCA already monitors — automating the first-pass triage that
would otherwise sit a person in front of traumatic listings. A collected lead becomes a
**proposed observation** in the review queue through the same seam as a hand-logged one
(`HuntingLeadService`): an analyst still decides, citing evidence, before anything supports a
relationship.

This is the most sensitive layer, so the boundary is enforced in code, not convention.

## The guardrails

1. **Monitored-only.** Collection runs **only** against sources the registry has moved to
   `monitored` — which required an administrator's authorization with a recorded lawful basis. A
   non-monitored source returns `422`.
2. **Proposes only.** Every lead enters the review queue as a *proposed* observation flagged for
   legal review. Nothing is auto-approved; "AI proposes, analysts decide" is unbroken.
3. **CSAM-safe by construction.** A collected lead carries **text and entity hints only** —
   `HuntingLeadCreate` has **no media field**, so the collector cannot fetch, store, or transmit
   imagery. The `http` provider reads only the configured *text* fields and never follows a media
   URL. Suspected-minor concerns route to the report-only [CSAM hard-stop](hunting_grounds_csam_hardstop.md).
4. **Configured lawful source only.** The real (`http`) provider talks to an endpoint you are
   licensed to query and have a recorded lawful basis for; it will not build without
   `ORCA_HUNTING_COLLECTION_LAWFUL_BASIS`. No scraping, no dark-web.
5. **Disabled by default.** Off until configured; the endpoints return a clear `400`. The `mock`
   provider exercises the wiring with synthetic offline leads (no network).

## Providers

Selected with `ORCA_HUNTING_COLLECTION_PROVIDER`:

| Provider   | What it does                                                                    | Network |
|------------|---------------------------------------------------------------------------------|---------|
| `disabled` | Off (default). The endpoints return a clear, actionable `400`.                  | none    |
| `mock`     | Deterministic synthetic text leads (with a phone hint) derived from the source. | none    |
| `http`     | Generic read-only client for a **licensed** collection JSON endpoint (text).    | yes     |

## Configuration (`ORCA_HUNTING_COLLECTION_*`)

| Variable                                  | Required | Purpose                                                          |
|-------------------------------------------|----------|------------------------------------------------------------------|
| `ORCA_HUNTING_COLLECTION_PROVIDER`        | —        | `disabled` (default), `mock`, or `http`.                         |
| `ORCA_HUNTING_COLLECTION_URL`             | `http`   | The licensed endpoint (queried read-only with `?source=&aor=&limit=`). |
| `ORCA_HUNTING_COLLECTION_API_KEY`         | optional | Secret, sent as a `Bearer` token. **Never logged.**              |
| `ORCA_HUNTING_COLLECTION_LAWFUL_BASIS`    | `http`   | Recorded lawful basis. **Required to enable the `http` provider.** |
| `ORCA_HUNTING_COLLECTION_RESULTS_PATH`    | —        | Dotted path to the results array. Default `results`.             |
| `ORCA_HUNTING_COLLECTION_SUMMARY_FIELD`   | —        | Per-item text summary field. Default `summary`.                  |
| `ORCA_HUNTING_COLLECTION_ENTITIES_FIELD`  | —        | Optional per-item `[{entity_type, value}]` list. Default `entities`. |
| `ORCA_HUNTING_COLLECTION_DEFAULT_CONFIDENCE` | —     | Confidence stamped on collected leads. Default `0.4`.            |

## Expected endpoint shape (`http` provider)

One read-only `GET` per source:

```
GET {URL}?source={source_url}&aor={aor}&limit={n}
Authorization: Bearer {API_KEY}      # only if a key is configured
Accept: application/json
```

mapped (with the defaults) from:

```json
{ "results": [
  { "summary": "Ad reuses phone +15555550142",
    "entities": [ { "entity_type": "phone_number", "value": "+15555550142" } ] }
] }
```

A row without a text `summary` is skipped; a malformed entity hint is dropped while the lead is
kept. **There is no media field** to read. Errors are surfaced as a **secret-free**
`CollectionConnectionError` (only HTTP status / host).

## Located identifiers (every lead, every source)

"Locate, don't collect": at ingestion, ORCA reads the lead **text** and extracts the *pointers
and identifiers* that build a case — **phone numbers, emails, crypto wallet addresses, `.onion`
services, URLs, and @handles** — resolving each into ORCA's entity graph. This runs on **every**
lead (hand-logged, clearnet collection, or any future dark-web source), so a number/handle/wallet
that recurs across listings collapses to one entity and cross-links automatically. It is purely
**additive** — the full text lead is preserved and explicit entity hints are kept; extraction only
surfaces *more* pointers. Extractors favour precision over recall, and everything remains a
proposal an analyst reviews. No media is ever read or stored (see `app/services/identifier_extraction.py`).

## API

- `GET /api/v1/hunting/collection/status` — secret-free posture. `READ_CASE_MATERIAL`.
- `POST /api/v1/hunting/sources/{id}/collect?limit={n}` — collect from one monitored source.
  `CREATE_OBSERVATION`. `422` if not monitored, `400` if disabled, `502` on upstream failure.
- `POST /api/v1/hunting/collection/run?limit={n}` — collect from **all** monitored sources.
  `CREATE_OBSERVATION`.
- Audited as `hunting.collection.run` / `hunting.collection.sweep`; each lead also creates the
  usual `observation.intake` record.

## Dark web (Tor / `.onion`)

Collection reaches **`.onion`** sources through a **Tor SOCKS proxy** the same way discovery does:
`ORCA_HUNTING_COLLECTION_TOR_PROXY=socks5://127.0.0.1:9050` plus `pip install ".[tor]"`. Tor is
only the transport — leads stay **text/metadata only, CSAM-safe, locate-don't-collect**. The
`.onion`/crypto/handle identifier extraction is already wired, so dark-web leads cross-link with
clearnet ones automatically. Access is gated behind `ORCA_HUNTING_COLLECTION_DARKWEB_ACK=true`
(records counsel sign-off + LE deconfliction); the provider refuses to build otherwise.

## AOR intelligence (cross-venue links)

`GET /api/v1/hunting/intel?aor=…` is the **common operating picture**: it reports which located
identifiers recur across **two or more** monitored venues. The same phone, wallet, `.onion`, or
handle seen in multiple places is the strongest signal that separate listings are one operation —
this is the seam where located leads become a case. It is **read-only** (proposes nothing) and
returns pointers/metadata only. The LE referral dossier is enriched with the same count: each
located identifier carries a `venue_count`, and cross-venue ones (`≥2`) are flagged in the markdown
and the UI. `READ_CASE_MATERIAL`.

### Identifier pivot — "where is this one?"

`GET /api/v1/hunting/intel/identifier?type=…&value=…` is the per-identifier axis of the picture:
given one located identifier, it returns **every** monitored venue it appears in (with the source,
AOR, text lead, and observation status), the distinct AORs, and the identifiers it **co-occurs**
with (link candidates, ranked by shared leads). This answers the operator's core question — *where
are this phone/wallet/handle/`.onion`'s listings and posts?* — so an analyst can assemble an LE
referral. `404` if the identifier was never located. Read-only; pointers/metadata only.
`READ_CASE_MATERIAL`. In the UI, selecting any cross-venue identifier expands its dossier in place.

### Operation cluster — "what's the whole network?"

`GET /api/v1/hunting/intel/operation?type=…&value=…` widens the pivot from direct co-occurrence to
the **whole operation**: the connected component around a seed identifier. Two located identifiers
are linked when they co-occur in the same lead **or** a relationship ties them; the operation is the
transitive closure from the seed across those edges. Where the AOR rollup is "everything in a
region," this is "everything in one network" — the seam that says *these scattered listings are one
operation*, regardless of AOR. Returns the member identifiers (with venue/lead counts), the venues
and AORs it touches, and the relationship map; the traversal is capped (`truncated` flags a very
large network). `404` if the seed was never located. Read-only; pointers/metadata only.
`READ_CASE_MATERIAL`. In the UI, "Reveal operation network" expands it inside the pivot panel.

## Cross-venue link proposal (intelligence → review queue)

`POST /api/v1/hunting/links/propose?aor=…` turns the cross-venue intelligence into reviewable case
links. For each identifier pair that co-occurs in **approved** leads across **two or more**
monitored venues, ORCA proposes an `appears_with` relationship (`system_proposed` / `proposed`) into
the review queue for an analyst to confirm. This preserves the lawful two-stage loop end to end: *AI
proposes the lead → an analyst approves the observation → the system proposes the cross-venue link →
an analyst approves the link.* Only **approved** observations are cited (an ontology invariant of the
relationship layer); nothing is auto-confirmed and existing links are never re-proposed.
`CREATE_OBSERVATION`. The "Suggest cross-venue links" action on the AOR intelligence card triggers it.

## Referral to law enforcement (locate → case)

`GET /api/v1/hunting/sources/{id}/referral` builds a **referral dossier** for a source: the
located identifiers, the text leads, and the relationship map ORCA assembled, together with the
source's provenance and the **lawful basis** it was watched under. It returns structured JSON plus
a ready-to-hand `summary_markdown`. **No media** — pointers and metadata only. It does not unmask
anyone: identifiers are leads for lawful follow-up, and de-anonymization (handle → person) is law
enforcement's job with legal process. Requires `READ_CASE_MATERIAL`; generating one is audited as
`hunting.referral.generated`. This is the seam where ORCA's recon becomes a Project 1591 referral.

### Per-identifier referral — the cross-venue case file

`GET /api/v1/hunting/intel/identifier/referral?type=…&value=…` is the per-**identifier** counterpart:
where the source referral is one venue, this assembles the case file for a single located identifier
across the **whole** hunting ground — every monitored venue it appears in (each with its lawful
basis), the text leads citing it, the identifiers it co-occurs with, and the relationships among
them, with a ready-to-hand `summary_markdown`. It is the natural follow-on to the identifier pivot:
locate an identifier everywhere, then hand LE the dossier. **No media** — pointers and metadata only.
`READ_CASE_MATERIAL`; `404` if the identifier was never located; audited as
`hunting.referral.identifier_generated`. In the UI it's a one-click action inside the pivot panel.

### AOR operation rollup — the regional case file

`GET /api/v1/hunting/intel/aor/referral?aor=…` is the widest referral: it consolidates a whole area
of responsibility into **one** operation dossier — every monitored venue in the region (each with
its lawful basis), all located identifiers (cross-venue ones flagged), the **cross-venue links**
that tie separate venues into one operation, and the relationship map, with a `summary_markdown`.
This is the "this is one trafficking operation" packet: per-source and per-identifier referrals
zoom in; the rollup is the regional picture. Always returns a package (empty when nothing is
monitored/located — no `404`). **No media** — pointers and metadata only. `READ_CASE_MATERIAL`;
audited as `hunting.referral.aor_generated`. In the UI it's a per-AOR action on the AOR picture.

### Operation referral — the linked-network case file

`GET /api/v1/hunting/intel/operation/referral?type=…&value=…` is the fourth referral tier: where the
AOR rollup bounds the case by **region**, this bounds it by the actual **linked network** — the
[operation cluster](#operation-cluster--whats-the-whole-network) around a seed identifier. It wraps
that connected component into an LE dossier: the member identifiers, the venues (each with lawful
basis), the relationship map, and a `summary_markdown`. Use it when the operation crosses AORs and a
region-scoped rollup would either miss members or sweep in unrelated ones. **No media** — pointers
and metadata only. `READ_CASE_MATERIAL`; `404` if the seed was never located; audited as
`hunting.referral.operation_generated`. In the UI it's a one-click action inside the revealed
operation network. Together the four tiers cover every scope an analyst hands to LE — **source**,
**identifier**, **AOR**, and **operation**.

### Referral history — the accountability view

`GET /api/v1/hunting/referrals` reads the append-only audit trail (`hunting.referral.*`, newest
first) into a referral history: each row records that a dossier was generated — its **tier**
(source / identifier / AOR / operation), the **subject**, the **author**, the **time**, and a short
count summary — **never the dossier's contents**. This closes the accountability loop on the
referral surface: an operator can see what has been handed to LE, at what scope, and by whom, without
re-opening or re-generating any dossier. Counts and pointers only. `READ_CASE_MATERIAL` (the same
gate as the referrals themselves). In the UI it's a "Referrals handed to law enforcement" card on the
Hunting Grounds page.

## On the cadence

When the [continuous cadence](hunting_grounds_discovery.md#seeking-on-its-own--the-continuous-cadence)
is enabled, each tick runs the discovery sweep **and then** a collection sweep over the monitored
sources, attributed to the `system` actor. Both are independently gated by their own provider
config (disabled by default), and a collection failure never blocks discovery (or the loop). The
schedule status surfaces the last collection run alongside discovery.

## How to turn it on (real source)

1. Authorize and monitor the source(s) you intend to collect from (records a lawful basis).
2. Obtain a licensed collection endpoint and record its lawful basis with counsel.
3. Set `ORCA_HUNTING_COLLECTION_PROVIDER=http`, `_URL`, `_LAWFUL_BASIS`, and (if needed) `_API_KEY`
   and the field/path mappings. Never commit real values.
4. Confirm `GET /hunting/collection/status` shows `configured: true`, then collect — every lead
   lands in the review queue for an analyst to decide.

Until those steps are complete, collection stays disabled — which is the point.
