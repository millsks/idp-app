import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "@mui/material";
import { CssBaseline } from "@mui/material";

import App from "./App";
import { theme } from "./theme";

function renderApp(initialPath = "/") {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <MemoryRouter initialEntries={[initialPath]}>
          <App />
        </MemoryRouter>
      </ThemeProvider>
    </QueryClientProvider>,
  );
}

describe("App", () => {
  it("renders the home page by default", () => {
    renderApp("/");
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      "The Integrated Developer Portal",
    );
  });

  it("redirects unknown paths to home", () => {
    renderApp("/this-route-does-not-exist");
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      "The Integrated Developer Portal",
    );
  });
});
