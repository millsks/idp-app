import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { ThemeProvider } from "@mui/material";

import { HomePage } from "./HomePage";
import { theme } from "../theme";

function renderHomePage() {
  return render(
    <MemoryRouter>
      <ThemeProvider theme={theme}>
        <HomePage />
      </ThemeProvider>
    </MemoryRouter>,
  );
}

describe("HomePage", () => {
  it("renders the main headline (AC-2)", () => {
    renderHomePage();
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      "The Integrated Developer Portal",
    );
  });

  it("renders all five capability pillar cards (AC-3)", () => {
    renderHomePage();
    expect(screen.getByText("AI Skills & Prompts Library")).toBeInTheDocument();
    expect(screen.getByText("Software Marketplace")).toBeInTheDocument();
    expect(screen.getByText("Developer Utilities")).toBeInTheDocument();
    expect(screen.getByText("Application Accelerators")).toBeInTheDocument();
    expect(screen.getByText("Vulnerability Library")).toBeInTheDocument();
  });

  it("marks four non-MVP1 pillars as Coming Soon (AC-4)", () => {
    renderHomePage();
    const comingSoonChips = screen.getAllByText("Coming Soon");
    expect(comingSoonChips).toHaveLength(4);
  });

  it("does not mark AI Skills & Prompts Library as Coming Soon (AC-4)", () => {
    renderHomePage();
    // Only 4 chips, none adjacent to the live pillar title
    const libraryCard = screen
      .getByText("AI Skills & Prompts Library")
      .closest('[aria-label*="available now"]');
    expect(libraryCard).toBeInTheDocument();
  });

  it("renders Sign In CTA linking to /login (AC-5)", () => {
    renderHomePage();
    const signInBtn = screen.getByRole("link", { name: /sign in/i });
    expect(signInBtn).toHaveAttribute("href", "/login");
  });

  it("renders GitHub repository link (AC-6)", () => {
    renderHomePage();
    const ghLink = screen.getByRole("link", {
      name: /open source on github/i,
    });
    expect(ghLink).toHaveAttribute("href", "https://github.com/millsks/idp-app");
    expect(ghLink).toHaveAttribute("target", "_blank");
    expect(ghLink).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("does not render an unsolicited auth modal or login prompt (AC-7)", () => {
    renderHomePage();
    // No dialog/modal role present on initial render
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("supporting copy describes the portal purpose (AC-2)", () => {
    renderHomePage();
    expect(screen.getByText(/community-built, open-source portal/i)).toBeInTheDocument();
  });
});
