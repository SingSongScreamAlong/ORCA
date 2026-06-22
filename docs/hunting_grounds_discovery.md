# Hunting Grounds — Autonomous Discovery

The **engine that lets ORCA seek**. Where the [registry](hunting_grounds_registry.md) governs
*which* sources may be monitored, autonomous discovery is how ORCA *finds new candidate venues*
in an area of responsibility — so the operator need not trawl traumatic listings by hand. It is
the executable form of the "discovery only proposes" rule in the
[charter](hunting_grounds_charter.md).

The whole design exists so **autonomy can never outrun the law**.

## The four guardrails (enforced in code, not by convention)

1. **It only ever proposes.** Every candidate is fed through `HuntingRegistryService.run_discovery`
   and enters the registry as `proposed` (deduped by URL). There is **no path** from discovery to
   `authorized` or `monitored`. A human administrator still authorizes each source, with a
   recorded lawful basis, before anything is ever watched.
2. **It reaches out only through a configured, lawful source.** The real (`http`) provider is a
   generic client for a discovery/OSINT endpoint **you** configure and that **you have a recorded
   lawful basis to query**. It does **not** scrape search engines or sites against their terms, and
   it does **not** crawl the dark web. The provider refuses to build without
   `ORCA_HUNTING_DISCOVERY_LAWFUL_BASIS` set.
3. **It is CSAM-safe by construction.** Candidates carry text/metadata only — a name, a URL, a
   category, a note. There is **no media field anywhere** in the pipeline, so imagery cannot be
   fetched, stored, or transmitted. Suspected-minor concerns route to the
   [CSAM hard-stop](hunting_grounds_csam_hardstop.md) (report-only, never-store).
4. **It is disabled by default.** With no configuration the engine is off and the endpoint
   returns a clear `400`. The `mock` provider exists only to exercise the wiring with synthetic
   `.invalid` candidates (no network).

## Providers

Selected with `ORCA_HUNTING_DISCOVERY_PROVIDER`:

| Provider   | What it does                                                                 | Network |
|------------|------------------------------------------------------------------------------|---------|
| `disabled` | Off (default). The endpoint returns a clear, actionable `400`.               | none    |
| `mock`     | Deterministic synthetic `.invalid` candidates derived from the AOR.          | none    |
| `http`     | Generic read-only client for a **licensed** discovery/OSINT JSON endpoint.   | yes     |

## Configuration (`ORCA_HUNTING_DISCOVERY_*`)

| Variable                              | Required           | Purpose                                                            |
|---------------------------------------|--------------------|--------------------------------------------------------------------|
| `ORCA_HUNTING_DISCOVERY_PROVIDER`     | —                  | `disabled` (default), `mock`, or `http`.                           |
| `ORCA_HUNTING_DISCOVERY_URL`          | `http`             | The licensed endpoint (queried read-only with `?aor=&limit=`).     |
| `ORCA_HUNTING_DISCOVERY_API_KEY`      | optional           | Secret, sent as a `Bearer` token. **Never logged.**                |
| `ORCA_HUNTING_DISCOVERY_LAWFUL_BASIS` | `http`             | Recorded lawful basis. **Required to enable the `http` provider.** |
| `ORCA_HUNTING_DISCOVERY_RESULTS_PATH` | —                  | Dotted path to the results array (e.g. `data.items`). Default `results`. |
| `ORCA_HUNTING_DISCOVERY_NAME_FIELD`   | —                  | Per-item field for the venue name. Default `name`.                 |
| `ORCA_HUNTING_DISCOVERY_URL_FIELD`    | —                  | Per-item field for the venue URL. Default `url`.                   |
| `ORCA_HUNTING_DISCOVERY_CATEGORY`     | —                  | Default category for candidates. Default `escort_listing`.         |
| `ORCA_HUNTING_DISCOVERY_AORS`         | —                  | Comma-separated AOR watchlist **fallback** (the operator-managed watchlist takes precedence). |
| `ORCA_HUNTING_DISCOVERY_SCHEDULE_ENABLED` | —              | Start the continuous cadence. Default `false`.                     |
| `ORCA_HUNTING_DISCOVERY_SCHEDULE_INTERVAL_MINUTES` | —     | Sweep interval (≥1; a 60s floor applies). Default `60`.            |
| `ORCA_HUNTING_DISCOVERY_SCHEDULE_LIMIT` | —                | Candidates per AOR each automatic sweep. Default `10`.             |

The configuration is read into a frozen `HuntingDiscoveryConfig`. Secrets are redacted in
`repr`/`safe_dict`; the API key never appears in logs or error messages.

## Seeking across many areas — the sweep

`auto_discover` seeks one AOR; a **sweep** seeks across a list of AORs in one pass, so the
operator can cover the whole region at once. Target selection is layered: an explicit call/query
wins; otherwise the **operator-managed watchlist** (persisted) is used; otherwise the env
fallback (`ORCA_HUNTING_DISCOVERY_AORS`). The provider is built once and reused; because the
registry store updates synchronously, a venue found for an earlier AOR is skipped as a duplicate
if it recurs later **in the same sweep**.

### The operator-managed watchlist

Operators curate the AORs the cadence sweeps from the UI — no redeploy — under
`/api/v1/hunting/watchlist`:

- `GET /watchlist` — the current watchlist (`READ_CASE_MATERIAL`).
- `POST /watchlist` `{aor}` — add an AOR (admin-only, `201`; case-insensitive dedup).
- `DELETE /watchlist/{aor}` — remove one (admin-only, `204`).

Adds/removes are audited (`hunting.watchlist.added` / `hunting.watchlist.removed`). When the
persisted watchlist is empty, the `ORCA_HUNTING_DISCOVERY_AORS` env list still applies, so an
operator can ship a standing watchlist and refine it live.

