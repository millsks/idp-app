import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { ThemeProvider } from "@mui/material";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { LibraryPage } from "./LibraryPage";
import { theme } from "../theme";

// Prevent PublicPreviewStrip from making real network calls.
vi.mock("../api/client", () => ({
  apiClient: {
    get: vi.fn().mockResolvedValue({ data: { items: [], total: 0, page: 1, size: 0, pages: 0 } }),
  },
}));

// Default: unauthenticated
vi.mock("../hooks/useAuth", () => ({
  useAuth: () => ({ isAuthenticated: false, user: null, isLoading: false }),
}));

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

describe("LibraryPage", () => {
  it("renders the page heading", () => {
    renderLibraryPage();
    expect(
      screen.getByRole("heading", { level: 1, name: /ai skills & prompts library/i }),
    ).toBeInTheDocument();
  });

  it("renders Sign In CTA linking to /login for unauthenticated visitors", () => {
    renderLibraryPage();
    const cta = screen.getByRole("link", { name: /sign in to browse/i });
    expect(cta).toHaveAttribute("href", "/login");
  });

  it("renders without error when the preview cache is empty", () => {
    renderLibraryPage();
    // PublicPreviewStrip returns null on empty data — page still renders correctly
    expect(screen.getByRole("heading", { level: 1 })).toBeInTheDocument();
  });

  it("describes the library to visitors", () => {
    renderLibraryPage();
    expect(screen.getByText(/browse the public preview below/i)).toBeInTheDocument();
  });
});
