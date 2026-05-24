/**
 * Unit tests for auth API wrapper functions.
 * apiClient is mocked so no real HTTP calls are made.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { apiClient } from "./client";
import { exchangeToken, fetchCurrentUser, callLogout } from "./auth";

vi.mock("./client", () => ({
  apiClient: {
    post: vi.fn(),
    get: vi.fn(),
  },
}));

beforeEach(() => {
  vi.clearAllMocks();
});

describe("exchangeToken", () => {
  it("posts to /auth/token/exchange with the exchange code and returns the token", async () => {
    vi.mocked(apiClient.post).mockResolvedValueOnce({
      data: { access_token: "jwt-abc", token_type: "bearer" },
    });

    const result = await exchangeToken("code123");

    expect(apiClient.post).toHaveBeenCalledWith("/auth/token/exchange", {
      exchange_code: "code123",
    });
    expect(result).toEqual({ access_token: "jwt-abc", token_type: "bearer" });
  });
});

describe("fetchCurrentUser", () => {
  it("fetches GET /users/me and returns the user profile", async () => {
    const profile = {
      id: 1,
      email: "alice@example.com",
      username: "alice",
      full_name: "Alice",
      avatar_url: "https://example.com/avatar.png",
      oauth_provider: "github",
    };
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: profile });

    const result = await fetchCurrentUser();

    expect(apiClient.get).toHaveBeenCalledWith("/users/me");
    expect(result).toEqual(profile);
  });

  it("returns null when the endpoint errors (graceful Story 3.1 fallback)", async () => {
    vi.mocked(apiClient.get).mockRejectedValueOnce(new Error("404 Not Found"));

    const result = await fetchCurrentUser();

    expect(result).toBeNull();
  });
});

describe("callLogout", () => {
  it("posts to /auth/logout", async () => {
    vi.mocked(apiClient.post).mockResolvedValueOnce({
      data: { message: "Logged out successfully" },
    });

    await callLogout();

    expect(apiClient.post).toHaveBeenCalledWith("/auth/logout");
  });
});
