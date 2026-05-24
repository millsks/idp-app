/**
 * AuthCallbackPage — handles the OAuth redirect from the backend.
 *
 * Mounted at /auth/callback.
 * Reads `?exchange_code=` from the URL, calls AuthContext.login(), then
 * redirects to the original intended route (`?redirect=` param) or home (/).
 * On any failure redirects to /login?error=auth_failed (AC-4).
 */
import { useEffect, useRef } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Box, CircularProgress, Typography } from "@mui/material";
import { useAuth } from "../hooks/useAuth";

export function AuthCallbackPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  // Guard against StrictMode double-invoke
  const calledRef = useRef(false);

  useEffect(() => {
    if (calledRef.current) return;
    calledRef.current = true;

    const exchangeCode = searchParams.get("exchange_code");
    const redirectTo = searchParams.get("redirect") ?? "/";

    if (!exchangeCode) {
      void navigate("/login?error=auth_failed", { replace: true });
      return;
    }

    login(exchangeCode)
      .then(() => navigate(redirectTo, { replace: true }))
      .catch(() => navigate("/login?error=auth_failed", { replace: true }));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <Box
      display="flex"
      flexDirection="column"
      alignItems="center"
      justifyContent="center"
      minHeight="60vh"
      gap={2}
    >
      <CircularProgress />
      <Typography color="text.secondary">Completing sign-in…</Typography>
    </Box>
  );
}
