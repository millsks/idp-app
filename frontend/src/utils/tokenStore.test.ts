/**
 * Unit tests for the module-level token store.
 * These are stateful — each test resets the store to a known baseline.
 */
import { describe, it, expect, vi, afterEach } from "vitest";
import { getAuthToken, setAuthToken, setLogoutCallback, runLogout } from "./tokenStore";

afterEach(() => {
  // Reset store state between tests.
  setAuthToken(null);
  setLogoutCallback(() => {
    /* unregistered */
  });
});

describe("getAuthToken / setAuthToken", () => {
  it("returns null when no token has been set", () => {
    expect(getAuthToken()).toBeNull();
  });

  it("returns the stored token after setAuthToken", () => {
    setAuthToken("my-jwt-token");
    expect(getAuthToken()).toBe("my-jwt-token");
  });

  it("clears the token when setAuthToken(null) is called", () => {
    setAuthToken("some-token");
    setAuthToken(null);
    expect(getAuthToken()).toBeNull();
  });
});

describe("setLogoutCallback / runLogout", () => {
  it("calls the registered logout callback when runLogout is invoked", () => {
    const logoutFn = vi.fn();
    setLogoutCallback(logoutFn);
    runLogout();
    expect(logoutFn).toHaveBeenCalledOnce();
  });

  it("does not throw when runLogout is called with a no-op callback", () => {
    setLogoutCallback(() => {
      /* no-op */
    });
    expect(() => {
      runLogout();
    }).not.toThrow();
  });
});
