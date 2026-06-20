# Horizontal Execution Map

> **For orchestrators:** This is the coordination overlay for the Polingo redesign. It does NOT contain code. It declares the concurrent lanes, their file ownership, the dependency gates, and the merge order. Each lane has its own implementation plan (linked below). Dispatch lanes via worktree-isolated subagents per the rules here.

**Source spec:** `docs/superpowers/specs/2026-06-20-horizontal-execution-model-design.md`

**Goal:** Ship the schema fix (Plan 2) on the critical path while frontend refactor, contract-freeze testing, and an isolated MCP/worker track run concurrently — without merge conflicts.

---

## Lanes

| Lane | Branch | Plan doc | Agent type |
|---|---|---|---|
| **L1 Backend A** *(critical path)* | `plan-2-schema` | `2026-06-18-polingo-schema-unification.md` | backend |
| **L2 Frontend** | `plan-6-fe-refactor` | `2026-06-20-l2-frontend-refactor.md` | frontend |
| **L3 QA / Testing** | `test-contract-freeze` | `2026-06-20-l3-contract-freeze-tests.md` | QA |
| **L4 Backend B** | `plan-5-mcp` | `2026-06-20-l4-mcp-and-worker-scaffold.md` | backend2 |

---

## File-ownership manifest (disjoint by construction)

A lane MUST only modify files in its own row. Overlap = conflict; route the change through the owning lane.

| Path | Owner |
|---|---|
| `backend-app/app/**` (all `.py`) | **L1** |
| `backend-app/migrations/**` | **L1** |
| `backend-app/requirements.txt` | **L1** (L4 adds worker deps via a *separate* `mcp_server/requirements.txt` / `worker/requirements.txt`, not this file) |
| `frontend-app/src/**` | **L2** |
| `frontend-app/package.json`, `vite.config.js` | **L2** |
| `backend-app/tests/contract/**` | **L3** |
| `backend-app/tests/conftest.py` | **L3** *(append-only: add fixtures, never edit L1-owned assertions)* — see conflict note below |
| `mcp_server/**` (new top-level dir) | **L4** |
| `worker/**` (new top-level dir) | **L4** |
| `.claude/BACKLOG.md`, `.claude/CONTEXT.md` | whoever merges last per their plan's doc task (L1 owns the Plan 2 doc updates) |

**conftest conflict note:** L3 needs a non-autouse `seeded_client` fixture (the current `fresh_db` is autouse + unseeded). To avoid editing the L1-touched `conftest.py`, **L3 puts its fixtures in `backend-app/tests/contract/conftest.py`** (pytest merges nested conftests). No edit to the root conftest. This is enforced in the L3 plan.

---

## Dependency DAG

```
            ┌─ Gate 0: L3 contract-freeze tests (golden current HTTP) ─┐
            │                merge to main FIRST                        │
            └───────────────────────────┬──────────────────────────────┘
                                         │ safety net live
        ┌────────────────┬───────────────┴────────────┬─────────────────┐
        ▼                ▼                              ▼                 ▼
   L1 Plan 2        L2 FE refactor                L4 MCP server     L4 worker scaffold
   (critical)       (client+state)                (HTTP client)     (new dir, deferred)
        │                │                              │                 │
        └── merge 2nd ───┤ rebase on Plan2 ─ merge 3rd ─┤ rebase ─ merge 4th
                         ▼
               Plan 4 (later) ── unblocks ──> Plan 6 part 2 (per-Format UI)
```

**Gate 0 is a hard gate.** L1/L2/L4 may *start* in parallel immediately (they branch from current `main`), but L3's contract tests should land first so any accidental contract drift in L1/L2 is caught on rebase.

---

## Merge order (strict)

1. **L3 → main** — contract-freeze tests. Fast. Establishes the net.
2. **L1 → main** — Plan 2 schema. Central; everyone rebases onto it.
3. **L2 → main** — frontend refactor. Rebase first, absorb the contract delta (below).
4. **L4 → main** — MCP + worker. Rebase; isolated, trivial.

After each merge, the next lane rebases its branch on updated `main` before its own merge.

---

## Plan 2 → consumer contract delta

The only HTTP-contract changes Plan 2 introduces that consumers must absorb on rebase:

- **Pronoun values:** `oni/one` (bundled) → split `oni` + `one`. Surfaces in `/api/endings/question` `pronoun` field and `/api/admin/sentences` `pronoun` field. L2 render points: `App.jsx:988`, `App.jsx:1243` (now in extracted components).
- **History `id`:** `/api/stats/history` records carry the real `Attempt.id` (the old `+1_000_000` disambiguation hack is gone). Field name unchanged (`id`); only the value space changes → **no frontend code change needed**, but L3 golden tests for `/api/stats/history` must not assert specific id *values*.
- **Gender values:** `męski` → 5-gender set. Surfaces in `WordRead.gender`, `WordWithStats.gender`, `EndingsQuestion.gender`. L3 golden tests must not pin `gender == "męski"`.

L3's contract tests MUST be written to tolerate these (assert *shape*, not the volatile values above). This is specified in the L3 plan.

---

## Worktree dispatch rules

- Each lane subagent runs with `isolation: worktree` so the four working copies never collide on disk.
- A lane that finishes and is merged has its worktree auto-cleaned.
- Orchestrator dispatches L1, L2, L4 concurrently after L3 Gate 0 is in flight; reviews each lane's output against its plan before merging in the strict order above.

---

## Paused / out of scope this round

- **Plan 7 promptfoo evals** — postponed (BACKLOG row `⏸ paused`).
- **Plan 4 exercise engine** — downstream of Plan 2; not a lane this round.
- **Plan 6 part 2** (per-Format components) — blocked on Plan 4.
- **L4 worker integration** — scaffold/design only; wiring into `words.py` happens in a later plan after Plan 2 merges (the form-gen code lives in L1-owned files).
