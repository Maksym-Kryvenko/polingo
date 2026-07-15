import { describe, it, expect, vi, beforeEach } from "vitest";
import * as wordsApi from "./words";

const mockOk = (obj) => ({ ok: true, text: () => Promise.resolve(JSON.stringify(obj)) });

beforeEach(() => {
  global.fetch = vi.fn(() => Promise.resolve(mockOk({})));
});

describe("words api", () => {
  it("getInitial builds the count query", async () => {
    await wordsApi.getInitial(10);
    expect(global.fetch.mock.calls[0][0]).toContain("/words/initial?count=10");
  });

  it("updateWord PUTs /words/{id} with translations", async () => {
    await wordsApi.updateWord(7, { polish: "a", english: "b", ukrainian: "c" });
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toContain("/words/7");
    expect(opts.method).toBe("PUT");
    expect(JSON.parse(opts.body)).toEqual({ polish: "a", english: "b", ukrainian: "c" });
  });

  it("checkWord POSTs text", async () => {
    await wordsApi.checkWord("robić");
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toContain("/words/check");
    expect(JSON.parse(opts.body)).toEqual({ text: "robić" });
  });

  it("checkWordsBulk POSTs to bulk endpoint", async () => {
    await wordsApi.checkWordsBulk("a, b");
    expect(global.fetch.mock.calls[0][0]).toContain("/words/check/bulk");
  });
});
