/**
 * Unit tests for /users/me API wrapper functions.
 * apiClient is mocked so no real HTTP calls are made.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { apiClient } from "./client";
import { fetchMe, patchMe, type UserMe } from "./users";

vi.mock("./client", () => ({
  apiClient: {
    get: vi.fn(),
    patch: vi.fn(),
  },
}));

const mockUser: UserMe = {
  id: 1,
  email: "alice@example.com",
  full_name: "Alice",
  avatar_url: "https://example.com/avatar.png",
  oauth_provider: "github",
  is_active: true,
  is_superuser: false,
  created_at: "2026-01-01T00:00:00Z",
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe("fetchMe", () => {
  it("calls GET /users/me and returns the user profile", async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockUser });

    const result = await fetchMe();

    expect(apiClient.get).toHaveBeenCalledWith("/users/me");
    expect(result).toEqual(mockUser);
  });
});

describe("patchMe", () => {
  it("calls PATCH /users/me with the update payload and returns the updated profile", async () => {
    const updated = { ...mockUser, full_name: "Alice Updated" };
    vi.mocked(apiClient.patch).mockResolvedValueOnce({ data: updated });

    const result = await patchMe({ full_name: "Alice Updated" });

    expect(apiClient.patch).toHaveBeenCalledWith("/users/me", { full_name: "Alice Updated" });
    expect(result).toEqual(updated);
  });
});
