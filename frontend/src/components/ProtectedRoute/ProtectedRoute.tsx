/**
 * ProtectedRoute — wraps React Router v7 <Route> elements.
 *
 * - While auth is loading: renders a centered spinner.
 * - Unauthenticated: redirects to /login?redirect={current pathname}.
 * - Authenticated: renders <Outlet /> (child routes).
 */
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { Box, CircularProgress } from "@mui/material";
import { useAuth } from "../../hooks/useAuth";

export function ProtectedRoute() {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <CircularProgress aria-label="Loading authentication state" />
      </Box>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to={`/login?redirect=${encodeURIComponent(location.pathname)}`} replace />;
  }

  return <Outlet />;
}
