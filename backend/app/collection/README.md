# Hunting Grounds — collection (interfaces only)

"Hunting Grounds" is ORCA's future collection engine. In this repository it exists as
**interface definitions only**. There is no collection logic here, by design.

## Future responsibilities

- **Monitoring** — watch configured sources for new material.
- **Archiving** — preserve material as it is found.
- **Entity extraction** — extract candidate entities from collected material.
- **Evidence preservation** — capture and hash artifacts at the moment of collection.

## Design constraints (non-negotiable)

A collector is a **producer**, not an authority:

1. It produces **evidence** (preserved, hashed, immutable) and **observations**
   (append-only, attributed to a source).
2. Anything it infers — candidate entities, candidate relationships — is a
   **proposal**. It is created `system_proposed` / `proposed` and goes to the review
   queue.
3. It has **no privileged path**. It cannot confirm, cannot bypass review, and cannot
   bypass the audit log.
4. It operates only within the mission boundaries in [`docs/mission.md`](../../../docs/mission.md):
   no unauthorized access, no covert or real-time tracking of individuals, no
   detection evasion.

These constraints are why collection is specified before it is built: the interfaces
encode the boundaries.

## Files

- `interfaces.py` — `Collector`, `EvidencePreserver`, and `EntityExtractor` protocols,
  plus the data contracts (`CollectionTarget`, `CollectedItem`) they exchange.
