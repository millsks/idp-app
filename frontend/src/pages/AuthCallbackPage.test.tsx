import { describe, it, expect, vi, type Mock } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { ThemeProvider } from "@mui/material";

import { AuthCallbackPage } from "./AuthCallbackPage";
import { theme } from "../theme";

// Capture the destination of navigate() calls.
function LocationDisplay() {
  const location = useLocation();
  return <div data-testid="location">{location.pathname + location.search}</div>;
}

// Provide a controllable mock for AuthContext.
const mockLogin = vi.fn<[string], Promise<void>>();

vi.mock("../hooks/useAuth", () => ({
  useAuth: () => ({ login: mockLogin }),
}));

function renderCallbackPage(search: string) {
  return render(
    <MemoryRouter initialEntries={[`/auth/callback${search}`]}>
      <ThemeProvider theme={theme}>
        <Routes>
          <Route path="/auth/callback" element={<AuthCallbackPage />} />
          <Route path="*" element={<LocationDisplay />} />
        </Routes>
      </ThemeProvider>
    </MemoryRouter>,
  );
}

describe("AuthCallbackPage", () => {
  it("shows a loading spinner while processing (AC-3)", () => {
    mockLogin.mockReturnValue(new Promise(() => undefined)); // never resolves
    renderCallbackPage("?exchange_code=abc123");
    expect(screen.getByRole("progressbar")).toBeInTheDocument();
  });

  it("calls login() with the exchange code and redirects to / on success (AC-3)", async () => {
    (mockLogin as Mock).mockResolvedValue(undefined);
    renderCallbackPage("?exchange_code=abc123");

    await waitFor(() => {
      expect(screen.getByTestId("location")).toHaveTextContent("/");
    });
    expect(mockLogin).toHaveBeenCalledWith("abc123");
  });

  it("respects ?redirect= param and navigates there on success (AC-3)", async () => {
    (mockLogin as Mock).mockResolvedValue(undefined);
    renderCallbackPage("?exchange_code=abc123&redirect=%2Fprofile");

    await waitFor(() => {
      expect(screen.getByTestId("location")).toHaveTextContent("/profile");
    });
  });

  it("redirects to /login?error=auth_failed when exchange_code is missing (AC-4)", async () => {
    renderCallbackPage("");

    await waitFor(() => {
      expect(screen.getByTestId("location")).toHaveTextContent("/login?error=auth_failed");
    });
  });

  it("redirects to /login?error=auth_failed when login() rejects (AC-4)", async () => {
    (mockLogin as Mock).mockRejectedValue(new Error("expired"));
    renderCallbackPage("?exchange_code=expired_code");

    await waitFor(() => {
      expect(screen.getByTestId("location")).toHaveTextContent("/login?error=auth_failed");
    });
  });
});
