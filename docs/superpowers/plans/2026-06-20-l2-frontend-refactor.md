# L2 — Frontend Refactor (Part 1: API client + state layer) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Horizontal execution — Lane L2.** Runs concurrently with L1/L3/L4. **Branch:** `plan-6-fe-refactor`. Merges 3rd (after L1 Plan 2); rebase on the post-Plan-2 `main` and absorb the contract delta (pronoun `oni/one`, gender values) before merging. See `2026-06-20-horizontal-execution-map.md`.

**Goal:** Extract a typed-by-convention **API client** and a **state layer** (custom hooks) out of the monolithic `frontend-app/src/App.jsx` (1340 lines, ~24 fetch calls, ~66 state vars) **without changing behavior** — establishing the structure Plan 6 part 2 (per-Format components) will build on.

**Architecture:** Introduce Vitest (no test infra exists today) so the extraction is verifiable. Move all `fetch()` calls into `src/api/` modules grouped by domain (one function per endpoint), unit-tested with a mocked `fetch`. Then rewire `App.jsx` to call the client instead of inline `fetch`. Finally extract per-domain state into custom hooks, starting with two domains as the established pattern; remaining domains follow the same shape. **No per-Format exercise components** — those need Plan 4's contract and are explicitly out of scope.

**Tech Stack:** React 18, Vite 5, Vitest + @testing-library/react, plain JS (no TypeScript — match existing).

**Depends on:** Plan 1 (merged). Branches from current `main`. The current API base URL resolves to `import.meta.env.VITE_API_BASE_URL || http://{hostname}:8000/api` (`App.jsx:3`).

**Owned files:** `frontend-app/**` only. Do NOT touch any backend file.

**Out of scope:** per-Format exercise components (Plan 6 part 2 / Plan 4); pronunciation/TTS rewrites; visual/CSS changes.

---

### Task 1: Add Vitest test infrastructure

**Files:**
- Modify: `frontend-app/package.json`
- Create: `frontend-app/vitest.config.js`
- Create: `frontend-app/src/test/setup.js`

- [ ] **Step 1: Add dev dependencies and a test script**

In `frontend-app/package.json`, add to `devDependencies`:

```json
    "vitest": "^2.0.0",
    "@testing-library/react": "^16.0.0",
    "@testing-library/dom": "^10.4.0",
    "@testing-library/jest-dom": "^6.4.0",
    "jsdom": "^25.0.0"
```

> `@testing-library/dom` is a **required peer** of `@testing-library/react` v16 (de-bundled since v14) — omitting it makes `renderHook` fail to resolve. Vitest 2 is compatible with the installed Vite 5 / React 18; jsdom 25 needs Node 18+.

and add to `scripts`:

```json
    "test": "vitest run",
    "test:watch": "vitest"
```

Run: `cd frontend-app && npm install`
Expected: deps install.

- [ ] **Step 2: Create the Vitest config**

Create `frontend-app/vitest.config.js`:

```javascript
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.js"],
  },
});
```

- [ ] **Step 3: Create the test setup**

Create `frontend-app/src/test/setup.js`:

```javascript
import "@testing-library/jest-dom";
```

- [ ] **Step 4: Add a smoke test to prove the runner works**

Create `frontend-app/src/test/smoke.test.js`:

```javascript
import { describe, it, expect } from "vitest";

describe("vitest", () => {
  it("runs", () => {
    expect(1 + 1).toBe(2);
  });
});
```

- [ ] **Step 5: Run it**

Run: `cd frontend-app && npm test`
Expected: 1 passed.

- [ ] **Step 6: Commit**

```bash
git add frontend-app/package.json frontend-app/package-lock.json frontend-app/vitest.config.js frontend-app/src/test/setup.js frontend-app/src/test/smoke.test.js
git commit -m "test(fe): add Vitest + testing-library infrastructure"
```

---

### Task 2: Extract the API client (base + one domain module, TDD)

**Files:**
- Create: `frontend-app/src/api/base.js`
- Create: `frontend-app/src/api/session.js`
- Create: `frontend-app/src/api/session.test.js`

