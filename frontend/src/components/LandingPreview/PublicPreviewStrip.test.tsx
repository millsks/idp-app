import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "@mui/material";

import { PublicPreviewStrip, type LibraryItem } from "./PublicPreviewStrip";
import { theme } from "../../theme";

// ---------------------------------------------------------------------------
// Mock apiClient
// ---------------------------------------------------------------------------

const mockApiGet = vi.hoisted(() => vi.fn());

vi.mock("../../api/client", () => ({
  apiClient: {
    get: mockApiGet,
  },
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeItem(overrides: Partial<LibraryItem> = {}): LibraryItem {
  return {
    slug: "test-skill",
    title: "Test Skill",
    description: "A test skill description.",
    content_type: "Skill",
    tags: ["testing"],
    is_public: true,
    ...overrides,
  };
}

function renderStrip() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <MemoryRouter>
          <PublicPreviewStrip />
        </MemoryRouter>
      </ThemeProvider>
    </QueryClientProvider>,
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("PublicPreviewStrip", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows nothing when the API returns an empty list (AC5)", async () => {
    mockApiGet.mockResolvedValueOnce({
      data: { items: [], total: 0, page: 1, size: 0, pages: 0 },
    });

    renderStrip();

    // Strip should not render section heading when empty
    await waitFor(() => {
      expect(screen.queryByText(/Explore the Library/i)).not.toBeInTheDocument();
    });
  });

  it("shows nothing on API error (AC5)", async () => {
    mockApiGet.mockRejectedValueOnce(new Error("Network error"));

    renderStrip();

    await waitFor(() => {
      expect(screen.queryByText(/Explore the Library/i)).not.toBeInTheDocument();
    });
  });

  it("renders up to 6 item cards when items exist (AC1)", async () => {
    const items = Array.from({ length: 8 }, (_, i) =>
      makeItem({ slug: `skill-${String(i)}`, title: `Skill ${String(i)}` }),
    );
    mockApiGet.mockResolvedValueOnce({
      data: { items, total: 8, page: 1, size: 8, pages: 1 },
    });

    renderStrip();

    await waitFor(() => {
      expect(screen.getByText(/Explore the Library/i)).toBeInTheDocument();
    });

    // Only 6 cards rendered
    const cards = screen.getAllByRole("button", { name: /Preview Skill/i });
    expect(cards).toHaveLength(6);
  });

  it("each card shows title, description, content_type chip, and tags (AC2)", async () => {
    mockApiGet.mockResolvedValueOnce({
      data: {
        items: [makeItem({ tags: ["python", "ai"] })],
        total: 1,
        page: 1,
        size: 1,
        pages: 1,
      },
    });

    renderStrip();

    await waitFor(() => {
      expect(screen.getByText("Test Skill")).toBeInTheDocument();
    });

    expect(screen.getByText("A test skill description.")).toBeInTheDocument();
    expect(screen.getByText("Skill")).toBeInTheDocument(); // content_type chip
    expect(screen.getByText("python")).toBeInTheDocument();
    expect(screen.getByText("ai")).toBeInTheDocument();
  });

  it("does not render full content field (AC3)", async () => {
    // The component should never display a 'content' div
    mockApiGet.mockResolvedValueOnce({
      data: {
        items: [makeItem()],
        total: 1,
        page: 1,
        size: 1,
        pages: 1,
      },
    });

    renderStrip();

    await waitFor(() => screen.getByText("Test Skill"));

    // No element with id/text "content"
    expect(screen.queryByText(/^content$/i)).not.toBeInTheDocument();
  });

  it("clicking a card shows title, description, and CTA modal (AC4)", async () => {
    mockApiGet.mockResolvedValueOnce({
      data: {
        items: [makeItem()],
        total: 1,
        page: 1,
        size: 1,
        pages: 1,
      },
    });

    renderStrip();

    await waitFor(() => screen.getByText("Test Skill"));

    const cardButton = screen.getByRole("button", { name: /Preview Test Skill/i });
    await userEvent.click(cardButton);

    // Modal shows title and description but NOT full content
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getAllByText("Test Skill").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("A test skill description.").length).toBeGreaterThanOrEqual(1);

    // CTA link to /login is shown
    const ctaLink = screen.getByRole("link", { name: /Sign in to view full content/i });
    expect(ctaLink).toBeInTheDocument();
    expect(ctaLink).toHaveAttribute("href", "/login");
  });

  it("modal does not show full content for unauthenticated users (AC4)", async () => {
    mockApiGet.mockResolvedValueOnce({
      data: {
        items: [makeItem()],
        total: 1,
        page: 1,
        size: 1,
        pages: 1,
      },
    });

    renderStrip();

    await waitFor(() => screen.getByText("Test Skill"));

    await userEvent.click(screen.getByRole("button", { name: /Preview Test Skill/i }));

    // Full Markdown content area should never appear
    expect(screen.queryByTestId("full-content")).not.toBeInTheDocument();
  });
});
