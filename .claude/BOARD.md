# Polingo Kanban Board

Lightweight task board for the horizontal execution round. One swimlane per lane/agent. Keep cards **small** (≈1 plan task each); split anything that grows. Move a card across columns by editing its status emoji.

**Columns:** 🟦 Ready · 🟨 In progress · 🟧 Review · ✅ Done · ⏸ Blocked
**Owner key:** A = Backend A (L1) · B = Backend B (L4) · F = Frontend (L2) · Q = QA (L3)

**Coordination rules**
- Cards respect the file-ownership manifest in `plans/2026-06-20-horizontal-execution-map.md`. No cross-lane file edits.
- **Step 0 first (S0 below):** merge the planning branch (docs/board) to `main`, THEN cut every lane branch from the updated `main` — else lane worktrees won't contain their own plan docs.
- Merge order is strict: **Q → A → F → B**, then the doc-sync card (DS).
- L3 merges first to establish a baseline; L1/L2/L4 are NOT blocked from starting (they branch and run immediately).
- `.claude/*` and `README.md` are edited ONLY by the final doc-sync card (DS), never by a lane.
- When you pick up a card: set 🟨 + add your agent id. When done locally: 🟧 (awaiting merge). After merge: ✅.

---

## S0 — Bootstrap (do before any lane branch is cut)

| ID | Card | Status | Dep |
|---|---|---|---|
| S0 | Merge `plan-horizontal-execution` (docs/BOARD/BACKLOG only) → `main`; then cut all four lane branches from updated `main` | 🟦 Ready | — |

## Lane Q — QA / Testing  (branch `test-contract-freeze`, merge 1st)

| ID | Card | Status | Dep |
|---|---|---|---|
| Q1 | Scaffold `tests/contract/` nested conftest + `seeded_client` (resolve `app`/`seed_words` imports); freeze `/healthz` | 🟦 Ready | — |
| Q2 | Freeze GET read contracts (words/initial, session, session/words/all, stats, stats/history, endings/config+stats, admin devices/settings/sentences) | 🟦 Ready | Q1 |
| Q3 | Freeze write contracts (practice submit/validate, choose-translation question, session language/add, words/check, admin setting update) | 🟦 Ready | Q1 |
| Q4 | Write `tests/contract/README.md` (un-frozen endpoints) + run full suite green | 🟦 Ready | Q2,Q3 |
| Q5 | **Merge to main (Gate 0)** | ⏸ Blocked | Q4 |

## Lane A — Backend A / Schema (branch `plan-2-schema`, merge 2nd) — CRITICAL PATH

| ID | Card | Status | Dep |
|---|---|---|---|
| A1 | Task 1: Alembic + baseline migration + `init_db` runs upgrade head (B3) | 🟦 Ready | — |
| A2 | Task 2: 5-gender model + `is_virile`/`is_animate_masculine`; remap legacy `męski` (B1 pt1) | 🟦 Ready | A1 |
| A3 | Task 3: split `Pronoun` oni/one; migration 0003 (B1 pt2) | 🟦 Ready | A2 |
| A4 | Task 4: nullable `Word.aspect` + migration 0004 (M4/M5 groundwork) | 🟦 Ready | A3 |
| A5 | Task 5: `Attempt` model + create-table migration 0005 (M3) | 🟦 Ready | A4 |
| A6 | Task 6: cutover — copy data, drop old tables, rewrite call sites (M3) | 🟦 Ready | A5 |
| A7 | Task 7 (DESCOPED): leave a note for doc-sync — do NOT edit `.claude/*`/`README.md` (DS owns them) | 🟦 Ready | A6 |
| A8 | **Merge to main** | ⏸ Blocked | A7, Q5 |

## Lane F — Frontend (branch `plan-6-fe-refactor`, merge 3rd)

| ID | Card | Status | Dep |
|---|---|---|---|
| F1 | Task 1: add Vitest + testing-library infra + smoke test | 🟦 Ready | — |
| F2 | Task 2: extract API base helper + session client (tested) | 🟦 Ready | F1 |
| F3 | Task 3: extract words/practice/endings/stats/admin clients + barrel (tested) | 🟦 Ready | F2 |
| F4 | Task 4: rewire App.jsx to API client (per-domain commits, build green) | 🟦 Ready | F3 |
| F5 | Task 5: extract `useSession` + `usePractice` hooks (tested) | 🟦 Ready | F4 |
| F6 | Task 6: `REFACTOR.md` + manual smoke | 🟦 Ready | F5 |
| F7 | Rebase on post-Plan-2 main; absorb oni/one + gender contract delta (no delta — frontend never referenced those enums) | ✅ Done | F6, A8 |
| F8 | **Merge to main** | ✅ Done | F7 |

## Lane B — Backend B / MCP + Worker (branch `plan-5-mcp`, merge 4th)

| ID | Card | Status | Dep |
|---|---|---|---|
| B1 | MCP Task 1: backend HTTP client w/ structured-error passthrough (tested) | 🟦 Ready | — |
| B2 | MCP Task 2: word-management tools over stdio (FastMCP) + README | 🟦 Ready | B1 |
| B3 | Worker Task 3a: `forms_status` state machine (tested) | 🟦 Ready | — |
| B4 | Worker Task 3b: ARQ task scaffold + injectable integration point (tested) | 🟦 Ready | B3 |
| B5 | Worker README documenting deferred backend wiring | 🟦 Ready | B4 |
| B6 | Rebase on post-Plan-2 main | ✅ Done | B2,B5, A8 |
| B7 | **Merge to main** | ✅ Done | B6 |

## DS — Doc-sync consolidation (after ALL lanes merge)

| ID | Card | Status | Dep |
|---|---|---|---|
| DS | Single editor of `.claude/CONTEXT.md` + `.claude/BACKLOG.md` + `README.md`: mark Attempt/virility/aspect live, Alembic migrations note, flip statuses, changelog | ✅ Done | A8,F8,B7,Q5 |

---

## Parking lot (later plans, not this round)
- Plan 4 exercise engine (unblocks Plan 6 part 2)
- Plan 6 part 2: per-Format components (useAddWords/usePronunciation/useEndings/useManage/useAdmin/useHistory hooks + components)
- Plan 3 worker→backend wiring (forms_status column migration, replace daemon threads, docker-compose redis+worker)
- Plan 7 promptfoo evals (⏸ paused)
- Masculine-personal/animate word re-tagging (Plan 2 lossy-remap follow-up)
