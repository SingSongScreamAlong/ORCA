# Hunting Grounds — CSAM hard-stop (suspected-minor escalation)

The charter's most important safety promise, made executable: a **report-only, never-store**
escalation channel for suspected-minor / CSAM material. ORCA is a **referral source** — it
**flags and routes**; a human files the **NCMEC CyberTipline** report; **ORCA never stores or
transmits the material.**

> **Why this exists before any collector.** In 1591 work the system *will* encounter CSAM.
> The lawful posture is *detect → report → do not retain*, because possession is itself a
> crime. This mechanism is built so the only thing ORCA ever holds is a minimal **pointer** and
> the **NCMEC report reference** — never the content.

## What it is — and is not

- **Is:** a way to raise a minimal, urgent flag (which source/URL, when, who, and a short
  *concern* describing why), route it to an admin queue, and **track** that an NCMEC report was
  filed (by reference number).
- **Is not:** storage of the material; automated transmission to NCMEC; an evidence record of
  the content. There is **no media field** anywhere in this path. The `concern` field is a
  pointer for the human filer — operators are instructed **not** to paste illegal content into
  it, and the UI says so.

## Lifecycle

```
open ──report (NCMEC ref)──▶ reported ──close──▶ closed
  └──dismiss (not CSAM)──▶ dismissed
```

- **Raise** (`POST /hunting/escalations`, any operator with `create_observation`): records the
  concern; status `open`.
- **Report** (`POST /hunting/escalations/{id}/report`, **admin**): records the NCMEC CyberTipline
  reference; status `reported`. (Filing the report is a human action outside ORCA.)
- **Close** (admin): after reporting.
- **Dismiss** (admin): if reviewed and found not to be CSAM.

Listing and all decisions are **admin-only**; every transition is recorded in an append-only
history.

## UI

On the **/hunting** page:
- A red **"⚑ Flag suspected minor / CSAM"** action on each *monitored* source (operators), with
  a prominent "report-only, describe the concern — do not paste content" warning.
- An **Escalations** queue at the top (admins only — the fetch 403s for everyone else) to record
  the NCMEC reference, close, or dismiss.

## Honest limits

- ORCA does **not** integrate with the NCMEC CyberTipline API — filing is a deliberate human
  step; this tracks it. The exact reporting workflow/obligations should be confirmed with
  counsel for the operating entity.
- This is the *manual triage* hard-stop. When a live collector is built, the same principle
  applies upstream: indicator hits route here and **media is never fetched or stored**.

See [`hunting_grounds_charter.md`](hunting_grounds_charter.md) for the full envelope.
