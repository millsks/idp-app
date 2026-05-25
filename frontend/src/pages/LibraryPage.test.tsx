import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { ThemeProvider } from "@mui/material";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { LibraryPage } from "./LibraryPage";
import { theme } from "../theme";
import type { LibraryItemList } from "../api/library";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

// useLibraryItems return value — override per test.
const mockUseLibraryItems = vi.fn();

vi.mock("../hooks/useLibraryItems", () => ({
  useLibraryItems: (filters: unknown) =>
    mockUseLibraryItems(filters) as { data: LibraryItemList | undefined; isLoading: boolean },
}));

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const emptyData: LibraryItemList = { items: [], total: 0, page: 1, size: 20, pages: 0 };

const twoItemsData: LibraryItemList = {
  items: [
    {
      slug: "python-skill",
      title: "Python Skill",
      description: "Write better Python.",
      content_type: "Skill",
      tags: ["python"],
      is_public: true,
      target_ai: "claude",
      author: "alice",
      last_updated: null,
    },
    {
      slug: "writing-prompt",
      title: "Writing Prompt",
      description: "Craft compelling stories.",
      content_type: "Prompt",
      tags: ["writing"],
      is_public: true,
      target_ai: "chatgpt",
      author: "bob",
      last_updated: null,
    },
  ],
  total: 2,
  page: 1,
  size: 20,
  pages: 1,
};

// ---------------------------------------------------------------------------
// Render helper
// ---------------------------------------------------------------------------

function renderLibraryPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ThemeProvider theme={theme}>
          <LibraryPage />
        </ThemeProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("LibraryPage", () => {
  it("AC 1: renders the page heading", () => {
    mockUseLibraryItems.mockReturnValue({ data: emptyData, isLoading: false });
    renderLibraryPage();
    expect(
      screen.getByRole("heading", { level: 1, name: /ai skills & prompts library/i }),
    ).toBeInTheDocument();
  });

  it("renders a search input", () => {
    mockUseLibraryItems.mockReturnValue({ data: emptyData, isLoading: false });
    renderLibraryPage();
    expect(screen.getByRole("textbox", { name: /search library/i })).toBeInTheDocument();
  });

  it("renders content type toggle buttons", () => {
    mockUseLibraryItems.mockReturnValue({ data: emptyData, isLoading: false });
    renderLibraryPage();
    expect(screen.getByRole("group", { name: /filter by content type/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /all types/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /skills only/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /prompts only/i })).toBeInTheDocument();
  });

  it("AC 2: renders SkillCard items when data is available", () => {
    mockUseLibraryItems.mockReturnValue({ data: twoItemsData, isLoading: false });
    renderLibraryPage();
    expect(screen.getByRole("heading", { name: /python skill/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /writing prompt/i })).toBeInTheDocument();
  });

  it("AC 5: renders 'No results found' empty state when data is empty", () => {
    mockUseLibraryItems.mockReturnValue({ data: emptyData, isLoading: false });
    renderLibraryPage();
    expect(screen.getByText(/no results found/i)).toBeInTheDocument();
  });

  it("shows loading skeletons while query is pending", () => {
    mockUseLibraryItems.mockReturnValue({ data: undefined, isLoading: true });
    renderLibraryPage();
    // Skeletons render — at least one rect element with aria role
    // We just verify the cards are NOT rendered and no 'No results found'
    expect(screen.queryByText(/no results found/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /python skill/i })).not.toBeInTheDocument();
  });

  it("shows result count when items are present", () => {
    mockUseLibraryItems.mockReturnValue({ data: twoItemsData, isLoading: false });
    renderLibraryPage();
    expect(screen.getByText(/2 results/i)).toBeInTheDocument();
  });

  it("AC 4: updates search input value when typed", async () => {
    mockUseLibraryItems.mockReturnValue({ data: emptyData, isLoading: false });
    const user = userEvent.setup({ delay: null });
    renderLibraryPage();
    const searchBox = screen.getByRole("textbox", { name: /search library/i });
    await user.type(searchBox, "python");
    expect(searchBox).toHaveValue("python");
  });

  it("AC 6: type filter toggles update the active button", async () => {
    mockUseLibraryItems.mockReturnValue({ data: emptyData, isLoading: false });
    const user = userEvent.setup({ delay: null });
    renderLibraryPage();
    const skillButton = screen.getByRole("button", { name: /skills only/i });
    await user.click(skillButton);
    expect(skillButton).toHaveAttribute("aria-pressed", "true");
  });

  it("AC 8: tag chips render and can be toggled", async () => {
    mockUseLibraryItems.mockReturnValue({ data: twoItemsData, isLoading: false });
    const user = userEvent.setup({ delay: null });
    renderLibraryPage();
    // Tags derived from items: 'python', 'writing'
    await waitFor(() => {
      expect(screen.getAllByText("python")[0]).toBeInTheDocument();
    });
    const pythonChip = screen.getAllByText("python")[0];
    await user.click(pythonChip);
    // After click the chip becomes aria-pressed=true (active)
    expect(pythonChip.closest("[aria-pressed]")).toHaveAttribute("aria-pressed", "true");
  });
});
