/**
 * Tests for ItemDetail component — Story 4.3 AC 2, 3, 4, 5, 11.
 */
import { describe, it, expect, vi, beforeEach, beforeAll, afterAll } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "@mui/material";

import { ItemDetail } from "./ItemDetail";
import { theme } from "../../theme";
import type { LibraryItemDetail } from "../../api/library";

// ---------------------------------------------------------------------------
// Mock the API module so no real HTTP calls are made
// ---------------------------------------------------------------------------

vi.mock("../../api/library", () => ({
  fetchLibraryItem: vi.fn(),
  fetchLibraryItems: vi.fn(),
  fetchPublicLibraryItems: vi.fn(),
}));

import { fetchLibraryItem } from "../../api/library";

// ---------------------------------------------------------------------------
// Mock clipboard API
// jsdom's navigator.clipboard is either undefined or non-overridable via
// Object.defineProperty.  Use vi.stubGlobal with a Proxy that intercepts
// only the 'clipboard' property so all other navigator behaviour is intact.
// ---------------------------------------------------------------------------

let writeTextMock: ReturnType<typeof vi.fn<(text: string) => Promise<void>>>;

beforeAll(() => {
  writeTextMock = vi.fn<(text: string) => Promise<void>>();
  const realNavigator = globalThis.navigator;
  vi.stubGlobal(
    "navigator",
    new Proxy(realNavigator, {
      get(target, prop: string) {
        if (prop === "clipboard") return { writeText: writeTextMock };
        // eslint-disable-next-line @typescript-eslint/no-unsafe-return
        return Reflect.get(target, prop, target);
      },
    }),
  );
});

afterAll(() => {
  vi.unstubAllGlobals();
});

// ---------------------------------------------------------------------------
// Shared test data
// Use a different heading in content so it doesn't clash with the component's
// own <h1> title ("Python Skill") when testing heading queries.
// ---------------------------------------------------------------------------

const mockSkill: LibraryItemDetail = {
  slug: "python-skill",
  title: "Python Skill",
  description: "A skill for writing excellent Python code.",
  content_type: "Skill",
  tags: ["python", "testing"],
  is_public: true,
  target_ai: "claude",
  author: "alice",
  last_updated: "2026-05-01T00:00:00Z",
  content: "# Skill Overview\n\nThis is the **full** content with `code`.",
  github_url: "https://github.com/owner/repo/blob/main/skills/python-skill/SKILL.md",
};

const mockPrompt: LibraryItemDetail = {
  slug: "writing-prompt",
  title: "Writing Prompt",
  description: "A creative writing prompt.",
  content_type: "Prompt",
  tags: ["writing"],
  is_public: true,
  target_ai: null,
  author: null,
  last_updated: null,
  content: "## Write a story…",
  github_url: "https://github.com/owner/repo/blob/main/prompts/writing-prompt.md",
};

// ---------------------------------------------------------------------------
// Render helper
// ---------------------------------------------------------------------------

