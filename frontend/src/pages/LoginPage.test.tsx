import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { ThemeProvider } from "@mui/material";

import { LoginPage } from "./LoginPage";
import { theme } from "../theme";

function renderLoginPage(search = "") {
  return render(
    <MemoryRouter initialEntries={[`/login${search}`]}>
      <Routes>
        <Route
          path="/login"
          element={
            <ThemeProvider theme={theme}>
              <LoginPage />
            </ThemeProvider>
          }
        />
      </Routes>
    </MemoryRouter>,
  );
}

describe("LoginPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the 'Continue with GitHub' button (AC-9)", () => {
    renderLoginPage();
    expect(screen.getByRole("button", { name: /continue with github/i })).toBeInTheDocument();
  });

  it("renders the 'Continue with Google' button (AC-9)", () => {
    renderLoginPage();
    expect(screen.getByRole("button", { name: /continue with google/i })).toBeInTheDocument();
  });

  it("navigates to /api/v1/auth/github when GitHub button is clicked (AC-10)", async () => {
    const user = userEvent.setup();
    renderLoginPage();

    const hrefSetter = vi.fn();
    const mockLoc = Object.defineProperty(Object.create(null) as Location, "href", {
      set: hrefSetter,
      get: () => "",
      configurable: true,
    });
    vi.spyOn(globalThis, "location", "get").mockReturnValue(mockLoc);

    await user.click(screen.getByRole("button", { name: /continue with github/i }));

    expect(hrefSetter).toHaveBeenCalledWith("/api/v1/auth/github");
  });

  it("shows no error alert when there is no error param", () => {
    renderLoginPage();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("shows auth_failed error message when ?error=auth_failed (AC-4)", () => {
    renderLoginPage("?error=auth_failed");
    expect(screen.getByRole("alert")).toHaveTextContent(/authentication failed/i);
  });

  it("shows provider_denied error message when ?error=provider_denied", () => {
    renderLoginPage("?error=provider_denied");
    expect(screen.getByRole("alert")).toHaveTextContent(/access was denied/i);
  });

  it("shows invalid_state error message when ?error=invalid_state", () => {
    renderLoginPage("?error=invalid_state");
    expect(screen.getByRole("alert")).toHaveTextContent(/invalid session state/i);
  });
});
