/**
 * Tests for ProfilePage — covers Story 3.1 ACs 7–13.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { ThemeProvider } from "@mui/material";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { ProfilePage } from "./ProfilePage";
import { theme } from "../theme";
import type { UserMe } from "../api/users";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("../hooks/useAuth", () => ({
  useAuth: () => ({ user: null, isAuthenticated: true, isLoading: false }),
}));

const mockFetchMe = vi.fn<() => Promise<UserMe>>();
const mockPatchMe = vi.fn<(update: { full_name: string }) => Promise<UserMe>>();

vi.mock("../api/users", () => ({
  fetchMe: (...args: unknown[]) => mockFetchMe(...(args as [])),
  patchMe: (update: { full_name: string }) => mockPatchMe(update),
}));

// ---------------------------------------------------------------------------
// Fixture
// ---------------------------------------------------------------------------

const baseProfile: UserMe = {
  id: 1,
  email: "alice@example.com",
  full_name: "Alice Example",
  avatar_url: "https://avatars.example.com/alice.png",
  oauth_provider: "github",
  is_active: true,
  is_superuser: false,
  created_at: "2026-05-01T00:00:00Z",
};

// ---------------------------------------------------------------------------
// Render helper
// ---------------------------------------------------------------------------

function renderProfilePage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ThemeProvider theme={theme}>
          <ProfilePage />
        </ThemeProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("ProfilePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows a loading spinner while data is fetching (AC-12)", () => {
    mockFetchMe.mockReturnValue(
      new Promise((_resolve) => {
        /* never resolves */
      }),
    ); // never resolves
    renderProfilePage();
    expect(screen.getByRole("progressbar")).toBeInTheDocument();
  });

  it("shows an error alert when the fetch fails (AC-12)", async () => {
    mockFetchMe.mockRejectedValue(new Error("network error"));
    renderProfilePage();
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/failed to load/i);
    });
  });

  it("renders profile data after successful fetch (AC-8, AC-9)", async () => {
    mockFetchMe.mockResolvedValue(baseProfile);
    renderProfilePage();

    await waitFor(() => {
      expect(screen.getByText("My Profile")).toBeInTheDocument();
    });

    // Display name
    expect(screen.getByText("Alice Example")).toBeInTheDocument();
    // Email read-only field
    expect(screen.getByDisplayValue("alice@example.com")).toBeInTheDocument();
    // Read-only helper text (AC-9)
    expect(screen.getByText(/managed by your OAuth provider/i)).toBeInTheDocument();
    // Member since (AC-8)
    expect(screen.getByText(/Member since/i)).toBeInTheDocument();
    // GitHub provider badge (AC-8)
    expect(screen.getByLabelText(/OAuth provider: GitHub/i)).toBeInTheDocument();
  });

  it("shows Google provider badge for google OAuth users (AC-8)", async () => {
    mockFetchMe.mockResolvedValue({ ...baseProfile, oauth_provider: "google" });
    renderProfilePage();
    await waitFor(() => {
      expect(screen.getByLabelText(/OAuth provider: Google/i)).toBeInTheDocument();
    });
  });

  it("pre-populates the display name field with current value (AC-10)", async () => {
    mockFetchMe.mockResolvedValue(baseProfile);
    renderProfilePage();
    await waitFor(() => {
      expect(screen.getByRole("textbox", { name: /display name/i })).toHaveValue("Alice Example");
    });
  });

  it("shows inline validation error for blank name without calling API (AC-11)", async () => {
    mockFetchMe.mockResolvedValue(baseProfile);
    renderProfilePage();
    await waitFor(() => {
      expect(screen.getByRole("textbox", { name: /display name/i })).toBeInTheDocument();
    });

    const nameField = screen.getByRole("textbox", { name: /display name/i });
    await userEvent.clear(nameField);
    await userEvent.type(nameField, "   ");
    await userEvent.click(screen.getByRole("button", { name: /save/i }));

    expect(screen.getByText(/must not be blank/i)).toBeInTheDocument();
    expect(mockPatchMe).not.toHaveBeenCalled();
  });

  it("calls PATCH /users/me and shows success message on save (AC-10, AC-13)", async () => {
    const updatedProfile = { ...baseProfile, full_name: "Alice Updated" };
    mockFetchMe.mockResolvedValue(baseProfile);
    mockPatchMe.mockResolvedValue(updatedProfile);

    renderProfilePage();
    await waitFor(() => {
      expect(screen.getByRole("textbox", { name: /display name/i })).toHaveValue("Alice Example");
    });

    const nameField = screen.getByRole("textbox", { name: /display name/i });
    await userEvent.clear(nameField);
    await userEvent.type(nameField, "Alice Updated");
    await userEvent.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() => {
      expect(mockPatchMe).toHaveBeenCalledWith({ full_name: "Alice Updated" });
    });
    await waitFor(() => {
      expect(screen.getByText(/updated successfully/i)).toBeInTheDocument();
    });
  });

  it("renders avatar with src when avatar_url is present (AC-8)", async () => {
    mockFetchMe.mockResolvedValue(baseProfile);
    renderProfilePage();
    await waitFor(() => {
      expect(screen.getByText("My Profile")).toBeInTheDocument();
    });
    const avatar = screen.getByRole("img", { name: "Alice Example" });
    expect(avatar).toHaveAttribute("src", "https://avatars.example.com/alice.png");
  });

  it("renders initials fallback when avatar_url is null (AC-8)", async () => {
    mockFetchMe.mockResolvedValue({ ...baseProfile, avatar_url: null });
    renderProfilePage();
    await waitFor(() => {
      expect(screen.getByText("AE")).toBeInTheDocument();
    });
  });
});
