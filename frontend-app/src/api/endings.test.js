import { describe, it, expect, vi, beforeEach } from "vitest";
import * as endingsApi from "./endings";

const mockOk = (obj) => ({ ok: true, text: () => Promise.resolve(JSON.stringify(obj)) });

beforeEach(() => {
  global.fetch = vi.fn(() => Promise.resolve(mockOk({})));
});

describe("endings api", () => {
  it("getQuestion builds cases query for nouns", async () => {
    await endingsApi.getQuestion({ part_of_speech: "rzeczownik", cases: "biernik" });
    const url = global.fetch.mock.calls[0][0];
    expect(url).toContain("/endings/question?part_of_speech=rzeczownik&cases=biernik");
    expect(url).not.toContain("tenses");
  });

  it("getQuestion builds tenses query for verbs and appends exclude", async () => {
    await endingsApi.getQuestion({ part_of_speech: "czasownik", tenses: "tera%C5%BAniejszy", exclude_word_id: 5 });
    const url = global.fetch.mock.calls[0][0];
    expect(url).toContain("part_of_speech=czasownik");
    expect(url).toContain("tenses=");
    expect(url).toContain("exclude_word_id=5");
  });

  it("validate POSTs word_id/answer/correct_answer", async () => {
    await endingsApi.validate({ word_id: 1, answer: "kota", correct_answer: "kota" });
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toContain("/endings/validate");
    expect(JSON.parse(opts.body)).toEqual({ word_id: 1, answer: "kota", correct_answer: "kota" });
  });
});
