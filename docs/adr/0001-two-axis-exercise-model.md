---
Status: proposed
Date: 2026-06-17
---

# Exercise model: orthogonal Topic × Format

> **Status note:** This describes the *target* redesign, not the current code. Today practice modes are hard-coded and records are split across `PracticeRecord` and `EndingsPracticeRecord`. There are no `Topic`/`Format` columns or an `Exercise`/`Attempt` table yet.

Practice will be modelled as two independent axes — **Topic** (grammar skill: cases, tenses, aspect, agreement, government) and **Format** (how prompted: multiple-choice, fill-blank, translate, write, speak, listen, word-order, cloze, matching). An Exercise is a (Topic, Format) pair plus a target Word/Form; an Attempt records the result keyed by both.

We chose this over a flat enum of named exercise types because the catalogue grows combinatorially: with N topics and M formats, the flat model needs N×M hand-maintained types, whereas the two-axis model lets us add a topic or a format independently and catalogue/route them generically.

## Considered options

- **Flat enum of named exercise types** — rejected: N×M hand-maintained variants, no clean way to slice stats by skill vs by format.
- **Topic-primary, one fixed format per topic** — rejected: too rigid; we want the same topic drillable several ways.

## Consequences

- **The N×M saving is in cataloguing, routing, and stats-slicing — not in implementation effort.** Per-cell generation and grading work still grows with N×M; each Format defines its own grading contract (grading is *not* universal across cells).
- **Not every cell is valid.** Degenerate combinations exist (e.g. `pronunciation × fill-blank`, `aspect × multiple-choice` where the binary collapses the distractor pool, `word-order × translate` where a single `correct_answer` can't hold multiple valid orderings). The implementation must carry an explicit **validity matrix** and define behaviour for unsupported cells (skip/reject), rather than assuming every cell is generatable.
- Stats become sliceable along both axes (weak *topics* vs weak *formats*).
