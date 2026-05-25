/**
 * ItemDetail — full detail page for a single library item.
 *
 * Route: /library/:slug  (Option A — dedicated route, deep-linkable, browser history works)
 *
 * AC 2: Renders full Markdown content with syntax highlighting
 * AC 3: Metadata: content_type badge, title, description, tags, target AI, author, last updated
 * AC 4: "Copy to clipboard" → Snackbar toast (auto-dismiss 3 s)
 * AC 5: "View on GitHub" → new tab to the server-computed source URL
 * AC 11: Keyboard-navigable; MUI components meet WCAG 2.1 AA contrast
 */
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import "highlight.js/styles/github.css";
import {
  Alert,
  Box,
  Button,
  Chip,
  Container,
  Divider,
  Skeleton,
  Snackbar,
  Stack,
  Typography,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import { useLibraryItem } from "../../hooks/useLibraryItem";

// ---------------------------------------------------------------------------
// Loading skeleton
// ---------------------------------------------------------------------------

function DetailSkeleton() {
  return (
    <Container maxWidth="lg">
      <Skeleton variant="text" width={120} height={36} sx={{ mb: 2 }} />
      <Skeleton variant="rectangular" height={48} sx={{ mb: 2 }} />
      <Skeleton variant="text" width="70%" sx={{ mb: 1 }} />
      <Skeleton variant="text" width="40%" sx={{ mb: 3 }} />
      <Skeleton variant="rectangular" height={400} />
    </Container>
  );
}

// ---------------------------------------------------------------------------
// Error state
// ---------------------------------------------------------------------------

interface ErrorStateProps {
  message?: string;
  onBack: () => void;
}

function ErrorState({ message = "Item not found.", onBack }: ErrorStateProps) {
  return (
    <Container maxWidth="lg">
      <Button
        startIcon={<ArrowBackIcon />}
        onClick={onBack}
        sx={{ mb: 2 }}
        aria-label="Back to library"
      >
        Back to Library
      </Button>
      <Alert severity="error">{message}</Alert>
    </Container>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function ItemDetail() {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();
  const { data: item, isLoading, isError } = useLibraryItem(slug ?? "");
  const [copySuccess, setCopySuccess] = useState(false);
  const [copyError, setCopyError] = useState(false);

  const handleBack = () => {
    void navigate("/library");
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(item?.content ?? "");
      setCopySuccess(true);
    } catch {
      setCopyError(true);
    }
  };

  if (isLoading) {
    return <DetailSkeleton />;
  }

  if (isError || !item) {
    return (
      <ErrorState
        message={
          isError
            ? "Could not load this item. It may not exist or a temporary error occurred."
            : "Item not found."
        }
        onBack={handleBack}
      />
    );
  }

  const contentTypeColor = item.content_type === "Skill" ? "primary" : "secondary";
  const lastUpdatedFormatted = (() => {
    if (!item.last_updated) return null;
    const d = new Date(item.last_updated);
    if (Number.isNaN(d.getTime())) return null;
    return d.toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });
  })();

  return (
    <Container maxWidth="lg">
      {/* Back navigation (AC 1) */}
      <Button
        startIcon={<ArrowBackIcon />}
        onClick={handleBack}
        sx={{ mb: 3 }}
        aria-label="Back to library"
      >
        Back to Library
      </Button>

      {/* Header: title + content_type badge + action buttons */}
      <Box sx={{ mb: 3 }}>
        <Stack
          direction={{ xs: "column", sm: "row" }}
          alignItems={{ xs: "flex-start", sm: "center" }}
          justifyContent="space-between"
          gap={2}
          sx={{ mb: 1.5 }}
        >
          {/* Title + badge */}
          <Stack direction="row" alignItems="center" gap={1.5} flexWrap="wrap">
            <Typography variant="h4" component="h1" fontWeight={700}>
              {item.title}
            </Typography>
            <Chip
              label={item.content_type}
              color={contentTypeColor}
              aria-label={`Content type: ${item.content_type}`}
            />
          </Stack>

          {/* Action buttons (AC 4, 5) */}
          <Stack direction="row" gap={1} flexShrink={0} flexWrap="wrap">
            <Button
              variant="outlined"
              startIcon={<ContentCopyIcon />}
              onClick={() => {
                void handleCopy();
              }}
              aria-label="Copy Markdown content to clipboard"
            >
              Copy to clipboard
            </Button>
            {item.github_url != null && (
              <Button
                component="a"
                variant="outlined"
                startIcon={<OpenInNewIcon />}
                href={item.github_url}
                target="_blank"
                rel="noopener noreferrer"
                aria-label="View source file on GitHub (opens in new tab)"
              >
                View on GitHub
              </Button>
            )}
          </Stack>
        </Stack>

        {/* Description (AC 3) */}
        {item.description && (
          <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
            {item.description}
          </Typography>
        )}

        {/* Target AI + tags (AC 3) */}
        {(item.target_ai != null || item.tags.length > 0) && (
          <Stack direction="row" flexWrap="wrap" gap={1} alignItems="center" sx={{ mb: 1.5 }}>
            {item.target_ai && (
              <Chip
                label={item.target_ai}
                variant="outlined"
                size="small"
                aria-label={`Target AI: ${item.target_ai}`}
              />
            )}
            {item.tags.map((tag) => (
              <Chip key={tag} label={tag} size="small" variant="outlined" />
            ))}
          </Stack>
        )}

        {/* Author + last updated (AC 3) */}
        {(item.author != null || lastUpdatedFormatted != null) && (
          <Stack direction="row" gap={3} flexWrap="wrap">
            {item.author && (
              <Typography variant="caption" color="text.secondary">
                Author:{" "}
                <a
                  href={`https://github.com/${encodeURIComponent(item.author)}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label={`View ${item.author} on GitHub`}
                >
                  @{item.author}
                </a>
              </Typography>
            )}
            {lastUpdatedFormatted && (
              <Typography variant="caption" color="text.secondary">
                Last updated: {lastUpdatedFormatted}
              </Typography>
            )}
          </Stack>
        )}
      </Box>

      <Divider sx={{ mb: 3 }} />

      {/* Markdown content (AC 2) */}
      <Box
        sx={{
          "& pre": {
            borderRadius: 1,
            overflow: "auto",
            p: 2,
            bgcolor: "grey.50",
          },
          "& code:not(pre code)": {
            px: 0.5,
            py: 0.25,
            borderRadius: 0.5,
            bgcolor: "grey.100",
            fontSize: "0.875em",
          },
          "& h1, & h2, & h3, & h4": { mt: 3, mb: 1 },
          "& p": { mb: 1.5 },
          "& ul, & ol": { pl: 3, mb: 1.5 },
          "& a": { color: "primary.main" },
          "& blockquote": {
            borderLeft: "4px solid",
            borderColor: "primary.light",
            pl: 2,
            ml: 0,
            color: "text.secondary",
          },
          "& table": { borderCollapse: "collapse", width: "100%" },
          "& th, & td": { border: "1px solid", borderColor: "divider", px: 1.5, py: 0.75 },
        }}
        role="article"
        aria-label="Item content"
      >
        <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
          {item.content}
        </ReactMarkdown>
      </Box>

      {/* Toast: copy success (AC 4) */}
      <Snackbar
        open={copySuccess}
        autoHideDuration={3000}
        onClose={() => {
          setCopySuccess(false);
        }}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
      >
        <Alert
          severity="success"
          onClose={() => {
            setCopySuccess(false);
          }}
          aria-live="polite"
        >
          Copied to clipboard
        </Alert>
      </Snackbar>

      {/* Toast: copy error */}
      <Snackbar
        open={copyError}
        autoHideDuration={3000}
        onClose={() => {
          setCopyError(false);
        }}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
      >
        <Alert
          severity="error"
          onClose={() => {
            setCopyError(false);
          }}
          aria-live="polite"
        >
          Failed to copy to clipboard
        </Alert>
      </Snackbar>
    </Container>
  );
}
