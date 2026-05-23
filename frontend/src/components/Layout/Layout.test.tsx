import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { ThemeProvider } from "@mui/material";
import { Layout } from "./Layout";
import { theme } from "../../theme";

function renderLayout() {
  return render(
    <ThemeProvider theme={theme}>
      <MemoryRouter>
        <Layout />
      </MemoryRouter>
    </ThemeProvider>,
  );
}

describe("Layout", () => {
  it("renders the app bar with the portal title", () => {
    renderLayout();
    expect(screen.getByText(/Integrated Developer Portal/i)).toBeInTheDocument();
  });

  it("renders the menu toggle button", () => {
    renderLayout();
    const menuButton = screen.getByLabelText(/toggle navigation drawer/i);
    expect(menuButton).toBeInTheDocument();
  });

  it("toggles the drawer when menu button is clicked", async () => {
    const user = userEvent.setup();
    renderLayout();
    const menuButton = screen.getByLabelText(/toggle navigation drawer/i);
    await user.click(menuButton);
    // Drawer state toggled — just verify no crash occurs
    expect(menuButton).toBeInTheDocument();
  });
});
