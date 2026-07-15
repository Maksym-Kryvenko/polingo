# Polingo Backlog

Single tracker for the redesign: what's decided, what's in flight, what's done. Pairs with `.claude/CONTEXT.md` (glossary), `docs/adr/` (decisions), and `docs/superpowers/plans/` (build steps). Paths are relative to the repo root.

**Status legend:** ✅ done · 🔜 planned (queued in a plan) · 🔲 open (no plan yet) · 🚫 rejected

**How to use:** when you finish a task, flip its status and add a dated line to the Changelog. When you write a new plan, update the Plan series table. When a finding is fixed, mark it ✅ and cite the commit/plan.

---

## Plan series

| Plan | Scope | Status |
|---|---|---|
| 1 — Foundation & Correctness | env config, pytest harness, fail-loud migration, model-ids→config, fixes M2/M9/B2/M10 | ✅ **complete** — merged to `main` (PR #1, `0de2958`); all 6 tasks, 16 tests green |
| 2 — Schema unification | Alembic, virility model (B1), unified `Attempt` table, data migration | ✅ **complete** — merged to `main` (`b951adc`). Alembic 0001–0006, 5-gender virility, nullable `aspect`, unified `Attempt` (old record tables dropped) |
| 3 — Reliable form-gen | ARQ+Redis worker, `forms_status`, durable retries (ADR-0003) | ✅ **scaffold complete** — merged to `main` (`5696b8a`). `worker/` has `forms_status` state machine + ARQ task scaffold; backend runtime wiring still deferred (see parking lot) |
| 4 — Exercise engine | Topic×Format generation + deterministic grading + validity matrix (ADR-0001) | 🔲 not written (unblocks Plan 6 part 2) |
| 5 — MCP server | FastMCP stdio, add/manage/stats tools (ADR-0002) | ✅ **complete** — merged to `main` (`5696b8a`). `mcp_server/` standalone FastMCP stdio: backend HTTP client + word-management tools |
| 6 — Frontend split | API client, state layer, per-Format components | ✅ **part 1 complete** — merged to `main` (`1c4997a`). Per-domain API clients + `useSession`/`usePractice` hooks + Vitest. Part 2 (per-Format components) blocked on Plan 4 |
| 7 — promptfoo evals | gold-form configs, OpenAI↔Claude matrix, CI gate | ⏸ **paused** — postponed; not in the current parallel round |

### Horizontal execution (2026-06-20)

The redesign ran as **4 concurrent lanes** instead of one sequential backend track. See `plans/2026-06-20-horizontal-execution-map.md` (DAG, file-ownership, merge order) and the design `specs/2026-06-20-horizontal-execution-model-design.md`. Task board: `.claude/BOARD.md`. **Round complete — all lanes merged to `main` in order (2026-07-15).**

| Lane | Branch | Plan | Merge order | Status |
|---|---|---|---|---|
| L3 QA/Testing | `test-contract-freeze` | contract-freeze tests | **1st (Gate 0)** | ✅ merged (`498d697`) |
| L1 Backend A (critical) | `plan-2-schema` | Plan 2 | 2nd | ✅ merged (`b951adc`) |
| L2 Frontend | `plan-6-fe-refactor` | Plan 6 part 1 | 3rd | ✅ merged (`1c4997a`) |
| L4 Backend B | `plan-5-mcp` | Plan 5 + Plan 3 scaffold | 4th | ✅ merged (`5696b8a`) |

---

## Review findings (from the 3-critic + Opus consolidation, 2026-06-17)

### Blockers
| ID | Finding | Status | Handled by |
|---|---|---|---|
| B1 | Gender model lacks virility (męskoosobowy); `Pronoun.oni_one` bundled → can't store `oni robili`/`one robiły` | ✅ | Plan 2 (5-gender + `oni`/`one` split, migrations 0002/0003, `b951adc`) |
| B2 | `grammar.py` masculine accusative-**plural** uses singular animacy rule (wrong form taught) | ✅ | Plan 1 · Task 5 |
| B3 | `database.py` migration swallows all errors; `create_all` can't alter tables | ✅ | Plan 1 · Task 2 (fail-loud) + Plan 2 (Alembic, `init_db` runs `upgrade head`, `b951adc`) |

### Majors
| ID | Finding | Status | Handled by |
|---|---|---|---|
| M1 | ADRs missing Status/Date/Consequences; ADR-0001 fails hard-to-reverse test | ✅ | Doc fix 2026-06-17 |
| M2 | LLM-approved wrong answers auto-persisted as canonical `WordOption` (correctness ratchet) | 🔜 | Plan 1 · Task 4 |
| M3 | CONTEXT "Attempt = single source of truth" false (two disjoint record tables) | ✅ | Plan 2 unified `Attempt` table; old record tables dropped (migrations 0005/0006, `b951adc`) |
| M4 | aspect/government Topics listed but have no backing data | ✅ aspect field / 🔜 government data | Plan 2 nullable `Word.aspect` (migration 0004) landed; government rule table still Plan 4 |
| M5 | Future tense omits aspect-controls-form hard rule (`*będę zrobić`) | 🔜 | `aspect` field now exists (Plan 2); grammar rule use deferred to Plan 4 |
| M6 | Degenerate Topic×Format cells break "common contract" claim | ✅ ADR / 🔜 impl | ADR-0001 validity matrix + Plan 4 |
| M7 | MCP backend-unreachable behaviour undefined | ✅ | ADR-0002 + Plan 5 MCP HTTP client with structured-error passthrough (`5696b8a`) |
| M8 | ARQ retry/dead-letter/stuck policy undefined | ✅ scaffold / 🔜 runtime | ADR-0003 + Plan 3 `forms_status` state machine + ARQ scaffold (`5696b8a`); backend wiring deferred |
| M9 | SQLite engine has no busy timeout → "database is locked" risk | ✅ | Plan 1 · Task 2 (`timeout: 30`) |
| M10 | Nominative-plural virile `-i/-y` alternation unlabelled | ✅ | Plan 1 · Task 5 |

### Minors
| ID | Finding | Status | Handled by |
|---|---|---|---|
| m1 | Deck vs Session conflation | ✅ | Doc fix (clarified: one session = the Deck) |
| m2 | `Form` is umbrella over two tables, not one entity | ✅ | Doc fix (marked polymorphic) |
| m3 | `Exercise` term has no stored entity | ✅ | Doc fix (marked ephemeral/runtime) |
| m4 | speak/listen imply audio infra not fully present | ✅ | Doc fix (marked planned) |
| m5 | Conditional & imperative moods absent from `VerbTense` | 🔲 | Future plan (conjugation breadth) |
| m6 | Multi-government prepositions (na/w/za/po) unstructured | 🔲 | Plan 4 (government data) |
| m7 | ADR-0003 Huey contradiction / swap-ease vs hard-to-reverse | ✅ | Doc fix |
| m8 | ADR-0002 "reachable port" rationale bogus | ✅ | Doc fix (rewrote to process-isolation) |
| m9 | `ConnectedDevice` tracking undocumented for single-user app | ✅ | Doc fix (Admin term added) |
| m10 | LanguageSet practice-mode switch not in glossary | ✅ | Doc fix (term added) |
| m11 | ADR-0001 O(N×M) honesty | ✅ | Doc fix (Consequences) |
| m12 | agreement Topic too narrow | ✅ | Doc fix (broadened) |

### Rejected (consolidator's adversarial pass — recorded so they don't resurface)
| Finding | Why rejected |
|---|---|
| celownik-nijaki "blocker" | Neuter dative `-u` / biernik=mianownik are correct; critic self-downgraded |
| wołacz feminine `-u` "misleads" | `-o` already listed first; reference table, not a ranking |
| past-tense pronoun-key "silent failure" | Real data inconsistency but no code path hits it → latent, fold into B1 |
| doc/code gap = 3 separate blockers | One cross-cutting framing issue, solved by `Status` field |
| "Word gender should mention adjectives" | Adjective gender determined by head noun at exercise time |

---

## Changelog

### 2026-07-15
- **Horizontal execution round complete** — all four lanes merged to `main` in strict order: L3 QA contract-freeze (Gate 0, `498d697`) → L1 Plan 2 schema unification (`b951adc`) → L2 Plan 6 part-1 frontend refactor (`1c4997a`) → L4 Plans 5+3 MCP/worker scaffold (`5696b8a`).
- **Plan 2 (schema):** adopted Alembic (migrations 0001–0006, `init_db` runs `upgrade head`); 5-gender virility model with `is_virile`/`is_animate_masculine` and `oni`/`one` pronoun split; nullable `Word.aspect`; unified `Attempt` table now the single source of truth — old `PracticeRecord`/`EndingsPracticeRecord` tables dropped, all call sites + stats/history rewritten. Closes **B1, B3, M3, M4 (aspect), M10**.
- **Plan 5 (MCP):** standalone `mcp_server/` FastMCP stdio process — backend HTTP client with structured-error passthrough + word-management tools. Closes **M7**.
- **Plan 3 (worker scaffold):** `worker/` `forms_status` state machine + ARQ task scaffold (backend runtime wiring deferred). Addresses **M8** (scaffold).
- **Plan 6 part 1 (frontend):** extracted per-domain API clients (session/words/practice/endings/stats/admin) + `useSession`/`usePractice` hooks from `App.jsx`; added Vitest infra (24 tests green). No pronoun/gender contract delta — frontend never referenced those enums.
- Added GitHub Actions CI (`.github/workflows/ci.yml`): backend pytest + frontend build. Doc-sync (DS): flipped statuses in CONTEXT.md/BACKLOG.md/BOARD.md/README.md.

### 2026-06-18
- Set up 3 junior agents (haiku): backend / frontend / QA. Backend agent blocked on Bash permission in background mode → lead took over Plan 1 execution.
- Plan 1 partially executed on branch `plan-1-foundation`: Task 1 (pytest + config seam), Task 2 (config-driven engine, test harness, fail-loud migration **B3**, SQLite **M9**), Task 3 (model-ids→config). 11 tests green. Tasks 4–6 (M2, B2/M10, README) pending.
- Saved research notes: `docs/notes/2026-06-17-frontend-plan6-analysis.md`, `docs/notes/2026-06-17-qa-strategy.md`.
- Paused.

### 2026-06-17
- Grill session: locked 17 redesign decisions (single-user, unified Attempt, Topic×Format, +topics agreement/aspect/government, +formats listen/word-order/cloze/matching, MCP stdio-over-REST, ARQ+Redis, deterministic-first grading, pytest+promptfoo, full frontend split, Alembic).
- Created `CONTEXT.md` glossary + ADR-0001/0002/0003.
- Ran 3-critic + Opus consolidation workflow over the docs (49 raw findings → prioritised, 5 rejected).
- Doc fixes: ADRs stamped `Status: proposed` + Date + Considered Options + Consequences; fixed m7/m8 rationales, M6/m11 validity-matrix/honesty; CONTEXT terms tagged live/planned, fixed M3/M4 overclaims + m1/m2/m3/m4/m9/m10/m12.
- Wrote Plan 1 (Foundation & Correctness).
- Added `CONTEXT.md` documentation map + this backlog.
