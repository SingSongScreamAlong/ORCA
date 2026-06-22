# Foundry Connection Setup (Manual)

How to point ORCA's Foundry connector at a real Palantir Foundry tenant for a **read-only**
check. As of **v1.2** the default client (`ORCA_FOUNDRY_CLIENT=rest`) is a real httpx REST
connector that calls Foundry's documented v2 API; v1.1 shipped only a mock + SDK placeholder.
This is optional and never required for development or CI — ORCA runs fully on the
deterministic mock client with no credentials.

> **Never commit credentials.** Put them only in a local `.env` (gitignored). `.env.example`
> contains placeholders. ORCA redacts secrets in logs/health output, but the operator is
> still responsible for keeping `.env` private.

## 1. Choose an auth method

The connector supports two methods — provide **one**:

- **Bearer token (user token):** set `ORCA_FOUNDRY_TOKEN` (used directly; no token exchange).
  Generate one in Foundry under **User Settings → Tokens → Create token**. This is the
  simplest path and works on any enrollment plan. Note a user token carries *your* full
  permissions and expires, so keep it private and short-lived — good for connection tests and
  single-user setups.
- **OAuth2 client credentials (service identity):** set `ORCA_FOUNDRY_CLIENT_ID` and
  `ORCA_FOUNDRY_CLIENT_SECRET`. The REST connector exchanges these at
  `POST {tenant}/multipass/api/oauth2/token` (`grant_type=client_credentials`) and caches the
  returned access token. If your tenant requires explicit scopes for ontology reads, set
  `ORCA_FOUNDRY_SCOPES` (space-separated).

> **Enrollment-plan note.** Creating a *Backend service* application in the Developer Console
> shows whether the **client-credentials grant** is available for your organization. Some
> enrollment plans do **not** include it (the console will say a *public client* will be
> created and you "will not need to handle client secrets"). On such a plan, use the **user
> token** path above; the connector will use client credentials automatically once a plan
> that includes the grant is in place — no code change.

## 2. Set environment variables

In `backend/.env` (copy from `backend/.env.example`):

```bash
ORCA_FOUNDRY_ENABLED=true
ORCA_FOUNDRY_CLIENT=rest                      # real REST connector (default)
ORCA_FOUNDRY_TENANT_URL=https://your-tenant.palantirfoundry.com
ORCA_FOUNDRY_ONTOLOGY_API_NAME=your-ontology-api-name

# one auth method:
ORCA_FOUNDRY_TOKEN=...                       # OR
# ORCA_FOUNDRY_CLIENT_ID=...
# ORCA_FOUNDRY_CLIENT_SECRET=...
# ORCA_FOUNDRY_SCOPES=                        # optional, only if your tenant requires scopes

# a single harmless demo object to read:
ORCA_FOUNDRY_TEST_OBJECT_TYPE=OrcaCase
ORCA_FOUNDRY_TEST_OBJECT_ID=<a-non-sensitive-demo-object-id>
```

For the ORCA tenant, `ORCA_FOUNDRY_TENANT_URL` is the host shown in the address bar (e.g.
`https://orca.usw-23.palantirfoundry.com`). Don't know your ontology's API name yet? You can
set `ORCA_FOUNDRY_ONTOLOGY_API_NAME=unknown` for now — the health check only *lists* ontologies
and doesn't use it — then discover the real value in the next step.

## 2a. Discover ontology / object-type API names

With at least the tenant URL and an auth method set, list what your credential can see:

```bash
cd backend
python -m app.foundry.discover
```

It prints the ontologies (their `apiName`s) and, once `ORCA_FOUNDRY_ONTOLOGY_API_NAME` is set,
the object types in that ontology — all read-only metadata. Copy the ontology's `apiName` (it
looks like `ontology-<uuid>`) into `ORCA_FOUNDRY_ONTOLOGY_API_NAME`. Both CLIs load
`backend/.env` automatically and never print secrets.

## 3. Run the read-only health check

```bash
cd backend
python -m app.foundry.health
# or, with the server running, as an admin:
curl -s http://localhost:8000/api/v1/integrations/foundry/health -H "X-ORCA-User: admin" | jq
```

### Expected results (v1.2, REST connector)

- **Disabled** (default): `{"enabled": false, "mode": "disabled", "ok": null}`.
- **Enabled but misconfigured:** `ok: false` with an `errors` list naming the missing vars.
- **Enabled, configured, tenant reachable:** `ok: true`, `mode: "real"`, with a `result`
  carrying an `ontology_count` (from the read-only `GET /api/v2/ontologies`).
- **Enabled but auth/scope/path rejected:** `ok: false` with a clear, **secret-free** message
  such as `OAuth2 token request was rejected (HTTP 401)` or `GET api/v2/ontologies returned
  HTTP 403`. Re-check the auth method, the scopes, and the tenant URL.

The health output never contains secret values (only a host display and redacted markers).

> If you prefer the official Palantir SDK over REST, set `ORCA_FOUNDRY_CLIENT=sdk`. That path
> is still the honest v1.1 placeholder: it probes for an SDK module
> (`ORCA_FOUNDRY_SDK_MODULE`, default `foundry_sdk`) and fails gracefully if it is not
> installed/implemented. The REST connector (`rest`) is the working default.

## 4. Read a demo object (optional)

With the health check green, you can confirm an object read from a quick Python shell (still
read-only, one harmless object):

```bash
cd backend
python -c "
from app.foundry.config import FoundryConfig
from app.foundry.client import build_foundry_client
c = build_foundry_client(FoundryConfig.from_env())
print(c.get_object_type_metadata('OrcaCase'))      # object-type metadata
"
```

Use a non-sensitive demo object type/id. To wire object reads into a workflow later, keep
them **read-only**, keep secrets in env, and surface failures through `FoundryError`
subclasses (which must remain secret-free).

## Safety reminders

- Read-only only — no writes to Foundry, no sync, no AIP execution.
- Use a **non-sensitive demo object** for the first connection test.
- Do not transmit raw evidence files to Foundry.
- Do not paste tenant secrets into docs, issues, or commit messages.
- See [`v1.2_foundry_rest_connector.md`](v1.2_foundry_rest_connector.md),
  [`v1.1_foundry_connection_spike.md`](v1.1_foundry_connection_spike.md), and
  [`safety_and_handling.md`](safety_and_handling.md).
