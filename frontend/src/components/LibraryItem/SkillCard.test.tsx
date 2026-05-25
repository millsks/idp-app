/**
 * Tests for the SkillCard component — Story 4.2 AC 2.
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { ThemeProvider } from "@mui/material";

import { SkillCard } from "./SkillCard";
import { theme } from "../../theme";
import type { LibraryItem } from "../../api/library";

const baseItem: LibraryItem = {
  slug: "python-skill",
  title: "Python Skill",
  description: "A skill for writing excellent Python code.",
  content_type: "Skill",
  tags: ["python", "testing"],
  is_public: true,
  target_ai: "claude",
  author: "alice",
  last_updated: "2026-05-01T00:00:00Z",
};

function renderCard(item: LibraryItem = baseItem) {
  return render(
    <ThemeProvider theme={theme}>
      <MemoryRouter>
        <SkillCard item={item} />
      </MemoryRouter>
    </ThemeProvider>,
  );
}

describe("SkillCard", () => {
  it("AC 2: renders the item title", () => {
    renderCard();
    expect(screen.getByRole("heading", { name: /python skill/i })).toBeInTheDocument();
  });

  it("AC 2: renders the description snippet", () => {
    renderCard();
    expect(screen.getByText(/writing excellent python code/i)).toBeInTheDocument();
  });

  it("AC 2: renders the content_type badge", () => {
    renderCard();
    expect(screen.getByText("Skill")).toBeInTheDocument();
  });

  it("AC 2: renders tags as chips", () => {
    renderCard();
    expect(screen.getByText("python")).toBeInTheDocument();
    expect(screen.getByText("testing")).toBeInTheDocument();
  });

  it("AC 2: renders target AI chip when present", () => {
    renderCard();
    expect(screen.getByText("claude")).toBeInTheDocument();
  });

  it("renders Prompt badge for Prompt content type", () => {
    renderCard({ ...baseItem, content_type: "Prompt" });
    expect(screen.getByText("Prompt")).toBeInTheDocument();
  });

  it("does not render target AI chip when target_ai is null", () => {
    renderCard({ ...baseItem, target_ai: null });
    // No chip labelled 'claude'
    expect(screen.queryByText("claude")).not.toBeInTheDocument();
  });

  it("renders fallback text when description is empty", () => {
    renderCard({ ...baseItem, description: "" });
    expect(screen.getByText(/no description available/i)).toBeInTheDocument();
  });

  it("does not render tags section when tags array is empty", () => {
    renderCard({ ...baseItem, tags: [] });
    expect(screen.queryByLabelText("Tags")).not.toBeInTheDocument();
  });
});
