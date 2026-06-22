# Hunting Grounds — Charter & Operating Envelope

> **Status: charter (governance), not an implemented collector.** This document defines the
> in-bounds envelope, the hard limits, and the lifecycle that *every* Hunting Grounds
> capability must pass through. No collector ships until it conforms to this and clears the
> per-source legal review described below. It expands ORCA's mission deliberately and in
> writing — see [`mission.md`](mission.md) and [`safety_and_handling.md`](safety_and_handling.md).

## Purpose

Hunting Grounds is ORCA's **reconnaissance and monitoring** layer for lawful anti-trafficking
OSINT. Its job is to **take the manual trawling off the operator** — discovering and watching
*public or authorized* venues where commercial sexual exploitation may be advertised, and
surfacing **candidate leads** for a human analyst to review and (later) refer to law
enforcement.

Two outcomes drive the design:

1. **Reduce operator exposure.** Automating discovery and first-pass triage means a person is
   not repeatedly, manually exposed to traumatic material. This protects analyst wellbeing and
   extends their effective tenure — a primary, first-class objective, not a side effect.
2. **Build the regional picture.** Aggregate reviewed leads into an Area-of-Responsibility
   (AOR) common operating picture — entities, recurring identifiers, venues, and the links
   between them — so the operator watches a picture instead of scanning sources.

## Role: ISR, not a strike — OSINT, not SIGINT

Hunting Grounds **observes and proposes; analysts decide; law enforcement acts.** It is an
intelligence/analysis function. It does **not** pursue, contact, or act against any person. It
is open-source intelligence fusion — never signals intelligence, interception, or intrusion.

## In bounds

- **Discovery** of candidate *public* venues by lawful means (licensed search/OSINT APIs,
  link-graph expansion from already-authorized sources, operator-provided seed lists).
- **Monitoring** of sources that have been **authorized** through the registry gate below.
- **Indicator-based triage** that produces *proposed* leads for human review.
- **Entity / relationship / AOR** picture building from reviewed material.
- **Referral packaging** with chain of custody (export later; in-house for now).

## Out of bounds — hard limits, on any platform (including Foundry)

- **No SIGINT / intrusion:** no interception of communications, no hacking, no use of
  credentials, no access to non-public or private accounts, no CFAA-type access.
- **No surveillance of identified individuals.** Lead generation is venue/pattern-based, not
  person-targeted; Hunting Grounds does not covertly monitor a named person.
- **No biometric / face matching.**
- **No contact, engagement, or undercover activity** with subjects or victims.
- **No autonomous conclusions, accusations, or auto-referrals.** A human decides every lead.
- **No access in violation of a source's terms or applicable law** without documented legal
  sign-off for that source and method.
- **No CSAM handling** — see the hard-stop below.

## CSAM hard-stop (absolute, engineered)

This domain *will* surface child sexual abuse material. The system is built so it cannot
possess it:

1. It operates on **text and metadata** — it does **not** auto-download, store, hash, or
   display imagery from monitored sources.
2. Indicators suggesting a **minor or CSAM** trigger: (a) **no storage** of the material;
   (b) an **urgent human-review flag**; (c) routing to the **NCMEC CyberTipline** reporting
   path.
3. ORCA is a **referral source** — it reports; it does not retain illegal material.

This is implemented in the pipeline, not left to procedure.

## Operator protection — trauma-informed by design

Because reducing exposure is a goal, not an afterthought: imagery is **withheld or blurred by
default**; analysts work from **text, indicators, and metadata**; any reveal of underlying
media is **explicit, justified, and audited**. The machine absorbs the scanning burden so the
human is shielded from as much of it as possible.

## The discovery → authorize → monitor lifecycle (authorization-first)

Auto-discovery **never** silently enrolls a site into monitoring. The gate is explicit:

```
 discover  ─▶  proposed source ─▶ [human + legal review] ─▶ authorized ─▶ monitored
                                          │
                                          └─▶ rejected (recorded, not monitored)
   authorized ─▶ suspended / retired   (reversible, audited)
```

- A discovered candidate enters the **source registry** as `proposed`, with its discovery
  provenance (how it was found).
- It becomes `authorized` **only** after a human records its **lawful basis, access method,
  and jurisdiction**, with legal review noted.
- Only `authorized` sources are monitored. Status changes are reversible and **audited**.

This preserves ORCA's rule — *authorization and lawful basis precede any action by the tool* —
even though the hunt runs independently.

## Minimization & victim protection

People advertised in these venues are presumed **potential victims**. Collect the **minimum
necessary**; minimize and protect their PII; never republish; apply retention limits. The
objective is identifying **trafficking patterns** and enabling protection — never exposing or
re-victimizing the advertised person.

## Lawful basis & legal review (per source)

No source is monitored until its lawful basis, access method, and jurisdiction are documented,
legally reviewed, and recorded in the registry. The **discovery layer's own methods** (which
APIs/sources it queries) are subject to the same review.

## Audit & accountability

Every discovery, authorization decision, monitoring action, lead, media reveal, and (later)
referral is written to ORCA's **append-only audit log**, attributable to a person or to an
explicitly authorized automated job.

## Initial scope

- **AOR:** New England — initially **Rhode Island and the surrounding area**.
- **Source category:** escort / commercial-sex public listings and similar advertising venues.
- **Disposition:** **in-house** for now; law-enforcement referral export to follow (built on
  ORCA's approved-only report-package export).

## Relationship to ORCA's invariants

Hunting Grounds **inherits every ORCA invariant** — propose-only / human-decided,
evidence-backed and hash-verifiable, need-to-know, append-only audit, no CSAM — and **adds**
the source-authorization gate, the CSAM/NCMEC hard-stop, and the trauma-minimization
requirements on top. Nothing here loosens an existing boundary; it tightens new ones around a
new capability.

## Build sequence (governed)

1. **This charter** (the written envelope).
2. **Source/NAI registry** with the `proposed → authorized → monitored → suspended/retired`
   lifecycle and lawful-basis metadata — the gate everything passes through.
3. **AOR picture** scaffold (over the entity/relationship graph).
4. **Lead → review** wiring (propose-only, into the existing review queue).
5. **Per-source collectors** — discovery first, then monitoring — each shipped **only** after
   its source clears the registry gate and a CSAM-safe fetch design is in place.
6. **LE referral export** (extends approved-only report packages).

Foundry is the scheduling / ingestion / normalization / entity-resolution **engine** for steps
5–6; ORCA remains the system of record, the registry, the review authority, the AOR picture,
and the audit.