We establish the base helper and the `session` domain as the pattern; later tasks repeat it for the other domains.

- [ ] **Step 1: Write the failing test for the session client**

Create `frontend-app/src/api/session.test.js`:

```javascript
import { describe, it, expect, vi, beforeEach } from "vitest";
import * as sessionApi from "./session";

// apiFetch reads resp.text() then JSON.parses, so the mock returns text().
const mockOk = (obj) => ({ ok: true, text: () => Promise.resolve(JSON.stringify(obj)) });

beforeEach(() => {
  global.fetch = vi.fn(() => Promise.resolve(mockOk({ language_set: "english", words: [] })));
});

describe("session api", () => {
  it("getSession GETs /api/session and returns parsed json", async () => {
    const data = await sessionApi.getSession();
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/session"),
      expect.objectContaining({ method: "GET" })
    );
    expect(data.language_set).toBe("english");
  });

  it("setLanguage PUTs /api/session/language with the body", async () => {
    await sessionApi.setLanguage("ukrainian");
    const [, opts] = global.fetch.mock.calls[0];
    expect(opts.method).toBe("PUT");
    expect(JSON.parse(opts.body)).toEqual({ language_set: "ukrainian" });
  });
});
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `cd frontend-app && npx vitest run src/api/session.test.js`
Expected: FAIL — `./session` does not exist.

- [ ] **Step 3: Create the base helper**

Create `frontend-app/src/api/base.js`. **Match the current code EXACTLY** — `App.jsx:3` uses the nullish operator `??` (NOT `||`; `??` only falls back on null/undefined, so an empty-string `VITE_API_BASE_URL` is preserved), and every call goes through a `buildUrl(path) => \`${API_BASE_URL}/${path}\`` helper (`App.jsx:32`) where `path` has **no leading slash** (e.g. `buildUrl("session")`).

```javascript
export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ??
  `http://${window.location.hostname}:8000/api`;

