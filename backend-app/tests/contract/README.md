# Contract-freeze tests (Lane L3)

Golden characterization tests of the HTTP API as of Plan 1. They assert response
SHAPE (status + keys + types), not volatile values that Plan 2 changes
(`gender` strings, history record `id` values, pronoun `oni/one` split).

## Running

These tests import `app`/`main` from the `backend-app` root, so that directory
must be on `PYTHONPATH`:

```bash
cd backend-app
PYTHONPATH=. .venv/bin/pytest tests/contract/ -v
```

## Frozen
words, practice (text), session, stats, endings, admin (read + settings update).

`endings/question` is frozen at its **404** empty-DB shape: on a freshly-seeded
DB no declension/conjugation/sentence rows exist (`fake_llm` stubs form-gen to
`[]`), so a 200 body is only testable once real form-gen runs.

## NOT frozen (manual verification only)
- POST /api/practice/pronunciation — multipart audio + STT
- GET  /api/practice/tts — audio/mpeg bytes
- POST /api/admin/sentences/{id}/fix — LLM regeneration
These need real binary I/O or live LLM and are excluded from the golden suite.

## Fixtures
`tests/contract/conftest.py` (nested, additive — the root conftest is never
edited) provides:
- `seeded_client` — a `TestClient` over a freshly-seeded in-memory DB with a
  default session and the first 6 words attached (choose-translation needs ≥4).
- `fake_llm_handlers` (autouse) — re-patches `validate_translation_via_llm` /
  `resolve_word_via_llm` in the **handler** namespaces (`app.api.practice`,
  `app.api.words`), because those modules bind the callables at import time so
  the root `fake_llm`'s patch of `app.llm.*` doesn't reach them.

## Plan 2 expectations
After Plan 2 merges and L3 rebases, these tests MUST still pass unchanged. If one
breaks, the contract changed unexpectedly — investigate before adjusting. They
are shape-level regression coverage, not a frozen golden-value snapshot, so they
deliberately tolerate the gender/pronoun/history-id value changes Plan 2 makes.
