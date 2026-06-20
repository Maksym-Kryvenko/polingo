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
| `backend-app/tests/contract/**` (incl. its own `conftest.py`) | **L3** |
| `mcp_server/**` (new top-level dir) | **L4** |
| `worker/**` (new top-level dir) | **L4** |
| `.claude/BACKLOG.md`, `.claude/CONTEXT.md`, `README.md` | **doc-sync consolidation card (after all lanes merge)** — NOT any lane. See note below. |
| `docker-compose.yml` | **deferred** — redis+worker services land in the later Plan 3 wiring, out of scope this round. No lane edits it. |

**conftest conflict note:** L3 needs a seeded client (the root `fresh_db` is autouse + unseeded). To avoid editing the L1-touched root `conftest.py`, **L3 puts its fixtures in `backend-app/tests/contract/conftest.py`** (pytest merges nested conftests). No edit to the root conftest.

**doc-sync collision note (critic finding):** Plan 2's original Task 7 edited `.claude/CONTEXT.md` / `.claude/BACKLOG.md` / `README.md`. Those files are ALSO touched on the planning branch (this round's BACKLOG/BOARD/CONTEXT edits). To avoid a guaranteed three-way conflict, **doc-sync is removed from every lane and done once as a final consolidation card after all four lanes merge.** Plan 2's Task 7 is descoped to "leave a note for doc-sync" rather than editing the docs itself.

**seed consistency note (critic finding):** L3's contract tests run `seed_words` against whatever schema is current. After L1 merges, `app/seed.py` (L1-owned) must keep its data consistent with the new 5-gender enums, or seeding fails at collection. L1 owns this; L3 transitively depends on it post-rebase.

---

## Step 0 — bootstrap the planning branch (do this FIRST)

**Critical bootstrapping fix:** these plan docs, `BOARD.md`, and the updated `BACKLOG.md` currently live only on branch `plan-horizontal-execution`. Lane branches are cut from `main`. If you cut them before merging this branch, **the lane worktrees won't contain their own plan docs.** So:

1. Merge `plan-horizontal-execution` → `main` (docs/board/backlog only, no code).
2. Only THEN cut `test-contract-freeze`, `plan-2-schema`, `plan-6-fe-refactor`, `plan-5-mcp` from the updated `main`.

## Dependency DAG

```
   Step 0: merge planning branch (docs) → main ── then cut all lane branches
        │
   L3 contract tests ── merge 1st (baseline) ──┐
        │                                       │ (others rebase onto it)
        ├────────────────┬─────────────────────┼─────────────────┐
        ▼                ▼                       ▼                 ▼
   L1 Plan 2        L2 FE refactor         L4 MCP server     L4 worker scaffold
   (critical)       (client+state)         (HTTP client)     (new dir, deferred)
        │                │                       │                 │
        └── merge 2nd ───┤ rebase on Plan2 ─ 3rd ┤ rebase ─ merge 4th
                         ▼
               Plan 4 (later) ── unblocks ──> Plan 6 part 2 (per-Format UI)
   Final: doc-sync consolidation card (CONTEXT/BACKLOG/README) after all merge
```

**On "Gate 0" (corrected — critic finding):** L1/L2/L4 are **not blocked** from starting; they branch and run immediately. L3 merely **merges first** to establish a test baseline that the others rebase onto. This is a merge-ordering convention, not a hard execution gate.

**On the contract "safety net" (corrected — critic finding):** L3's tests build their schema from live model metadata, so after L1 merges they exercise the *new* code, not a frozen snapshot. They are therefore **shape-level regression coverage** (catch accidental key/status changes), **not** a frozen golden-value contract — by design they tolerate the gender/pronoun/id values Plan 2 changes. Do not over-claim them as proof the API "cannot change." A true value-freeze (committed golden response bodies captured against `main` pre-merge) is a possible hardening, deliberately out of scope this round.

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
