/**
 * LibraryPage — Dedicated public page for the AI Skills & Prompts Library.
 *
 * Public visitors see the preview strip (up to 6 public items) with a
 * "Sign in to browse the full library" CTA.
 * Authenticated browsing, search, and full content will be layered onto
 * this page in Stories 4.2 and 4.3.
 */
import { Box, Button, Container, Typography } from "@mui/material";
import { Link as RouterLink } from "react-router-dom";
import { PublicPreviewStrip } from "../components/LandingPreview/PublicPreviewStrip";
import { useAuth } from "../hooks/useAuth";

export function LibraryPage() {
  const { isAuthenticated } = useAuth();

  return (
    <Container maxWidth="lg" disableGutters>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" fontWeight={700} gutterBottom>
          AI Skills &amp; Prompts Library
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          A curated collection of AI skills and prompt templates — ready to drop into any AI
          assistant. Browse the public preview below
          {isAuthenticated ? "." : ", or sign in to access the full library."}
        </Typography>

        {!isAuthenticated && (
          <Button
            component={RouterLink}
            to="/login"
            variant="contained"
            size="large"
            aria-label="Sign in to browse the full library"
            sx={{ mb: 4 }}
          >
            Sign In to Browse Full Library
          </Button>
        )}
      </Box>

      <PublicPreviewStrip />
    </Container>
  );
}
