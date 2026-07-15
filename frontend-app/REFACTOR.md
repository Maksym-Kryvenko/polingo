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
