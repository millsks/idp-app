import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { ThemeProvider } from "@mui/material";

import { ProtectedRoute } from "./ProtectedRoute";
import { theme } from "../../theme";

function LocationDisplay() {
  const location = useLocation();
  return <div data-testid="location">{location.pathname + location.search}</div>;
}

interface MockAuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
}

const mockUseAuth = vi.fn<[], MockAuthState>();

vi.mock("../../hooks/useAuth", () => ({
  useAuth: (): MockAuthState => mockUseAuth() as MockAuthState,
}));

function renderWithRoute(initialPath: string) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <ThemeProvider theme={theme}>
        <Routes>
          <Route element={<ProtectedRoute />}>
            <Route path="/protected" element={<div>Protected content</div>} />
          </Route>
          <Route path="*" element={<LocationDisplay />} />
        </Routes>
      </ThemeProvider>
    </MemoryRouter>,
  );
}

describe("ProtectedRoute", () => {
  it("renders child route when authenticated (AC-5)", () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: true, isLoading: false });
    renderWithRoute("/protected");
    expect(screen.getByText("Protected content")).toBeInTheDocument();
  });

  it("redirects to /login?redirect=<path> when unauthenticated (AC-5)", () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false, isLoading: false });
    renderWithRoute("/protected");
    expect(screen.getByTestId("location")).toHaveTextContent("/login?redirect=%2Fprotected");
  });

  it("renders a loading spinner while isLoading is true (AC-5)", () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false, isLoading: true });
    renderWithRoute("/protected");
    expect(screen.getByRole("progressbar")).toBeInTheDocument();
    expect(screen.queryByText("Protected content")).not.toBeInTheDocument();
  });
});