// New client convention: paths carry a LEADING slash (e.g. "/session").
// API_BASE_URL has no trailing slash, so the join is exact. (This replaces the
// old App.jsx buildUrl("session") no-slash convention, which is removed in Task 4.)
export async function apiFetch(path, { method = "GET", body, headers, raw } = {}) {
  const opts = { method, headers: { ...(headers || {}) } };
  if (body instanceof FormData) {
    opts.body = body;
  } else if (body !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const resp = await fetch(`${API_BASE_URL}${path}`, opts);
  if (raw) return resp;          // caller inspects resp.ok / blob itself
  if (!resp.ok) return null;     // NON-THROWING: mirrors the old `if (r.ok) {...}` swallow
  const text = await resp.text();
  return text ? JSON.parse(text) : null;  // tolerate empty/204 bodies (DELETEs)
}
```

> **Behavior-preservation (critic-driven, important):** the existing `App.jsx` fetches almost all do `const r = await fetch(...); if (r.ok) { setX(await r.json()); }` and **swallow** failures (no throw). So `apiFetch` is **non-throwing**: it returns `null` on non-ok and tolerates empty bodies. This keeps the mechanical swap 1:1. Two consequences for Task 4:
> - At each migrated call site, the old `if (r.ok)` guard becomes "if the returned value is non-null" — preserve any `else` branch (e.g. `fetchEndingsQuestion` sets the question to `null` on failure; `fetchTtsSetting` must stay silent on a 404). Reproduce each else-branch explicitly.
> - **`raw: true`** is for sites that read non-JSON or inspect the response directly: the **TTS blob** fetch (`playPronunciation`, App.jsx ~270) and the **pronunciation upload** (App.jsx ~559, though it does read json — keep non-raw). Fire-and-forget calls that never read a body (toggleOnTheFly/toggleTtsSource, deleteDevice/clearDevices, chooseSkip, endingsSkip, deleteWord, deleteSentence) are safe with the non-throwing empty-body handling above — they just ignore the returned `null`.

- [ ] **Step 4: Create the session client**

Create `frontend-app/src/api/session.js`:

```javascript
import { apiFetch } from "./base";

export const getSession = () => apiFetch("/session");
export const getAllWords = () => apiFetch("/session/words/all");
export const setLanguage = (language_set) =>
  apiFetch("/session/language", { method: "PUT", body: { language_set } });
export const addWord = (word_id) =>
  apiFetch("/session/words", { method: "POST", body: { word_id } });
export const addWordsBulk = (word_ids) =>
  apiFetch("/session/words/bulk", { method: "POST", body: { word_ids } });
export const toggleWord = (word_id, enabled) =>
  apiFetch("/session/words/toggle", { method: "PUT", body: { word_id, enabled } });
export const deleteWord = (word_id) =>
  apiFetch(`/session/words/${word_id}`, { method: "DELETE" });
```

- [ ] **Step 5: Run the test**

Run: `cd frontend-app && npx vitest run src/api/session.test.js`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend-app/src/api/base.js frontend-app/src/api/session.js frontend-app/src/api/session.test.js
git commit -m "feat(fe): extract API base helper + session client (tested)"
```

---

### Task 3: Extract the remaining API client modules

**Files:**
- Create: `frontend-app/src/api/words.js`, `practice.js`, `endings.js`, `stats.js`, `admin.js`
- Create: matching `*.test.js` for each
- Create: `frontend-app/src/api/index.js` (barrel)

Repeat the Task-2 pattern per domain. The full endpoint→function mapping (from the App.jsx audit):

- **words.js:** `getInitial(count)` → `GET /words/initial?count=`; `updateWord(id, {polish,english,ukrainian})` → `PUT /words/{id}`; `checkWord(text)` → `POST /words/check`; `checkWordsBulk(text)` → `POST /words/check/bulk`.
- **practice.js:** `validate(payload)` → `POST /practice/validate`; `skip(payload)` → `POST /practice/skip`; `chooseQuestion({language_set,direction,exclude_word_id})` → `GET /practice/choose-translation/question`; `chooseValidate(payload)` → `POST /practice/choose-translation/validate`; `submitPronunciation(formData)` → `POST /practice/pronunciation` (`body: formData`, returns json — non-raw); `ttsUrl(text)` → returns the URL string `${API_BASE_URL}/practice/tts?text=...` (URL builder, not a fetch). **Note:** `App.jsx` has NO `/practice/submit` call — do not add a `submit()` function (that endpoint exists server-side but is unused by the UI). **"Choose skip"** is `chooseValidate` with `answer: ""` (not a distinct endpoint).
- **endings.js:** `getConfig()` → `GET /endings/config`; `getQuestion({part_of_speech,cases,tenses,exclude_word_id})` → `GET /endings/question`; `validate({word_id,answer,correct_answer})` → `POST /endings/validate`; `getStats()` → `GET /endings/stats`. **"Endings skip"** is `validate` with `answer: ""` (not a distinct endpoint).
- **stats.js:** `getStats()` → `GET /stats`; `getHistory({limit,language_set})` → `GET /stats/history`; `explain(payload)` → `POST /stats/explain` where payload is `{word_polish, word_translation, section, user_answer, correct_answer, was_correct}` (the `section` field is pre-Plan-2 naming — see the rebase note).
- **admin.js:** `getDevices()` → `GET /admin/devices`; `deleteDevice(id)` → `DELETE /admin/devices/{id}`; `clearDevices()` → `DELETE /admin/devices`; `getSettings()` → `GET /admin/settings`; `getSetting(key)` → `GET /admin/settings/{key}`; `updateSetting(key, value)` → `PUT /admin/settings/{key}` body `{value}`; `getSentences()` → `GET /admin/sentences`; `saveSentence(id, {sentence,correct_answer})` → `PUT /admin/sentences/{id}`; `fixSentence(id)` → `POST /admin/sentences/{id}/fix`; `deleteSentence(id)` → `DELETE /admin/sentences/{id}`.

- [ ] **Step 1: Write one test per module (query-string + body assertions)**

For each module create a `*.test.js` mirroring `session.test.js`: mock `fetch`, call each function, assert the URL (path + query) and method/body. Example for `stats.js`:

```javascript
import { describe, it, expect, vi, beforeEach } from "vitest";
import * as statsApi from "./stats";

beforeEach(() => {
  global.fetch = vi.fn(() =>
    Promise.resolve({ ok: true, text: () => Promise.resolve(JSON.stringify({ records: [], total: 0 })) })
  );
});

describe("stats api", () => {
  it("getHistory builds the query string", async () => {
    await statsApi.getHistory({ limit: 100, language_set: "english" });
    expect(global.fetch.mock.calls[0][0]).toContain("/stats/history?limit=100&language_set=english");
  });
});
```

Write analogous focused tests for `words`, `practice`, `endings`, `admin` (at least the query-building and body-shaping functions).

- [ ] **Step 2: Run them to confirm they fail**

Run: `cd frontend-app && npx vitest run src/api/`
Expected: FAIL — modules not yet created.

- [ ] **Step 3: Implement the five modules**

Create each module following the `session.js` shape, using `apiFetch`. For query-string endpoints build the path with `URLSearchParams` (omit undefined params to match current behavior — e.g. `exclude_word_id` is only appended when set). For `practice.ttsUrl`, export a pure URL builder:

```javascript
import { API_BASE_URL } from "./base";
export const ttsUrl = (text) => `${API_BASE_URL}/practice/tts?text=${encodeURIComponent(text)}`;
```

- [ ] **Step 4: Create the barrel**

Create `frontend-app/src/api/index.js`:

```javascript
export * as session from "./session";
export * as words from "./words";
export * as practice from "./practice";
export * as endings from "./endings";
export * as stats from "./stats";
export * as admin from "./admin";
```

- [ ] **Step 5: Run the full api test suite**

Run: `cd frontend-app && npx vitest run src/api/`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend-app/src/api
git commit -m "feat(fe): extract words/practice/endings/stats/admin API clients (tested)"
```

---

### Task 4: Rewire App.jsx to use the API client

**Files:**
- Modify: `frontend-app/src/App.jsx` (replace ~24 inline `fetch` calls)

This is a mechanical, behavior-preserving swap. Do it in small commits per domain so a regression is easy to bisect.

- [ ] **Step 1: Import the client barrel**

At the top of `App.jsx`, add:

```javascript
import * as api from "./api";
```

- [ ] **Step 2: Replace the session + stats fetches**

Replace each inline `fetch(`${API_BASE_URL}/session...`)` / `/stats...` call (App.jsx lines ~141, 149, 160, 331, 425, 433, 461, 623, 631, 641) with the matching `api.session.*` / `api.stats.*` call. Keep the surrounding state updates identical. Remove the now-unused local `API_BASE_URL` const **only after** all call sites are migrated (it is re-exported from `api/base.js`).

- [ ] **Step 3: Build to verify no breakage**

Run: `cd frontend-app && npm run build`
Expected: build succeeds, no unresolved imports.

- [ ] **Step 4: Commit**

```bash
git add frontend-app/src/App.jsx
git commit -m "refactor(fe): route session/stats calls through API client"
```

- [ ] **Step 5: Repeat for practice, endings, words, admin**

For each remaining domain, replace its inline `fetch` calls with the client functions, run `npm run build`, and commit per domain:

```bash
git commit -m "refactor(fe): route <domain> calls through API client"
```

- [ ] **Step 6: Remove the dead `buildUrl`/`API_BASE_URL` locals and confirm no raw fetch remains**

All inline calls go through `const buildUrl = (path) => \`${API_BASE_URL}/${path}\`` (`App.jsx:32`), e.g. `fetch(buildUrl("session"))`. After migrating every domain, delete the local `API_BASE_URL` (App.jsx:3) **and** `buildUrl` (App.jsx:32) — the TTS URL now comes from `api.practice.ttsUrl`.

Run: `cd frontend-app && grep -n "buildUrl(\|API_BASE_URL" src/App.jsx`
Expected: **no output** (both locals removed; nothing references them). If the TTS blob fetch is still inline, it must use `api.practice.ttsUrl(text)` for the URL and `{ raw: true }`-style direct `fetch` is acceptable only with a `// raw: blob` comment.

---

### Task 5: Extract two state hooks as the pattern

**Files:**
- Create: `frontend-app/src/hooks/useSession.js`
- Create: `frontend-app/src/hooks/useSession.test.jsx`
- Create: `frontend-app/src/hooks/usePractice.js`
- Modify: `frontend-app/src/App.jsx`

The 66 state vars span 8 domains. We extract the two cleanest (`useSession`, `usePractice`) to establish the pattern; the remaining six (`useAddWords`, `usePronunciation`, `useEndings`, `useManage`, `useAdmin`, `useHistory`) follow the identical shape in a follow-up plan, listed below.

- [ ] **Step 1: Write the failing hook test**

Create `frontend-app/src/hooks/useSession.test.jsx`:

```javascript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useSession } from "./useSession";

beforeEach(() => {
  global.fetch = vi.fn(() =>
    Promise.resolve({
      ok: true,
      text: () => Promise.resolve(JSON.stringify({ language_set: "english", words: [{ id: 1 }] })),
    })
  );
});

describe("useSession", () => {
  it("loads session on mount and exposes languageSet + wordPool", async () => {
    const { result } = renderHook(() => useSession());
    await waitFor(() => expect(result.current.wordPool.length).toBe(1));
    expect(result.current.languageSet).toBe("english");
  });

  it("changeLanguage updates state", async () => {
    const { result } = renderHook(() => useSession());
    await act(async () => {
      await result.current.changeLanguage("ukrainian");
    });
    expect(result.current.languageSet).toBe("ukrainian");
  });
});
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `cd frontend-app && npx vitest run src/hooks/useSession.test.jsx`
Expected: FAIL — `./useSession` does not exist.

- [ ] **Step 3: Implement useSession**

Create `frontend-app/src/hooks/useSession.js`, moving the session/wordPool/languageSet/stats state and their loaders out of `App.jsx`:

```javascript
import { useState, useEffect, useCallback } from "react";
import * as api from "../api";

export function useSession() {
  const [languageSet, setLanguageSet] = useState("english");
  const [wordPool, setWordPool] = useState([]);
  const [stats, setStats] = useState(null);
  const [loadingStats, setLoadingStats] = useState(false);  // preserve the hero "loading…" label

  const refreshSession = useCallback(async () => {
    const data = await api.session.getSession();
    if (!data) return;                 // non-throwing apiFetch returns null on failure
    setLanguageSet(data.language_set);
    setWordPool(data.words || []);
  }, []);

  const refreshStats = useCallback(async () => {
    setLoadingStats(true);
    const data = await api.stats.getStats();
    if (data) setStats(data);
    setLoadingStats(false);
  }, []);

  const changeLanguage = useCallback(async (next) => {
    await api.session.setLanguage(next);
    setLanguageSet(next);
  }, []);

  useEffect(() => {
    refreshSession();
    refreshStats();
  }, [refreshSession, refreshStats]);

  return { languageSet, wordPool, stats, loadingStats, refreshSession, refreshStats,
           changeLanguage, setLanguageSet, setWordPool };
}
```

> **Cross-cutting warnings (critic-driven — `languageSet` is the most-referenced var in the file):**
> - **Enumerate every consumer before wiring.** `languageSet` is read by `fetchHistory` (~331), `fetchChooseQuestion` (~200), the practice/validate/skip/pronunciation handlers (~480/497/513/573), and the page-change effect's dep array (~402). `setWordPool` is called by `handleLoadInitial` (~436) and `handleManualSubmit` (~464); `setLanguageSet` by `handleLanguageChange` (~423) and the home `<select>` onChange (~696). All of these must now read the hook's value/setters — grep `languageSet`, `setLanguageSet`, `setWordPool`, `wordPool` in App.jsx and update each.
> - **Do NOT delete App's mount effect wholesale.** The current mount effect (~369) also calls `fetchEndingsConfig()` and `fetchTtsSetting()`. `useSession` only takes over session+stats; those two loaders must remain in App (or move to their own hooks in the follow-up). Removing them silently breaks endings config + TTS source loading.
> - **StrictMode:** if `main.jsx` wraps `<App/>` in `<React.StrictMode>`, the hook's mount effect double-fires in dev (same as the current App). The test uses `waitFor`, which tolerates this. Confirm StrictMode status; behavior is preserved either way.

- [ ] **Step 4: Run the hook test**

Run: `cd frontend-app && npx vitest run src/hooks/useSession.test.jsx`
Expected: PASS.

- [ ] **Step 5: Wire useSession into App.jsx and remove the migrated state**

In `App.jsx`, replace the inlined session/stats state declarations and their effects with `const { languageSet, wordPool, stats, refreshSession, refreshStats, changeLanguage } = useSession();`. Run `npm run build`; expect success.

- [ ] **Step 6: Extract usePractice the same way, then build**

Create `frontend-app/src/hooks/usePractice.js` moving practiceMode/practiceIndex/answer/practiceStatus/shuffledWords/lastAnswer/chooseQuestion. Add a focused test for the question-fetch + answer flow. Run `npm run build`.

- [ ] **Step 7: Run the whole frontend suite + build**

Run: `cd frontend-app && npm test && npm run build`
Expected: all tests pass, build succeeds.

- [ ] **Step 8: Commit**

```bash
git add frontend-app/src/hooks frontend-app/src/App.jsx
git commit -m "refactor(fe): extract useSession + usePractice state hooks (tested)"
```

---

### Task 6: Document the remaining extraction + manual smoke

**Files:**
- Create: `frontend-app/REFACTOR.md`

- [ ] **Step 1: Record the follow-up extraction list**

Create `frontend-app/REFACTOR.md`:

```markdown
# Frontend refactor status (Plan 6 part 1)

## Done
- API client: `src/api/{base,session,words,practice,endings,stats,admin}.js` (Vitest-covered)
- App.jsx routes all non-raw calls through `src/api`
- State hooks extracted: useSession, usePractice

## Remaining state hooks (same pattern, follow-up plan)
useAddWords · usePronunciation · useEndings · useManage · useAdmin · useHistory

## Out of scope (needs Plan 4 contract)
Per-Format exercise components.

## Plan 2 contract delta to absorb on rebase
- pronoun render points (oni/one split) — App.jsx ~988, ~1243
- gender values now 5-way — display only, no logic change
```

- [ ] **Step 2: Manual smoke check**

Run the app against a running backend and click through home → practice → endings → stats. Confirm no console errors and identical behavior to pre-refactor. (No automated e2e in this lane — that is L3's domain.)

- [ ] **Step 3: Commit**

```bash
git add frontend-app/REFACTOR.md
git commit -m "docs(fe): record refactor status and remaining extraction"
```

---

## Self-review

- API client covers all 24 endpoints from the App.jsx audit (Tasks 2–3). ✓
- Vitest infra added since none existed (Task 1). ✓
- Behavior preserved: base-URL uses `??` (not `||`) to match `App.jsx:3`; `apiFetch` is **non-throwing** (returns null on non-ok, tolerates empty/204 bodies) to mirror the existing `if (r.ok)` swallow pattern; `buildUrl`+`API_BASE_URL` locals are removed together (Task 4 Step 6 grep); `raw` reserved for the TTS blob; build run after every rewire. ✓
- `languageSet`/`wordPool` consumers enumerated; orphaned mount loaders (endingsConfig/tts) retained; `loadingStats` preserved; StrictMode noted (Task 5). ✓
- No invented endpoints: `practice.submit` dropped (unused by UI); choose/endings "skip" documented as validate-with-empty-answer; `section` field in explain body flagged for the Plan-2 rebase. ✓
- State-layer extraction demonstrated on 2 domains with the remaining 6 explicitly listed as same-pattern follow-up (Tasks 5–6) — avoids a risky 66-variable big-bang. ✓
- Per-Format components correctly deferred to Plan 4/Plan 6 part 2. ✓
- Contract delta from Plan 2 documented for rebase (Task 6). ✓
