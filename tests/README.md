# Tests

Two kinds of tests live here.

| Directory          | What it checks                                                       |
| ------------------ | ------------------------------------------------------------------- |
| `tests/backend/`   | Backend behaviour: endpoints, ontology invariants, the review loop. |
| `tests/structure/` | Repository structure and the machine-readable ontology.             |

Both run under `pytest` from the `backend/` directory (its `pyproject.toml` lists both
paths and puts `app` on the import path):

```bash
cd backend
pip install -e ".[dev]"
python -m pytest -q
```

## What the backend tests cover

- **The review loop** (`test_review_loop.py`) — a system-proposed relationship is
  surfaced for review, an analyst decision transitions it, and the decision is written
  to the append-only audit log. This is the behavioural heart of ORCA.
- **Ontology invariants** — an observation must reference an existing source; a
  relationship must reference supporting observations; confidence stays in `[0, 1]`.
- **Entity deduplication** — the same `(type, value)` resolves to one entity.
- **Workers propose, never confirm** (`test_worker_proposer.py`).

## What the structure tests cover

- Required directories and documents exist and are non-empty.
- Every core ontology object has a schema file, versioned `0.1`.
- The ontology enums agree with the backend enums.
- Hunting Grounds (collection) remains interfaces only.
