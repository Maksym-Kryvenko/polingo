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