## Seeking on its own — the continuous cadence

The strongest expression of "let the machine do the trawling": when
`ORCA_HUNTING_DISCOVERY_SCHEDULE_ENABLED=true`, ORCA runs a sweep across the watchlist on a fixed
interval, unattended. It inherits every guardrail — it **only proposes**, reaches out only
through the **configured lawful source**, and is **CSAM-safe**. Two gates keep it controllable:

- **Config gate.** The loop does not start unless the schedule is enabled; it is off in dev/CI.
- **Runtime kill-switch.** An administrator can `pause` (and `resume`) the cadence at any time
  without a redeploy. A paused loop skips its ticks but stays resident.

Each automatic run is attributed to a clear `system` actor and recorded via the sweep audit, so an
unattended cadence is still fully accountable. The loop is thin — it sleeps the interval and calls
the same run path as the admin **run now** trigger, so manual and automatic runs behave identically.
Each tick also runs an [automated collection](hunting_grounds_collection.md) sweep over the
monitored sources (independently gated; a collection failure never blocks discovery).

Schedule API (all under `/api/v1/hunting/discovery/schedule`):

- `GET /schedule` — posture (enabled, paused, running, interval, run count, last run). Readable
  with `READ_CASE_MATERIAL`.
- `POST /schedule/pause` · `POST /schedule/resume` — the kill-switch (admin-only).
- `POST /schedule/run-now` — run one sweep immediately, attributed to the triggering admin
  (admin-only); `400`/`502` mirror the sweep endpoint.

## Dark web (Tor / `.onion`)

The same `http` provider can reach **`.onion`** sources by routing through a **Tor SOCKS proxy**
(your hardened VM/VPN): set `ORCA_HUNTING_DISCOVERY_TOR_PROXY=socks5://127.0.0.1:9050` and install
the transport (`pip install ".[tor]"`). Tor is a *transport* — the locate-only, text/metadata,
CSAM-safe rules are unchanged; ORCA still fetches no media.

Because dark-web access carries legal exposure that clearnet OSINT does not, it is gated behind an
explicit acknowledgment: the provider **refuses to build** unless
`ORCA_HUNTING_DISCOVERY_DARKWEB_ACK=true`, which records that **legal counsel sign-off** and
**law-enforcement deconfliction** are in place (alongside the always-required lawful basis). The
status surfaces `tor_enabled` / `darkweb_acknowledged`. This mirrors the registry's
authorization-first gate — autonomy never reaches the dark web without a recorded human decision.

## Idempotent re-runs — URL normalization

Autonomous discovery is meant to run repeatedly, so it must not silt the registry up with
near-duplicates. De-duplication compares a **normalized** URL key (`normalize_url`): scheme/host
lower-cased, a leading `www.` dropped, a trailing slash and any `#fragment` removed. The source
keeps its original, clickable URL; only the *comparison key* is normalized. Query strings are
**preserved** — they can distinguish one listing from another.

## Expected endpoint shape (`http` provider)

The provider issues **one** read-only `GET` per pass:

```
GET {URL}?aor={aor}&limit={n}
Authorization: Bearer {API_KEY}      # only if a key is configured
Accept: application/json
```

and expects JSON it can map with the configured path/fields, e.g. with the defaults:

```json
{ "results": [ { "name": "Example RI listings", "url": "https://example.invalid/ri" } ] }
```

Items without a URL are skipped (a candidate must be addressable). Errors are surfaced as a
**secret-free** `DiscoveryConnectionError` — only a safe summary (HTTP status, host) is included.

## API

- `GET /api/v1/hunting/discovery/status` — secret-free posture (provider, enabled, configured,
  lawful-basis-recorded, host, AOR watchlist). Readable by anyone with `READ_CASE_MATERIAL`.
- `POST /api/v1/hunting/discovery/auto?aor={aor}&limit={n}` — seek one AOR. Requires
  `CREATE_OBSERVATION`. Returns a `HuntingDiscoveryResult` (`proposed`, `skipped_existing`,
  `provider`). Returns `400` when disabled/misconfigured, `502` on an upstream/network failure.
- `POST /api/v1/hunting/discovery/sweep?aors={a,b}&limit={n}` — seek across many AORs in one
  pass. Requires `CREATE_OBSERVATION`. `aors` is optional (comma-separated); with neither it nor
  a configured watchlist present, returns a clear `400`. Returns a `HuntingDiscoverySweepResult`
  (`aors`, per-AOR `results`, `total_proposed`, `total_skipped`, `provider`).
- Every run is recorded in the central append-only audit log — `hunting.discovery.auto`
  (`{aor, provider, proposed, skipped_existing}`) or `hunting.discovery.sweep`
  (`{aors, provider, total_proposed, total_skipped}`) — and each proposed source additionally
  logs `hunting.source.proposed`.

Manual discovery (`POST /hunting/discovery/run`, operator-pasted candidates) remains available
and behaves identically downstream — both only ever propose.

## How to turn it on (real source)

1. Obtain a source you are **licensed** to query and record the lawful basis with counsel.
2. Set `ORCA_HUNTING_DISCOVERY_PROVIDER=http`, `ORCA_HUNTING_DISCOVERY_URL=…`, the lawful basis,
   and (if needed) the API key and field/path mappings. Never commit real values.
3. Confirm `GET /hunting/discovery/status` shows `configured: true`.
4. Run a pass from the **Hunting Grounds → Autonomous discovery** card (or the API). Review the
   proposed sources; an administrator authorizes each before anything is monitored.

Until those steps are complete the engine stays disabled — which is the point.
