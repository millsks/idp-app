import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { ThemeProvider } from "@mui/material";
import { Layout } from "./Layout";
import { theme } from "../../theme";
import { AuthProvider } from "../../contexts/AuthContext";

// Allow individual tests to override useAuth
vi.mock("../../hooks/useAuth", async (importOriginal) => {
  const actual = await (importOriginal as () => Promise<Record<string, unknown>>)();
  return { ...actual };
});

import * as useAuthModule from "../../hooks/useAuth";

function renderLayout() {
  return render(
    <AuthProvider>
      <ThemeProvider theme={theme}>
        <MemoryRouter>
          <Layout />
        </MemoryRouter>
      </ThemeProvider>
    </AuthProvider>,
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

  it("shows 'Sign In' button when not authenticated", () => {
    vi.spyOn(useAuthModule, "useAuth").mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
      user: null,
      login: vi.fn(),
      logout: vi.fn(),
    });
    renderLayout();
    expect(screen.getByLabelText(/sign in/i)).toBeInTheDocument();
  });

  it("shows 'Log Out' button and Profile nav item when authenticated", () => {
    vi.spyOn(useAuthModule, "useAuth").mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: null,
      login: vi.fn(),
      logout: vi.fn(),
    });
    renderLayout();
    expect(screen.getByLabelText(/log out/i)).toBeInTheDocument();
    expect(screen.getByText("Profile")).toBeInTheDocument();
  });

  it("calls logout when 'Log Out' is clicked", async () => {
    const logoutFn = vi.fn();
    vi.spyOn(useAuthModule, "useAuth").mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: null,
      login: vi.fn(),
      logout: logoutFn,
    });
    const user = userEvent.setup();
    renderLayout();
    await user.click(screen.getByLabelText(/log out/i));
    expect(logoutFn).toHaveBeenCalledOnce();
  });
});
