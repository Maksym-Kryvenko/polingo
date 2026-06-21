import { describe, it, expect, vi, beforeEach } from "vitest";
import * as adminApi from "./admin";

const mockOk = (obj) => ({ ok: true, text: () => Promise.resolve(JSON.stringify(obj)) });

beforeEach(() => {
  global.fetch = vi.fn(() => Promise.resolve(mockOk({})));
});

describe("admin api", () => {
  it("updateSetting PUTs /admin/settings/{key} with value", async () => {
    await adminApi.updateSetting("tts_source", "server");
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toContain("/admin/settings/tts_source");
    expect(opts.method).toBe("PUT");
    expect(JSON.parse(opts.body)).toEqual({ value: "server" });
  });

  it("saveSentence PUTs /admin/sentences/{id}", async () => {
    await adminApi.saveSentence(3, { sentence: "s", correct_answer: "a" });
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toContain("/admin/sentences/3");
    expect(JSON.parse(opts.body)).toEqual({ sentence: "s", correct_answer: "a" });
  });

  it("fixSentence POSTs the fix endpoint", async () => {
    await adminApi.fixSentence(3);
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toContain("/admin/sentences/3/fix");
    expect(opts.method).toBe("POST");
  });

  it("clearDevices DELETEs /admin/devices", async () => {
    await adminApi.clearDevices();
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toContain("/admin/devices");
    expect(opts.method).toBe("DELETE");
  });
});
