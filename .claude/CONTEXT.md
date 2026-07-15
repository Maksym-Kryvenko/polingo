# Polingo — Domain Glossary

Single-user, self-hosted Polish vocabulary & grammar trainer. This file is a glossary only — no implementation detail.

Each term is tagged **[live]** (exists in code today) or **[planned]** (target of the redesign — see `docs/adr/`). The distinction matters: several practice-model terms below do not yet have backing data or tables.

## Project documentation map

Start here. All design/decision/plan documents and what each is for. **Paths are relative to the repo root** (this file lives in `.claude/`; the `docs/` tree is at the repo root).

| Document | What it is | Read it when |
|---|---|---|
| `.claude/CONTEXT.md` (this file) | Domain glossary — canonical names for every concept, tagged live vs planned. | Always first. To learn what a term *means* before touching code. |
| `.claude/BACKLOG.md` | Living tracker: plan-series progress, every review finding with status (done/planned/open/rejected), and a dated changelog. | To see what's decided, in flight, done, or deliberately rejected. Update it when you finish work. |
| `.claude/BOARD.md` | **Kanban board** for the horizontal execution round: small per-lane/per-agent cards with status (Ready/In progress/Review/Done/Blocked), dependencies, and merge order. | When picking up or tracking concrete agent tasks. Move a card's status when you start/finish. |
| `README.md` | User-facing overview, feature list, install/run/Docker instructions, API surface summary. | To run the app or understand existing features end-to-end. |
| `docs/adr/0001-two-axis-exercise-model.md` | **ADR (proposed):** practice modelled as orthogonal **Topic × Format**; why, rejected alternatives, the validity-matrix consequence. | Before designing/altering how exercises are generated, catalogued, or graded. |
| `docs/adr/0002-mcp-standalone-over-rest.md` | **ADR (proposed):** Claude Code integration as a standalone FastMCP stdio process wrapping the REST API; unreachable-backend behaviour to define. | Before building or wiring the MCP server. |
| `docs/adr/0003-arq-redis-task-queue.md` | **ADR (proposed):** form generation moves from daemon threads to ARQ+Redis with a `forms_status`; retry/dead-letter policy to define. | Before touching background form generation or adding the queue/worker. |
| `docs/superpowers/plans/2026-06-17-polingo-foundation.md` | **Plan 1 of 7 (✅ merged):** foundation + correctness fixes — env config, pytest harness, fail-loud migration, model-ids→config, fixes M2/M9/B2/M10. TDD, bite-sized steps. | Reference for the test harness, config seam, and TDD pattern later plans build on. |
| `docs/superpowers/specs/2026-06-20-horizontal-execution-model-design.md` | **Design spec:** why the redesign runs as 4 concurrent lanes, lane table, dependency DAG, merge order, and the Plan-2→consumer contract delta. | Before dispatching lanes or to understand why work is parallelised this way. |
| `docs/superpowers/plans/2026-06-20-horizontal-execution-map.md` | **Execution map (orchestration overlay):** file-ownership manifest, Step-0 bootstrap, merge order, gate semantics. No code. | When orchestrating the lanes or resolving who-owns-which-file. |
| `docs/superpowers/plans/2026-06-18-polingo-schema-unification.md` | **Plan 2 — Lane L1 (critical path):** Alembic, 5-gender virility model (B1), nullable `aspect`, unified `Attempt` table (M3), lossless data migration. | When implementing the schema unification (branch `plan-2-schema`). |
| `docs/superpowers/plans/2026-06-20-l3-contract-freeze-tests.md` | **Lane L3 (Gate 0):** golden characterization tests of the current HTTP contract, in `backend-app/tests/contract/`. | First — establishes the test baseline (branch `test-contract-freeze`). |
| `docs/superpowers/plans/2026-06-20-l2-frontend-refactor.md` | **Plan 6 part 1 — Lane L2:** extract API client + state hooks from `App.jsx` (Vitest), behaviour-preserving. | When refactoring the frontend (branch `plan-6-fe-refactor`). |
| `docs/superpowers/plans/2026-06-20-l4-mcp-and-worker-scaffold.md` | **Plan 5 + Plan 3 scaffold — Lane L4:** FastMCP stdio server (HTTP-isolated) + ARQ worker scaffold with `forms_status`. | When building the MCP server or the form-gen worker scaffold (branch `plan-5-mcp`). |
| `docs/notes/2026-06-17-frontend-plan6-analysis.md` | **Research note:** App.jsx inventory, proposed Plan 6 component split + Exercise contract, and how Plans 2–4 ripple into the UI/API. | Before writing Plan 6 part 2, or when changing the API contract the UI consumes. |
| `docs/notes/2026-06-17-qa-strategy.md` | **Research note:** test/QA strategy for Plans 2–4, deterministic-vs-LLM grading tests, validity-matrix tests, regression map for findings, promptfoo scope. | Before writing Plan 4 or 7; to design tests. |

