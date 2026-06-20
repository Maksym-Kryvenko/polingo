# Horizontal Execution Model — Design

**Date:** 2026-06-20
**Status:** Approved (user, 2026-06-20)
**Goal:** Restructure the Polingo redesign roadmap so independent work runs **concurrently across plans** in isolated git worktrees, instead of one sequential backend lane. Maximise throughput to ship the schema fix and **start testing as soon as possible**.

---

## Why horizontal (and why not split Plan 2)

The naive "horizontal" reading — fan Plan 2 across several backend agents — does **not** work:

- Plan 2's migration chain is strictly linear: `0001_baseline → 0002 → 0003 → 0004 → 0005 → 0006`, each `down_revision` pinned to its predecessor. Revisions cannot be authored out of order.
- Tasks 2–6 all edit the **same files** (`models.py`, `llm.py`, `api/words.py`, plus the cutover touches `practice.py`, `endings.py`, `stats.py`, `utils.py`, `session.py`). Multiple agents on those files = merge thrash, not speedup.
- Task 6 is an atomic cutover that depends on every prior task.

So Plan 2 stays a **single sequential lane**. Parallelism comes from running **other plans concurrently** on disjoint file sets.

### Why the frontend agent can't "just do Plan 6 now"

Plan 6 (Frontend split) has two halves with different dependencies:

| Plan 6 part | Depends on | Parallelizable now? |
|---|---|---|
| Extract **API client** from `App.jsx` | current HTTP endpoints (held frozen) | ✅ yes |
| Extract **state layer** | nothing backend-internal | ✅ yes |
| **Per-Format components** | Plan 4 Exercise engine (defines which Formats exist + the exercise contract) | ❌ no — that contract is not designed yet |

The blocker for per-Format UI is **Plan 4**, not Plan 2's schema. The mechanical refactor (client + state extraction out of the 1340-line `App.jsx`) is independent and can run today against the frozen current contract. Plan 2's ripple into the frontend is tiny (see contract delta below).

---

## Execution model — 4 concurrent lanes

Each lane runs in its own git worktree on its own branch, owning a disjoint set of files.

| Lane | Agent type | Branch | Owns (files) | Scope |
|---|---|---|---|---|
| **L1 Backend A** *(critical path)* | backend | `plan-2-schema` | `backend-app/app/*.py`, `backend-app/migrations/`, `backend-app/requirements.txt` | Plan 2 schema unification — the existing 7-task plan, **unchanged internally** |
| **L2 Frontend** | frontend | `plan-6-fe-refactor` | `frontend-app/src/**` | Plan 6 **part 1 only**: extract API client + state layer from `App.jsx`. **No** per-Format components (need Plan 4). |
| **L3 QA / Testing** | QA | `test-contract-freeze` | `backend-app/tests/contract/`, frontend e2e dir | **Phase 0:** golden HTTP contract tests of *current* behavior (the safety net). Then e2e/integration. |
| **L4 Backend B** | backend2 | `plan-5-mcp` (and `plan-3-worker`) | new `mcp_server/`, new `worker/` | MCP server (talks to backend over **HTTP**, does not import changing models) + Plan 3 ARQ worker **scaffold/design** (integration deferred). |

**Dedup note:** characterization/contract-freeze tests live in the **L3** lane (Phase 0), not L4. L4 backend B does MCP + worker scaffold only.

**Paused:** promptfoo evals (Plan 7) are postponed — recorded as a `🚫/paused` row in `BACKLOG.md`, not a lane.

---

## Dependency DAG + gates

```
                    ┌─ Gate 0: contract-freeze tests (L3 Phase 0) ─┐
                    │  golden current HTTP responses → merge first │
                    └───────────────────┬──────────────────────────┘
                                        │ (safety net live on main)
          ┌─────────────────┬───────────┴───────────┬──────────────────┐
          ▼                 ▼                         ▼                  ▼
   L1 Plan 2 (crit)   L2 FE refactor          L4 MCP server      L4 worker scaffold
   schema/migrations  client+state extract    (HTTP client)      (new dir, deferred)
          │                 │                         │                  │
          └── merge 1st ────┤ rebase on Plan2 ────────┤ rebase ──────────┘
                            ▼
                  Plan 4 (exercise engine) ── unblocks ──> Plan 6 part 2 (per-Format UI)
```

- **Gate 0 — contract freeze.** L3 writes golden tests of the *current* HTTP behavior and merges them to `main` first. This is the safety net that lets every refactor proceed without silently changing the API. Highest "start testing ASAP" value.
- After Gate 0, **L1 / L2 / L4 run concurrently** on separate worktrees.
- **Plan 4** (exercise engine) is downstream of Plan 2 and is **not** a lane in this round; it unblocks Plan 6 part 2 later.

### Merge order (Plan 2 is central — merge before others rebase)

1. **L3 contract-freeze tests → `main`** (fast, first; establishes the net).
2. **L1 Plan 2 → `main`** (large, central; everyone rebases onto the post-merge schema).
3. **L2 frontend refactor → `main`** (rebase first; absorb the small contract delta).
4. **L4 MCP / worker → `main`** (rebase; isolated, low-conflict).

### Plan 2 → frontend contract delta (absorbed by L2 on rebase)

Small and well-bounded:
- Pronoun display gains `oni` / `one` (was the bundled `oni/one`).
- History record `id` is now the real `Attempt.id` (the old `+1_000_000` disambiguation hack is gone).

Nothing else in the HTTP contract changes shape.

---

## Worktree & isolation strategy

- Each lane agent runs with `isolation: worktree` so the four lanes operate on independent working copies and never collide on disk.
- A worktree that ends up unchanged is auto-cleaned.
- Branch-per-lane keeps history reviewable; integration follows the merge order above.

---

## Deliverables (produced by writing-plans next)

1. **Execution-map doc** — this lane table, DAG, merge order, and file-ownership manifest (the "horizontal" overlay over the plan series).
2. **Plan 2 header patch** — annotate the existing schema-unification plan as Lane 1 / critical path and declare its owned files. (The Plan 2 doc is currently untracked and is committed as part of this work so it is not lost.)
3. **New plan: contract-freeze tests** (L3 Phase 0).
4. **New plan: frontend refactor part 1** (L2) — API client + state layer extraction from `App.jsx`.
5. **New plan: MCP server** (L4) + **Plan 3 worker scaffold/design** (L4).

---

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| Plan 2 merges late → L2/L4 carry large rebases | Plan 2 is the critical path and merges 2nd; contract delta to FE is tiny (2 items). |
| L4 MCP imports changing models → breaks on Plan 2 merge | MCP talks to backend over **HTTP**, not by importing `app.models`. |
| Worker scaffold needs form-gen logic that Plan 2 edits | Worker is **scaffold/design only**; integration deferred until Plan 2 merges. |
| Two agents (L3 vs L4) both write characterization tests | Resolved: contract tests are **L3-only**. |
| Per-Format UI built against a non-existent contract | Explicitly out of scope; Plan 6 part 2 waits on Plan 4. |
