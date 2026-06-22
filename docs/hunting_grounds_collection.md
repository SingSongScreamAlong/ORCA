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

## Referral to law enforcement (locate → case)

`GET /api/v1/hunting/sources/{id}/referral` builds a **referral dossier** for a source: the
located identifiers, the text leads, and the relationship map ORCA assembled, together with the
source's provenance and the **lawful basis** it was watched under. It returns structured JSON plus
a ready-to-hand `summary_markdown`. **No media** — pointers and metadata only. It does not unmask
anyone: identifiers are leads for lawful follow-up, and de-anonymization (handle → person) is law
enforcement's job with legal process. Requires `READ_CASE_MATERIAL`; generating one is audited as
`hunting.referral.generated`. This is the seam where ORCA's recon becomes a Project 1591 referral.

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