**Plan series:** 1 Foundation ✅ merged → **2 Schema unification (L1) ✅ merged** · **3 Form-gen (L4 scaffold) ✅ merged** · **5 MCP server (L4) ✅ merged** · **6 Frontend split part 1 (L2) ✅ merged** · contract-freeze tests (L3) ✅ merged → 4 Exercise engine (Topic×Format, not written) → 6 part 2 per-Format UI (blocked on 4) → 7 promptfoo (⏸ paused). The horizontal execution round is **complete** — all four lanes (Q→A→F→B) merged to `main` in order; see `.claude/BOARD.md`. The DB now uses **Alembic** migrations (`backend-app/migrations/versions/0001–0006`); `init_db` runs `upgrade head`. New plans live under `docs/superpowers/plans/` named `YYYY-MM-DD-<feature>.md` — **add a row above when you create one.**

> **Conventions for agents:** ADRs are *decision records* (the why, hard-to-reverse); plans are *step-by-step build instructions* (the how). ADRs marked `Status: proposed` describe the target, not current code — verify against the codebase before assuming a feature exists. When a decision changes, update the ADR's `Status` (e.g. `accepted`/`superseded`) rather than deleting it.

## Core terms

- **Word** *[live]* — a Polish lexical entry with translations (English, Ukrainian), a part of speech, and (for nouns) a gender. The unit a learner adds to their deck.
- **Form** *[live]* — an inflected realisation of a Word. Currently **polymorphic across two tables**: a *declension* (noun/adjective in case×gender×number, `WordDeclension`) or a *conjugation* (verb in tense×pronoun, `VerbConjugation`). There is no single `Form` table; the term is an umbrella over both. *[live]* the virility (męskoosobowy / niemęskoosobowy) axis now exists: the 5-gender model with `is_virile`/`is_animate_masculine`, and the `Pronoun` enum splits `oni`/`one` for virile vs non-virile past-tense storage (Plan 2, migrations 0002/0003).
- **Deck** *[live]* — the set of Words a learner has chosen to study. Backed by `UserSession` + `UserSessionWord`; there is exactly **one** session for the single user, so "Deck" and "the session word list" are the same thing. Words in a Deck can be enabled or disabled.

## Practice model

- **Topic** *[partly planned]* — the grammar skill being trained, independent of how it's tested.
  - *[live]* declension/cases, conjugation/tenses (present/past/future).
  - *[partly live]* aspect (perfective vs imperfective) — the nullable `Word.aspect` field now exists (Plan 2, migration 0004), though aspect-Topic exercises are not yet generated. agreement (gender + number + virility) — the virility axis now exists (see "Form" above). government (preposition→case, negation→genitive) *[planned, no backing data yet]* — still needs a curated rule table.
- **Format** *[partly planned]* — how an exercise is prompted and answered, independent of Topic.
  - *[live]* multiple-choice, fill-blank, translate, write-to-Polish, speak (`pronunciation`).
  - *[planned]* listen (audio→type), word-order, multi-blank cloze, matching. "speak"/"listen" depend on ASR/TTS wiring.
- **Exercise** *[planned, ephemeral]* — one concrete question, identified by a (Topic, Format) pair plus the target Word/Form. A runtime concept, not necessarily a stored entity. Topic and Format are orthogonal, but **not every pair is valid** — see ADR-0001's validity matrix.
- **Attempt** *[live]* — one learner answer to one Exercise: what they answered, the correct answer, whether it was right, and the grammatical context. Now the **single source of truth** for stats and history: the unified `Attempt` table (with `AttemptKind`) landed in Plan 2 (migrations 0005 create, 0006 data cutover + drop). The old `PracticeRecord`/`EndingsPracticeRecord` tables have been dropped; all write sites and stats/history queries read from `Attempt`.

## Roles & surfaces

- **Learner** *[live]* — the human practising (the single user).
- **Language set** *[live]* — the learner's chosen translation pairing for a session: Polish↔English or Polish↔Ukrainian. A session-level switch affecting prompts and grading.
- **MCP client** *[live, standalone]* — Claude Code (or another MCP host) acting on the Learner's behalf to add/curate Words via the MCP server. A standalone FastMCP stdio process (`mcp_server/`) wrapping the REST API via an HTTP client with structured-error passthrough (Plan 5). Not yet wired into the app's own runtime.
- **Admin / device tracking** *[live]* — the app records connected devices (`ConnectedDevice`) and exposes admin settings. Present despite the single-user framing; used for visibility/debugging, not multi-user isolation.
