# ORCA Frontend

The analyst application. Next.js (App Router) + TypeScript + Tailwind.

## Design philosophy

Evidence-first, calm, professional, information dense, with minimal visual noise. The
evidence is the focus; the interface stays out of the way.

It is deliberately **not** a cyberpunk or "command center" aesthetic — no neon, no
hacker styling, no futuristic theming. The palette is a restrained slate neutral with a
single muted accent. Confidence is shown in calm, legible bands rather than alarm
colors.

## Screens

| Route            | Screen        | Purpose                                                     |
| ---------------- | ------------- | ----------------------------------------------------------- |
| `/`              | Dashboard     | What is new, what changed, what requires review, health.    |
| `/review`        | Review Queue  | The most important screen — decide proposed items.          |
| `/observations`  | Observations  | The atomic units of truth, with source and references.      |
| `/entities`      | Entities      | Real-world things observations reference.                   |
| `/relationships` | Relationships | Evidence-backed links, with status and support.             |
| `/clusters`      | Clusters      | Candidate patterns grouping entities and observations.      |
| `/cases`         | Cases         | Analyst work products (Phase 3).                            |
| `/reports`       | Reports       | Authored analytic products (Phase 3).                       |

### The Review Queue

The review queue is where "AI proposes, analysts decide" happens. Each item shows the
four things an analyst needs:

1. **Why it was surfaced** — the rationale.
2. **Supporting evidence** — the linked artifacts.
3. **Confidence** — band and percentage.
4. **Actions** — Approve, Reject, Needs review.

Decisions post to the backend, which records them in the append-only audit log.

## Architecture

- **Server components** fetch from the backend and render evidence (`lib/api.ts`).
- The review actions are a small **client component** that posts decisions and refreshes.
- The frontend holds **no authority** of its own — it renders what the backend returns
  and records analyst decisions the backend validates and audits.
- Types in `lib/types.ts` mirror the API contract (`backend/app/schemas`).

## Running locally

```bash
cd frontend
cp .env.example .env.local        # points at http://localhost:8000/api/v1
npm install
npm run dev                       # http://localhost:3000
```

The backend must be running for data to appear; if it is not reachable, each screen
shows a calm notice rather than failing.

## Scripts

| Command             | Purpose                          |
| ------------------- | -------------------------------- |
| `npm run dev`       | Start the dev server.            |
| `npm run build`     | Production build.                |
| `npm run start`     | Serve the production build.      |
| `npm run lint`      | ESLint (next/core-web-vitals).   |
| `npm run typecheck` | TypeScript, no emit.             |