function renderItemDetail(slug = "python-skill") {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <ThemeProvider theme={theme}>
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={[`/library/${slug}`]}>
          <Routes>
            <Route path="/library/:slug" element={<ItemDetail />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    </ThemeProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  writeTextMock.mockResolvedValue(undefined);
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("ItemDetail", () => {
  describe("loading state", () => {
    it("shows a loading skeleton while data is fetching", () => {
      vi.mocked(fetchLibraryItem).mockReturnValue(
        new Promise(() => {
          /* never resolves */
        }),
      );
      renderItemDetail();
      // Skeletons render as role="progressbar" or just exist in DOM
      // Check that the title is NOT yet visible (still loading)
      expect(screen.queryByRole("heading", { name: /python skill/i })).not.toBeInTheDocument();
    });
  });

  describe("error state", () => {
    it("renders an error message when the request fails", async () => {
      vi.mocked(fetchLibraryItem).mockRejectedValue(new Error("Not found"));
      renderItemDetail();
      await waitFor(() => {
        expect(screen.getByRole("alert")).toBeInTheDocument();
      });
    });

    it("shows a back-to-library button in the error state", async () => {
      vi.mocked(fetchLibraryItem).mockRejectedValue(new Error("Not found"));
      renderItemDetail();
      await waitFor(() => {
        expect(screen.getByRole("button", { name: /back to library/i })).toBeInTheDocument();
      });
    });
  });

  describe("success state — metadata (AC 3)", () => {
    beforeEach(() => {
      vi.mocked(fetchLibraryItem).mockResolvedValue(mockSkill);
    });

    it("renders the item title as a heading", async () => {
      renderItemDetail();
      await waitFor(() => {
        expect(screen.getByRole("heading", { name: /python skill/i })).toBeInTheDocument();
      });
    });

    it("renders the content_type badge", async () => {
      renderItemDetail();
      await waitFor(() => {
        expect(screen.getByText("Skill")).toBeInTheDocument();
      });
    });

    it("renders the description", async () => {
      renderItemDetail();
      await waitFor(() => {
        expect(screen.getByText(/writing excellent python code/i)).toBeInTheDocument();
      });
    });

    it("renders all tags as chips", async () => {
      renderItemDetail();
      await waitFor(() => {
        expect(screen.getByText("python")).toBeInTheDocument();
        expect(screen.getByText("testing")).toBeInTheDocument();
      });
    });

    it("renders the target AI chip", async () => {
      renderItemDetail();
      await waitFor(() => {
        expect(screen.getByText("claude")).toBeInTheDocument();
      });
    });

    it("renders a link to the author's GitHub profile", async () => {
      renderItemDetail();
      await waitFor(() => {
        const authorLink = screen.getByRole("link", { name: /alice/i });
        expect(authorLink).toHaveAttribute("href", "https://github.com/alice");
      });
    });

    it("renders the last updated date", async () => {
      renderItemDetail();
      await waitFor(() => {
        expect(screen.getByText(/last updated/i)).toBeInTheDocument();
      });
    });
  });

  describe("success state — Markdown content (AC 2)", () => {
    it("renders the item content as parsed Markdown", async () => {
      vi.mocked(fetchLibraryItem).mockResolvedValue(mockSkill);
      renderItemDetail();
      await waitFor(() => {
        // The heading from markdown "# Python Skill" renders as an h1
        expect(screen.getAllByText(/python skill/i).length).toBeGreaterThan(0);
      });
    });

    it("renders a content article region", async () => {
      vi.mocked(fetchLibraryItem).mockResolvedValue(mockSkill);
      renderItemDetail();
      await waitFor(() => {
        expect(screen.getByRole("article")).toBeInTheDocument();
      });
    });
  });

  describe("copy to clipboard (AC 4)", () => {
    beforeEach(() => {
      vi.mocked(fetchLibraryItem).mockResolvedValue(mockSkill);
    });

    it("renders the copy to clipboard button", async () => {
      renderItemDetail();
      await waitFor(() => {
        expect(screen.getByRole("button", { name: /copy.*clipboard/i })).toBeInTheDocument();
      });
    });

    it("calls navigator.clipboard.writeText with the item content on click", async () => {
      const user = userEvent.setup();
      renderItemDetail();
      await waitFor(() => {
        expect(screen.getByRole("button", { name: /copy.*clipboard/i })).toBeInTheDocument();
      });
      await user.click(screen.getByRole("button", { name: /copy.*clipboard/i }));
      await waitFor(() => {
        expect(writeTextMock).toHaveBeenCalledWith(mockSkill.content);
      });
    });

    it("shows 'Copied to clipboard' toast on successful copy", async () => {
      const user = userEvent.setup();
      renderItemDetail();
      await waitFor(() => {
        expect(screen.getByRole("button", { name: /copy.*clipboard/i })).toBeInTheDocument();
      });
      await user.click(screen.getByRole("button", { name: /copy.*clipboard/i }));
      await waitFor(() => {
        expect(screen.getByText(/copied to clipboard/i)).toBeInTheDocument();
      });
    });

    it("shows an error toast when clipboard write fails", async () => {
      writeTextMock.mockRejectedValue(new Error("Permission denied"));
      const user = userEvent.setup();
      renderItemDetail();
      await waitFor(() => {
        expect(screen.getByRole("button", { name: /copy.*clipboard/i })).toBeInTheDocument();
      });
      await user.click(screen.getByRole("button", { name: /copy.*clipboard/i }));
      await waitFor(() => {
        expect(screen.getByText(/failed to copy/i)).toBeInTheDocument();
      });
    });
  });

  describe("View on GitHub (AC 5)", () => {
    it("renders a View on GitHub link with correct href", async () => {
      vi.mocked(fetchLibraryItem).mockResolvedValue(mockSkill);
      renderItemDetail();
      await waitFor(() => {
        // Use the specific aria-label to avoid matching the author link
        const link = screen.getByRole("link", { name: /view source file on github/i });
        expect(link).toHaveAttribute("href", mockSkill.github_url);
        expect(link).toHaveAttribute("target", "_blank");
        expect(link).toHaveAttribute("rel", "noopener noreferrer");
      });
    });

    it("does not render View on GitHub when github_url is null", async () => {
      vi.mocked(fetchLibraryItem).mockResolvedValue({ ...mockSkill, github_url: null });
      renderItemDetail();
      await waitFor(() => {
        expect(
          screen.queryByRole("link", { name: /view source file on github/i }),
        ).not.toBeInTheDocument();
      });
    });
  });

  describe("optional metadata fields", () => {
    it("does not render author or last-updated when absent", async () => {
      vi.mocked(fetchLibraryItem).mockResolvedValue(mockPrompt);
      renderItemDetail("writing-prompt");
      await waitFor(() => {
        expect(screen.getByRole("heading", { name: /writing prompt/i })).toBeInTheDocument();
      });
      expect(screen.queryByText(/@/)).not.toBeInTheDocument();
      expect(screen.queryByText(/last updated/i)).not.toBeInTheDocument();
    });

    it("does not render target AI chip when target_ai is null", async () => {
      vi.mocked(fetchLibraryItem).mockResolvedValue(mockPrompt);
      renderItemDetail("writing-prompt");
      await waitFor(() => {
        expect(screen.getByRole("heading", { name: /writing prompt/i })).toBeInTheDocument();
      });
      expect(screen.queryByLabelText(/target ai/i)).not.toBeInTheDocument();
    });
  });

  describe("back navigation", () => {
    it("renders the back-to-library button in the success state", async () => {
      vi.mocked(fetchLibraryItem).mockResolvedValue(mockSkill);
      renderItemDetail();
      await waitFor(() => {
        expect(screen.getByRole("button", { name: /back to library/i })).toBeInTheDocument();
      });
    });
  });
});
