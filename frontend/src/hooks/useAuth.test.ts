import { describe, it, expect } from "vitest";
import { renderHook } from "@testing-library/react";
import { useAuth } from "./useAuth";

describe("useAuth", () => {
  it("throws when used outside <AuthProvider>", () => {
    // Suppress the expected React error boundary console output.
    expect(() => renderHook(() => useAuth())).toThrow("useAuth must be used inside <AuthProvider>");
  });
});
