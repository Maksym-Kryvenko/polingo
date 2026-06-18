# Polingo Backlog

Single tracker for the redesign: what's decided, what's in flight, what's done. Pairs with `CONTEXT.md` (glossary), `docs/adr/` (decisions), and `docs/superpowers/plans/` (build steps).

**Status legend:** ✅ done · 🔜 planned (queued in a plan) · 🔲 open (no plan yet) · 🚫 rejected

**How to use:** when you finish a task, flip its status and add a dated line to the Changelog. When you write a new plan, update the Plan series table. When a finding is fixed, mark it ✅ and cite the commit/plan.

---

## Plan series

| Plan | Scope | Status |
|---|---|---|
| 1 — Foundation & Correctness | env config, pytest harness, fail-loud migration, model-ids→config, fixes M2/M9/B2/M10 | 🔜 **in progress** on branch `plan-1-foundation` — Tasks 1–3 done (config, harness, model-ids→config; 11 tests green); Tasks 4–6 pending (M2 fix, B2/M10 grammar, README) |
| 2 — Schema unification | Alembic, virility model (B1), unified `Attempt` table, data migration | 🔲 not written |
| 3 — Reliable form-gen | ARQ+Redis worker, `forms_status`, durable retries (ADR-0003) | 🔲 not written |
| 4 — Exercise engine | Topic×Format generation + deterministic grading + validity matrix (ADR-0001) | 🔲 not written |
| 5 — MCP server | FastMCP stdio, add/manage/stats tools (ADR-0002) | 🔲 not written |
| 6 — Frontend split | API client, state layer, per-Format components | 🔲 not written |
| 7 — promptfoo evals | gold-form configs, OpenAI↔Claude matrix, CI gate | 🔲 not written |

---

## Review findings (from the 3-critic + Opus consolidation, 2026-06-17)

### Blockers
| ID | Finding | Status | Handled by |
|---|---|---|---|
| B1 | Gender model lacks virility (męskoosobowy); `Pronoun.oni_one` bundled → can't store `oni robili`/`one robiły` | 🔜 | Plan 2 (schema + Alembic) |
| B2 | `grammar.py` masculine accusative-**plural** uses singular animacy rule (wrong form taught) | 🔜 | Plan 1 · Task 5 |
| B3 | `database.py` migration swallows all errors; `create_all` can't alter tables | ✅ fail-loud done (branch) · 🔜 Alembic | Plan 1 · Task 2 ✅ + Plan 2 (Alembic) |

### Majors
| ID | Finding | Status | Handled by |
|---|---|---|---|
| M1 | ADRs missing Status/Date/Consequences; ADR-0001 fails hard-to-reverse test | ✅ | Doc fix 2026-06-17 |
| M2 | LLM-approved wrong answers auto-persisted as canonical `WordOption` (correctness ratchet) | 🔜 | Plan 1 · Task 4 |
| M3 | CONTEXT "Attempt = single source of truth" false (two disjoint record tables) | ✅ glossary / 🔜 structural | Doc fix (clarified) + Plan 2 (unify) |
| M4 | aspect/government Topics listed but have no backing data | ✅ annotated / 🔜 data | Doc fix (marked planned) + Plan 2 (aspect field) + Plan 4 |
| M5 | Future tense omits aspect-controls-form hard rule (`*będę zrobić`) | 🔲 | Plan 2 (aspect field) + grammar note |
| M6 | Degenerate Topic×Format cells break "common contract" claim | ✅ ADR / 🔜 impl | ADR-0001 validity matrix + Plan 4 |
| M7 | MCP backend-unreachable behaviour undefined | ✅ ADR / 🔜 impl | ADR-0002 Consequences + Plan 5 |
| M8 | ARQ retry/dead-letter/stuck policy undefined | ✅ ADR / 🔜 impl | ADR-0003 Consequences + Plan 3 |
| M9 | SQLite engine has no busy timeout → "database is locked" risk | ✅ done (branch) | Plan 1 · Task 2 (`timeout: 30`) |
| M10 | Nominative-plural virile `-i/-y` alternation unlabelled | 🔜 | Plan 1 · Task 5 |

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
