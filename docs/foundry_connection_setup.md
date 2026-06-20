# Foundry Connection Setup (Manual)

How to point ORCA's v1.1 connection spike at a real Palantir Foundry tenant for a
**read-only** check. This is optional and never required for development or CI — ORCA runs
fully on the deterministic mock client with no credentials.

> **Never commit credentials.** Put them only in a local `.env` (gitignored). `.env.example`
> contains placeholders. ORCA redacts secrets in logs/health output, but the operator is
> still responsible for keeping `.env` private.

## 1. Choose an auth method

The spike supports two methods — provide **one**:

- **Bearer token:** set `ORCA_FOUNDRY_TOKEN`.
- **OAuth2 client credentials:** set `ORCA_FOUNDRY_CLIENT_ID` and `ORCA_FOUNDRY_CLIENT_SECRET`.

## 2. Set environment variables

In `backend/.env` (copy from `backend/.env.example`):

```bash
ORCA_FOUNDRY_ENABLED=true
ORCA_FOUNDRY_TENANT_URL=https://your-tenant.palantirfoundry.com
ORCA_FOUNDRY_ONTOLOGY_API_NAME=your-ontology-api-name

# one auth method:
ORCA_FOUNDRY_TOKEN=...                       # OR
# ORCA_FOUNDRY_CLIENT_ID=...
# ORCA_FOUNDRY_CLIENT_SECRET=...

# a single harmless demo object to read:
ORCA_FOUNDRY_TEST_OBJECT_TYPE=OrcaCase
ORCA_FOUNDRY_TEST_OBJECT_ID=<a-non-sensitive-demo-object-id>
```

## 3. Run the read-only health check

```bash
cd backend
python -m app.foundry.health
# or, with the server running, as an admin:
curl -s http://localhost:8000/api/v1/integrations/foundry/health -H "X-ORCA-User: admin" | jq
```

### Expected results in v1.1

- **Disabled** (default): `{"enabled": false, "mode": "disabled", "ok": null}`.
- **Enabled but misconfigured:** `ok: false` with an `errors` list naming the missing vars.
- **Enabled and configured, no SDK installed:** `ok: false` with a clear message that the
  Palantir SDK (`ORCA_FOUNDRY_SDK_MODULE`, default `foundry_sdk`) is not installed. **This
  is the expected state today** — the spike ships the abstraction + mock, not a wired SDK.

The health output never contains secret values (only a host display and redacted markers).

## 4. Wiring a real SDK (future work)

To make real read-only calls, implement the methods in
`backend/app/foundry/real_client.py` against the official Palantir OSDK/client once its
package and read API are confirmed. Keep it **read-only**, keep secrets in env, and surface
failures through `FoundryError` subclasses (which must remain secret-free). Set
`ORCA_FOUNDRY_SDK_MODULE` if the package name differs from the default probe.

## Safety reminders

- Read-only only — no writes to Foundry, no sync, no AIP execution.
- Use a **non-sensitive demo object** for the first connection test.
- Do not transmit raw evidence files to Foundry.
- Do not paste tenant secrets into docs, issues, or commit messages.
- See [`v1.1_foundry_connection_spike.md`](v1.1_foundry_connection_spike.md) and
  [`safety_and_handling.md`](safety_and_handling.md).
