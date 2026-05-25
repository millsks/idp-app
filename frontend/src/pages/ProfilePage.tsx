/**
 * ProfilePage — authenticated user's own profile page.
 *
 * Story 3.1 ACs: 7–13
 */
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  Avatar,
  Box,
  Button,
  Chip,
  CircularProgress,
  Divider,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import GitHubIcon from "@mui/icons-material/GitHub";
import GoogleIcon from "@mui/icons-material/Google";

import { QUERY_KEYS } from "../api/queryKeys";
import { fetchMe, patchMe } from "../api/users";
import { useAuth } from "../hooks/useAuth";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatMemberSince(isoDate: string): string {
  return new Intl.DateTimeFormat("en-US", { year: "numeric", month: "long" }).format(
    new Date(isoDate),
  );
}

function getInitials(name: string | null, email: string): string {
  if (name) {
    return name
      .split(" ")
      .map((w) => w[0])
      .slice(0, 2)
      .join("")
      .toUpperCase();
  }
  return email[0].toUpperCase();
}

function ProviderBadge({ provider }: { provider: string | null }) {
  if (provider === "github") {
    return (
      <Chip
        icon={<GitHubIcon fontSize="small" />}
        label="GitHub"
        size="small"
        variant="outlined"
        aria-label="OAuth provider: GitHub"
      />
    );
  }
  if (provider === "google") {
    return (
      <Chip
        icon={<GoogleIcon fontSize="small" />}
        label="Google"
        size="small"
        variant="outlined"
        aria-label="OAuth provider: Google"
      />
    );
  }
  return null;
}

// ---------------------------------------------------------------------------
// ProfilePage
// ---------------------------------------------------------------------------

export function ProfilePage() {
  const queryClient = useQueryClient();
  const { user: authUser } = useAuth();

  const { data: profile, isError } = useQuery({
    queryKey: QUERY_KEYS.currentUser(),
    queryFn: fetchMe,
    // Use the auth user as a partial initial hint — gives quick avatar/name render
    // before the full /users/me response arrives.
    ...(authUser
      ? {
          placeholderData: {
            id: authUser.id,
            email: authUser.email,
            full_name: authUser.full_name,
            avatar_url: authUser.avatar_url,
            oauth_provider: authUser.oauth_provider,
            is_active: true,
            is_superuser: false,
            created_at: new Date().toISOString(),
          },
        }
      : {}),
  });

  const [editedName, setEditedName] = useState<string>("");
  const [nameError, setNameError] = useState<string>("");
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Sync local edit state when query data first loads
  const currentDisplayName = profile?.full_name ?? "";
  useEffect(() => {
    if (profile) {
      setEditedName(profile.full_name ?? "");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profile?.email]); // key on email (stable identity) so edits aren't overwritten on refetch

  const mutation = useMutation({
    mutationFn: patchMe,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: QUERY_KEYS.currentUser() });
      setSaveSuccess(true);
      setTimeout(() => {
        setSaveSuccess(false);
      }, 3000);
    },
  });

  function handleSave() {
    const trimmed = editedName.trim();
    if (!trimmed) {
      setNameError("Display name must not be blank.");
      return;
    }
    setNameError("");
    setSaveSuccess(false);
    mutation.mutate({ full_name: trimmed });
  }

  // -------------------------------------------------------------------------
  // Loading / error states
  // -------------------------------------------------------------------------

  if (!profile) {
    if (isError) {
      return (
        <Alert severity="error" sx={{ mt: 4 }}>
          Failed to load your profile. Please refresh the page.
        </Alert>
      );
    }
    return (
      <Box sx={{ display: "flex", justifyContent: "center", mt: 8 }}>
        <CircularProgress aria-label="Loading profile" />
      </Box>
    );
  }

  const initials = getInitials(profile.full_name, profile.email);
  const memberSince = profile.created_at
    ? `Member since ${formatMemberSince(profile.created_at)}`
    : "";

  return (
    <Box sx={{ maxWidth: 600, mx: "auto", mt: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        My Profile
      </Typography>

      <Paper elevation={2} sx={{ p: 4 }}>
        <Stack spacing={3}>
          {/* Avatar + provider badge */}
          <Stack direction="row" spacing={2} alignItems="center">
            <Avatar
              src={profile.avatar_url ?? undefined}
              alt={profile.full_name ?? profile.email}
              sx={{ width: 80, height: 80, fontSize: "2rem" }}
            >
              {initials}
            </Avatar>
            <Box>
              <Typography variant="h6">{profile.full_name ?? profile.email}</Typography>
              <Stack direction="row" spacing={1} mt={0.5} alignItems="center">
                <ProviderBadge provider={profile.oauth_provider} />
                {memberSince && (
                  <Typography variant="body2" color="text.secondary">
                    {memberSince}
                  </Typography>
                )}
              </Stack>
            </Box>
          </Stack>

          <Divider />

          {/* Email — read-only */}
          <Box>
            <TextField
              label="Email address"
              value={profile.email}
              fullWidth
              slotProps={{ input: { readOnly: true } }}
              helperText="Your email address is managed by your OAuth provider and cannot be changed here."
              aria-label="Email address (read-only)"
            />
          </Box>

          {/* Display name — editable */}
          <Box>
            <TextField
              label="Display name"
              value={editedName}
              onChange={(e) => {
                setEditedName(e.target.value);
                if (nameError) setNameError("");
                if (saveSuccess) setSaveSuccess(false);
              }}
              fullWidth
              error={Boolean(nameError) || mutation.isError}
              helperText={
                nameError || (mutation.isError ? "Failed to save. Please try again." : undefined)
              }
              aria-label="Display name"
            />
          </Box>

          {saveSuccess && (
            <Alert
              severity="success"
              onClose={() => {
                setSaveSuccess(false);
              }}
            >
              Display name updated successfully.
            </Alert>
          )}

          {/* Save button */}
          <Box sx={{ display: "flex", justifyContent: "flex-end" }}>
            <Button
              variant="contained"
              onClick={handleSave}
              disabled={mutation.isPending || editedName.trim() === currentDisplayName}
              aria-label="Save display name"
            >
              {mutation.isPending ? "Saving…" : "Save"}
            </Button>
          </Box>
        </Stack>
      </Paper>
    </Box>
  );
}
