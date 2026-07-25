# Stopniowanie przymiotników (Adjective Grading) — Design

**Date:** 2026-07-25
**Status:** Approved (pre-implementation)

## Goal

Add a new practice section teaching Polish adjective grading (stopniowanie) across
three types:

- **proste** — regular synthetic grading (`ładny → ładniejszy → najładniejszy`)
- **nieregularne** — irregular grading (`dobry → lepszy → najlepszy`)
- **opisowe** — descriptive/analytic grading (`znany → bardziej znany → najbardziej znany`)

Exposed as its **own main-menu section** (a new nav card on Home), parallel to the
existing "Endings" (Odmiana) section. Interaction mirrors Endings: choose (multiple
choice) and write modes, validate, stats.

## Scope decisions

- **Nominative base forms only.** Store/ask the base (masculine nominative singular)
  comparative and superlative. Comparatives *do* inflect by case/gender in Polish, but
  that is explicitly **out of scope** for v1 — this section drills "which is the
  comparative/superlative form", not full declension of the graded form.
- **Distractors LLM-generated and cached.** Wrong multiple-choice options are generated
  once via `llm.py` and persisted on the grading row for reuse (same reuse pattern as
  `PracticeSentence`). No per-request LLM cost after first generation.
- **Frontend added inline** in `App.jsx` (cloning the Endings view). The larger
  page-extraction refactor flagged in review is tracked as a **separate backlog item**,
  not a blocker for this feature.

## Data model

New table `AdjectiveGrading` (one row per adjective `Word`):

| column | type | notes |
|---|---|---|
| `id` | int PK | |
| `word_id` | int FK → `Word.id` | the adjective; positive form = `word.polish` |
| `grading_type` | enum `GradingType` | `proste` \| `nieregularne` \| `opisowe` |
| `comparative` | str | nominative base, e.g. `lepszy`, `ładniejszy`, `bardziej znany` |
| `superlative` | str | nominative base, e.g. `najlepszy`, `najładniejszy`, `najbardziej znany` |
| `comparative_distractors` | str, nullable | JSON list of cached wrong options (lazy) |
| `superlative_distractors` | str, nullable | JSON list of cached wrong options (lazy) |

- **One row per `word_id`** (unique). `grading_type` classifies the adjective and doubles
  as the practice filter.
- New enum `GradingType(str, Enum)` in `models.py`.
- **Alembic migration `0007_adjective_grading.py`** creates the table. (Adding
  `AttemptKind.grading` is a Python-only enum change and needs **no** migration — the
  `Attempt.kind` column already stores arbitrary strings.)

## Seed

Extend `seed.py` with hardcoded lists per type, each linked to a seeded adjective `Word`:

- **nieregularne** (~10 triples): dobry/lepszy/najlepszy, zły/gorszy/najgorszy,
  duży/większy/największy, mały/mniejszy/najmniejszy, wysoki/wyższy/najwyższy,
  niski/niższy/najniższy, lekki/lżejszy/najlżejszy, ciężki/cięższy/najcięższy,
  daleki/dalszy/najdalszy, bliski/bliższy/najbliższy.
- **proste** (~15 regular): ładny, tani, ciekawy, zimny, ciepły, młody, stary, nowy,
  szybki, wolny, silny, słaby, mądry, głupi, gruby — each with its `-szy/-ejszy` +
  `naj-` forms hardcoded in the seed (no runtime derivation).
- **opisowe** (~8): known/abstract adjectives that grade analytically —
  znany→bardziej znany, chory→bardziej chory, zmęczony, zajęty, popularny, nerwowy,
  kolorowy, interesujący.

Distractor columns start `NULL` and are filled lazily on first question.

## Grammar reference

- Add `ADJECTIVE_GRADING_RULES` block in `grammar.py`: for each `grading_type`, a
  formation rule string + examples (and for `nieregularne`, the memorization list).
- Extend `get_grammar_reference(part_of_speech, case=None, tense=None, grading_type=None)`:
  when `part_of_speech == "przymiotnik"` and `grading_type` is set, return
  `{"grading_rules": ADJECTIVE_GRADING_RULES[grading_type]}`.

## Backend API — `app/api/grading.py` (prefix `/grading`)

Mirrors `app/api/endings.py`. New schemas in `schemas.py`: `GradingConfigResponse`,
`GradingQuestion`, `GradingValidationRequest`, `GradingValidationResponse`,
`GradingStatsResponse` (stats shape identical to `EndingsStatsResponse`).

- `GET /grading/config` → `{ grading_types: [...], counts: {type: n} }` (counts of seeded
  adjectives per type).
- `GET /grading/question?grading_types=proste,nieregularne&exclude_word_id=`
  1. Pick a random `AdjectiveGrading` row whose `grading_type` ∈ requested set
     (fallback: all), avoiding `exclude_word_id`.
  2. Randomly pick **degree** = comparative | superlative → `correct_answer`.
  3. **Choose mode:** if the matching `*_distractors` column is populated, use it;
     else call `llm.py` to generate 3 wrong forms, persist to the column, reuse.
     Options = `[correct] + distractors`, shuffled.
  4. Attach `grammar_reference = get_grammar_reference("przymiotnik",
     grading_type=row.grading_type)`.
  5. Response includes: `word_id, positive (word.polish), english, ukrainian,
     grading_type, degree, correct_answer, options, grammar_reference`.
  - 404 if no seeded adjectives for the requested types.
- `POST /grading/validate` → records `Attempt(kind=AttemptKind.grading, ...)`,
  case-insensitive exact match, returns `was_correct + correct_answer + stats`.
- `GET /grading/stats` → today/trend/overall %, available adjective count. Reuse the
  Endings stats calculation shape.

### Prompt phrasing (degree × type)

- comparative, proste/nieregularne: "stopień wyższy" — answer `lepszy`
- superlative, proste/nieregularne: "stopień najwyższy" — answer `najlepszy`
- opisowe: label as "(opisowy)" so the learner expects `bardziej …` / `najbardziej …`.

## Frontend

- New nav card on Home (`App.jsx`, next to the Endings card) → `setActivePage("grading")`.
- Add `"grading"` to the two valid-views arrays (`App.jsx` ~lines 28 & 47). (Extract these
  to a shared `VALID_PAGES` const while here.)
- New `grading` view, cloned from the Endings view: sub-type checkboxes
  (Proste / Nieregularne / Opisowe), choose|write mode toggle, prompt showing the degree,
  grammar-reference panel, stats bar.
- New API client `src/api/grading.js` (`getConfig`, `getQuestion`, `validate`, `getStats`),
  re-exported from `src/api/index.js`.
- Grading view state + `fetchGradingConfig/Question/Stats` + `handleGradingAnswer/Skip`
  handlers, following the Endings pattern.

## Testing

- Backend: contract test `tests/contract/test_grading.py` — config, question (both
  degrees, each type), distractor caching (2nd call reuses column, no 2nd LLM call),
  validate chain, stats, 404 on empty. Extend `conftest.py` `fake_llm` with grading
  distractor output.
- Frontend: `src/api/grading.test.js` — URL/body shape for all four calls (4 tests).

## Out of scope / backlog

- Case/gender declension of comparatives (v2).
- Page-extraction refactor of `App.jsx` (shared `ExerciseView` component + `useExerciseView`
  hook) — separate backlog item raised in frontend review.
