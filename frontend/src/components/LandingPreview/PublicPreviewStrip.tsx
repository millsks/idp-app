/**
 * PublicPreviewStrip — shows up to 6 public library items on the landing page.
 * Unauthenticated visitors see a card teaser; clicking opens a modal with a
 * "Sign in to view full content" CTA.  Full Markdown is never fetched here.
 */

import { useState } from "react";
import {
  Box,
  Button,
  Card,
  CardActionArea,
  CardContent,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid2,
  Stack,
  Typography,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { Link as RouterLink } from "react-router-dom";
import { apiClient } from "../../api/client";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface LibraryItem {
  slug: string;
  title: string;
  description: string;
  content_type: string;
  tags: string[];
  is_public: boolean;
  target_ai?: string | null;
  author?: string | null;
  last_updated?: string | null;
}

interface LibraryItemList {
  items: LibraryItem[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// ---------------------------------------------------------------------------
// Query
// ---------------------------------------------------------------------------

const PUBLIC_ITEMS_QUERY_KEY = ["library", "items", "public"] as const;
const MAX_PREVIEW_ITEMS = 6;

async function fetchPublicItems(): Promise<LibraryItemList> {
  const { data } = await apiClient.get<LibraryItemList>("/library/items/public");
  return data;
}

// ---------------------------------------------------------------------------
// Item Card
// ---------------------------------------------------------------------------

interface PreviewCardProps {
  item: LibraryItem;
  onSelect: (item: LibraryItem) => void;
}

function PreviewCard({ item, onSelect }: PreviewCardProps) {
  return (
    <Card sx={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <CardActionArea
        onClick={() => {
          onSelect(item);
        }}
        sx={{ flexGrow: 1, display: "flex", flexDirection: "column", alignItems: "flex-start" }}
        aria-label={`Preview ${item.title}`}
      >
        <CardContent sx={{ width: "100%" }}>
          <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
            <Chip
              label={item.content_type}
              size="small"
              color={item.content_type === "Skill" ? "primary" : "secondary"}
              aria-label={`Content type: ${item.content_type}`}
            />
          </Stack>

          <Typography variant="h6" gutterBottom>
            {item.title}
          </Typography>

          <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
            {item.description}
          </Typography>

          {item.tags.length > 0 && (
            <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
              {item.tags.map((tag) => (
                <Chip key={tag} label={tag} size="small" variant="outlined" />
              ))}
            </Stack>
          )}
        </CardContent>
      </CardActionArea>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Teaser Modal
// ---------------------------------------------------------------------------

interface TeaserModalProps {
  item: LibraryItem | null;
  onClose: () => void;
}

function TeaserModal({ item, onClose }: TeaserModalProps) {
  if (!item) return null;

  return (
    <Dialog open onClose={onClose} maxWidth="sm" fullWidth aria-labelledby="teaser-dialog-title">
      <DialogTitle id="teaser-dialog-title">{item.title}</DialogTitle>
      <DialogContent dividers>
        <Typography variant="body1">{item.description}</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
          Sign in to view the full content of this {item.content_type.toLowerCase()}.
        </Typography>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} color="inherit">
          Close
        </Button>
        <Button
          component={RouterLink}
          to="/login"
          variant="contained"
          color="primary"
          aria-label="Sign in to view full content"
        >
          Sign in to view full content
        </Button>
      </DialogActions>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// Public Preview Strip
// ---------------------------------------------------------------------------

export function PublicPreviewStrip() {
  const [selectedItem, setSelectedItem] = useState<LibraryItem | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: PUBLIC_ITEMS_QUERY_KEY,
    queryFn: fetchPublicItems,
  });

  // Hide the strip while loading
  if (isLoading) {
    return (
      <Box
        sx={{ display: "flex", justifyContent: "center", py: 4 }}
        aria-label="Loading library items"
      >
        <CircularProgress aria-label="Loading" />
      </Box>
    );
  }

  // On error or no items — show nothing (graceful hide), per AC5
  const items = data?.items.slice(0, MAX_PREVIEW_ITEMS) ?? [];
  if (isError || items.length === 0) {
    return null;
  }

  return (
    <Box component="section" aria-labelledby="preview-strip-heading" sx={{ mt: 6 }}>
      <Typography id="preview-strip-heading" variant="h5" fontWeight={700} gutterBottom>
        Explore the Library
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        A glimpse of the skills and prompts available to signed-in members.
      </Typography>

      <Grid2 container spacing={3}>
        {items.map((item) => (
          <Grid2 key={item.slug} size={{ xs: 12, sm: 6, md: 4 }}>
            <PreviewCard item={item} onSelect={setSelectedItem} />
          </Grid2>
        ))}
      </Grid2>

      <TeaserModal
        item={selectedItem}
        onClose={() => {
          setSelectedItem(null);
        }}
      />
    </Box>
  );
}
