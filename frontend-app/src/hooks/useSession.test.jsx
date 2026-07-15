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
