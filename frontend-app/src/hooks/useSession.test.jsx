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

  // Regression: App.jsx practice handlers call setStats(p.stats) with the stats
  // returned by each submit/validate endpoint. The hook must expose setStats,
  // otherwise those handlers throw "setStats is not a function" — surfaced in
  // the UI as "Could not validate." during Choose practice.
  it("exposes setStats and updates stats when called", async () => {
    const { result } = renderHook(() => useSession());
    expect(typeof result.current.setStats).toBe("function");
    const fresh = { today_percentage: 50, trend: 5, overall_percentage: 42, available_words: 100 };
    act(() => {
      result.current.setStats(fresh);
    });
    expect(result.current.stats).toEqual(fresh);
  });
});
