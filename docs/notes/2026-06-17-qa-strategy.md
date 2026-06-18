# QA & Test Strategy — Plans 2–4 + overall

> Research note produced by the Junior QA agent (haiku), 2026-06-17. Read-only analysis for lead review. This captures the agent's returned **summary** — the full per-case detail can be regenerated on request (the agent could not write files; SendMessage continuation was unavailable). Source: Plan 1 conftest pattern + `backend-app/app`.

## 1. Testing approach per plan
- **Plan 2 (unified Attempt):** unit-test stats/history aggregation against the new single table; integration-test the data migration (old `PracticeRecord`+`EndingsPracticeRecord` → `Attempt`) preserves counts. Extends Plan 1 `fresh_db`/`client` fixtures. No LLM.
- **Plan 3 (ARQ form-gen):** test enqueue + `forms_status` transitions; avoid real Redis via monkeypatch spy on the enqueue call (assert a job was scheduled), and test the worker function directly with a fake LLM. Test the durable sweep retries `failed`/stuck.
- **Plan 4 (exercise engine):** unit-test generation per (topic, format) and deterministic grading; integration-test the `/exercise` endpoint contract.

## 2. Deterministic vs LLM grading
- Deterministic path: seed a Word + canonical Form, assert grading compares to the stored Form (ref `practice.py:62-84`), accepts known variants, rejects wrong case forms.
- LLM fallback (`practice.py:87-117`): test via fake provider; **assert no auto-persist** to `WordOption` (locks in the M2 fix from Plan 1 Task 4).

## 3. Topic×Format validity matrix tests (ADR-0001)
- Test the matrix structure exists; test valid cells generate an exercise; test degenerate cells are rejected/skipped: `pronunciation×fill-blank`, `aspect×multiple-choice` (binary collapses distractors), `word-order×translate` (single `correct_answer` can't hold multiple orderings).

## 4. Regression tests for review findings
| Finding | Test that catches recurrence |
|---|---|
| B1 virility | model test: distinct storage for `oni`/`one` + virile gender axis |
| B2 accusative plural | `test_grammar_reference.py` asserts virility wording (Plan 1 Task 5) |
| B3 fail-loud migration | `test_database.py` migration raises on non-duplicate error |
| M2 auto-persist | `test_practice_grading.py` asserts no WordOption written (Plan 1 Task 4) |
| M5 future-aspect rule | grammar note asserts `*będę zrobić` invalidity once aspect field exists |
| M9 SQLite timeout | `test_database.py::test_file_url_sets_busy_timeout` (Plan 1 Task 2) |
| M10 nom-plural virility | `test_grammar_reference.py` nominative-plural label assertion |

## 5. promptfoo eval scope (Plan 7)
Gold-form eval cases for: resolve_word, generate_declensions, generate_verb_conjugations, generate_practice_sentences, translate-judge, pronunciation-judge. Example assertions: `kot` → genitive sg `kota`, instrumental sg `kotem`; `robić` → present `robię/robisz/robi`; judge accepts valid variant, rejects wrong case. Provider matrix OpenAI↔Claude (pairs with the pluggable text provider). CI-gated on prompt diffs.

## 6. Open questions for lead
1. Aspect modeling (field on Word vs separate). 2. Virility schema shape. 3. forms_status terminal states. 4. Exercise-gen concurrency. 5. Re-grading historical attempts after a grading change. 6. LLM model choice for evals. 7. Source of gold Polish test data.

> Lead note: Q1/Q2/Q3 are Plan 2 decisions; Q4 is Plan 3; Q5 affects the Attempt migration. Resolve in the respective plan grills.
