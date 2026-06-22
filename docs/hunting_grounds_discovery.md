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

The configuration is read into a frozen `HuntingDiscoveryConfig`. Secrets are redacted in
`repr`/`safe_dict`; the API key never appears in logs or error messages.

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
  lawful-basis-recorded, host). Readable by anyone with `READ_CASE_MATERIAL`.
- `POST /api/v1/hunting/discovery/auto?aor={aor}&limit={n}` — run a pass. Requires
  `CREATE_OBSERVATION`. Returns a `HuntingDiscoveryResult` (`proposed`, `skipped_existing`,
  `provider`). Returns `400` when disabled/misconfigured, `502` on an upstream/network failure.
- Every run is recorded in the central append-only audit log as `hunting.discovery.auto`
  (`{aor, provider, proposed, skipped_existing}`), and each proposed source additionally logs
  `hunting.source.proposed`.

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
