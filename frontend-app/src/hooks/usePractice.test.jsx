import { describe, it, expect } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { usePractice } from "./usePractice";

describe("usePractice", () => {
  it("manages practice state correctly", () => {
    const wordPool = [
      { id: 1, polish: "dom", english: "house" },
      { id: 2, polish: "kot", english: "cat" }
    ];
    const { result } = renderHook(() => usePractice({ wordPool, languageSet: "english" }));

    // Test initial state
    expect(result.current.practiceMode).toBe("translation");
    expect(result.current.practiceDirection).toBe("from_polish");
    expect(result.current.answer).toBe("");

    // Test mode changes
    act(() => {
      result.current.setPracticeMode("writing");
    });
    expect(result.current.practiceMode).toBe("writing");

    // Test answer updates
    act(() => {
      result.current.setAnswer("house");
    });
    expect(result.current.answer).toBe("house");

    // Test status updates
    act(() => {
      result.current.setPracticeStatus({ type: "success", message: "Correct!" });
    });
    expect(result.current.practiceStatus.type).toBe("success");

    // Test reset
    act(() => {
      result.current.resetPracticeState();
    });
    expect(result.current.answer).toBe("");
    expect(result.current.practiceIndex).toBe(0);
  });
});
