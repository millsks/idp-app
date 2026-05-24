/**
 * LoginPage — OAuth provider selection.
 *
 * Renders "Continue with GitHub" and "Continue with Google" buttons.
 * No username/password form (AC-9).
 * Buttons use full-page navigation (window.location.href) so the browser
 * leaves the SPA and follows the OAuth redirect (AC-10, Dev Notes).
 */
import { Box, Button, Container, Paper, Stack, Typography, Alert } from "@mui/material";
import GitHubIcon from "@mui/icons-material/GitHub";
import GoogleIcon from "@mui/icons-material/Google";
import { useSearchParams } from "react-router-dom";

function getErrorMessage(key: string): string {
  switch (key) {
    case "auth_failed":
      return "Authentication failed. Please try again.";
    case "invalid_state":
      return "Invalid session state. Please start the login flow again.";
    case "provider_denied":
      return "Access was denied by the provider. Please try again.";
    default:
      return "An unknown error occurred.";
  }
}

export function LoginPage() {
  const [searchParams] = useSearchParams();
  const errorKey = searchParams.get("error");
  const errorMessage = errorKey ? getErrorMessage(errorKey) : null;

  return (
    <Container maxWidth="xs" sx={{ mt: { xs: 6, md: 12 } }}>
      <Paper elevation={3} sx={{ p: 4 }}>
        <Stack spacing={3} alignItems="center">
          <Typography variant="h5" fontWeight={700}>
            Sign in
          </Typography>

          {errorMessage && (
            <Alert severity="error" sx={{ width: "100%" }}>
              {errorMessage}
            </Alert>
          )}

          <Box sx={{ width: "100%" }}>
            <Stack spacing={2}>
              <Button
                variant="contained"
                size="large"
                fullWidth
                startIcon={<GitHubIcon />}
                onClick={() => {
                  globalThis.location.href = "/api/v1/auth/github";
                }}
                aria-label="Continue with GitHub"
              >
                Continue with GitHub
              </Button>

              <Button
                variant="outlined"
                size="large"
                fullWidth
                startIcon={<GoogleIcon />}
                disabled
                aria-label="Continue with Google — coming soon"
              >
                Continue with Google
              </Button>
            </Stack>
          </Box>

          <Typography variant="caption" color="text.secondary" textAlign="center">
            Google login is coming soon.
          </Typography>
        </Stack>
      </Paper>
    </Container>
  );
}
