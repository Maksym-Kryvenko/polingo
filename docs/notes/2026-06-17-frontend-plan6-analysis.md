# Frontend Analysis — Plan 6 split + impact of Plans 2–4

> Research note produced by the Junior Frontend agent (haiku), 2026-06-17. Read-only analysis for lead review; not yet a plan. Source: `frontend-app/src/App.jsx` (~1340 lines) and `backend-app/app/api/*`.

## 1. App.jsx inventory

**8 screens** (page → line range → key state → endpoints):
- **home** (691–737): `activePage, languageSet, wordPool, stats, loadingStats` → GET /api/stats, GET /api/session
- **add** (740–784): `manualEntry, manualStatus, addingWords` → POST /words/check, /words/check/bulk, GET /words/initial, POST /session/words/bulk
- **practice** (787–888): `practiceMode (translation|writing|choose), practiceDirection, answer, practiceStatus, chooseQuestion, shuffledWords` → POST /practice/validate, /practice/skip, GET /practice/choose-translation/question, POST /practice/choose-translation/validate, GET /practice/tts
- **pronunciation** (891–918): `isRecording, pronunciationStatus, pronunciationIndex, mediaRecorderRef` → POST /practice/pronunciation, /practice/skip, GET /practice/tts
- **endings** (921–1067): `endingsConfig, endingsPoS, endingsCases, endingsTenses, endingsMode, endingsQuestion, endingsStatus, endingsStats, endingsWriteAnswer, showGrammar` → GET /endings/config, /endings/question, POST /endings/validate, GET /endings/stats
- **manage** (1070–1135): `allWords, editingWordId, editingValues, editSaving, manageFilterPoS` → GET /session/words/all, PUT /session/words/toggle, DELETE /session/words/{id}, PUT /words/{id}
- **admin** (1138–1266): devices/settings/sentences state → GET/DELETE /admin/devices(+/{id}), GET/PUT /admin/settings/{key}, GET/PUT/POST(fix)/DELETE /admin/sentences(+/{id}); polls devices every 5s
- **stats-detail** (1269–1335): `historyRecords, historyTotal, historyLoading, expandedExplain, explainText, explainLoading` → GET /stats/history, POST /stats/explain

**~66 state variables**, **24 endpoints** total — all in one component.

## 2. Proposed Plan 6 split

Target tree: `src/api/client` (all endpoints as named fns), `src/types` (Exercise contract), `src/state/*` (custom hooks: session/stats/practice/endings/admin/history), `src/components/{layout,pages,practice,endings,shared}`. App.jsx drops from 1340 → ~80 lines (routing shell).

**Exercise component contract** (every Format implements):
```
Exercise { topic, format, targetWord, prompt, correctAnswer: string|string[], alternatives?, metadata?, grammarReference? }
ExerciseComponentProps { exercise, onSubmit(answer)->Promise<ExerciseResult>, onSkip()->Promise<ExerciseResult>, isLoading? }
ExerciseResult { was_correct, correct_answer, alternatives?, feedback?, stats? }
```
`correctAnswer` is an array for word-order/matching. A shared `ExerciseContainer` owns question/answer/feedback display; per-format components differ only in input method.

~30 files, ~2500–3500 lines refactored.

## 3. Frontend impact of Plans 2–4

- **Plan 2 (unified Attempt):** history response `section` → `topic`+`format`; StatsDetailPage badge rendering (line 1311) changes; optional `?topic=&format=` history filters.
- **Plan 3 (forms_status):** word cards (AddPage ~772, ManagePage ~1098) show pending/generated/failed badge; endings question endpoint may return null while forms pending → "X words still generating"; add-word UX shows spinner + poll.
- **Plan 4 (Topic×Format engine):** unified `/api/practice/exercise?topic=&format=` endpoint; UI needs a **validity matrix** to disable invalid cells (e.g. aspect×MC); dynamic routing by `exercise.format`; grammar panel moves from EndingsPage into shared ExerciseContainer; aspect/agreement/government show "coming soon" until data exists.

## 4. Open questions for lead
1. Hash routing vs React Router? 2. Custom hooks vs Zustand/Redux? 3. Adopt TypeScript (fully/partially/no)? 4. CSS: global vs CSS modules? 5. Exercise endpoint path `/api/exercise` vs `/api/practice/exercise`, back-compat? 6. Validity matrix static vs `/api/practice/validity-matrix`? 7. forms_status: poll vs WebSocket vs manual refresh? 8. History schema: alias old fields for back-compat or lock-step update? 9. Storybook in Plan 6 or 7? 10. New (pending) word sort order in Manage? 11. TTS cache useRef vs localStorage? 12. Can Plan 6 precede Plan 4? 13. Component-test infra in Plan 6 or 7?

> Lead note: defer these to the Plan 6 grill. Items 5–8 (API contract) should be decided during Plans 2–4 design so the UI isn't built against a guess.
