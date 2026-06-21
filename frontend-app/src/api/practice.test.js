import { describe, it, expect, vi, beforeEach } from "vitest";
import * as practiceApi from "./practice";

const mockOk = (obj) => ({ ok: true, text: () => Promise.resolve(JSON.stringify(obj)) });

beforeEach(() => {
  global.fetch = vi.fn(() => Promise.resolve(mockOk({})));
});

describe("practice api", () => {
  it("validate POSTs the payload", async () => {
    await practiceApi.validate({ word_id: 1, answer: "x" });
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toContain("/practice/validate");
    expect(JSON.parse(opts.body)).toEqual({ word_id: 1, answer: "x" });
  });

  it("chooseQuestion builds the query and omits exclude when unset", async () => {
    await practiceApi.chooseQuestion({ language_set: "english", direction: "from_polish" });
    const url = global.fetch.mock.calls[0][0];
    expect(url).toContain("/practice/choose-translation/question?language_set=english&direction=from_polish");
    expect(url).not.toContain("exclude_word_id");
  });

  it("chooseQuestion appends exclude_word_id when set", async () => {
    await practiceApi.chooseQuestion({ language_set: "english", direction: "to_polish", exclude_word_id: 42 });
    expect(global.fetch.mock.calls[0][0]).toContain("exclude_word_id=42");
  });

  it("submitPronunciation POSTs FormData without JSON content-type", async () => {
    const fd = new FormData();
    fd.append("word_id", "1");
    await practiceApi.submitPronunciation(fd);
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toContain("/practice/pronunciation");
    expect(opts.body).toBe(fd);
    expect(opts.headers["Content-Type"]).toBeUndefined();
  });

  it("ttsUrl builds an encoded URL", () => {
    expect(practiceApi.ttsUrl("dzień dobry")).toContain("/practice/tts?text=dzie%C5%84%20dobry");
  });
});
