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

  it("explain POSTs the payload", async () => {
    const payload = {
      word_polish: "kot", word_translation: "cat", section: "translation",
      user_answer: "dog", correct_answer: "cat", was_correct: false,
    };
    await statsApi.explain(payload);
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toContain("/stats/explain");
    expect(JSON.parse(opts.body)).toEqual(payload);
  });
});
