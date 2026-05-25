/**
 * LibraryPage — Full authenticated browse, search & filter page.
 *
 * AC 1: Shows library items list loaded from GET /api/v1/library/items.
 * AC 2: Each card displays title, description, content_type, tags, target AI.
 * AC 4: Search box debounced 300ms — updates q filter.
 * AC 5: "No results found" empty state.
 * AC 6: content_type toggle filter (All / Skill / Prompt).
 * AC 7: target_ai chip filter.
 * AC 8: Tags chip filter.
 * AC 9: Combined filters apply AND logic (server-side).
 * AC 13: Page is wrapped in ProtectedRoute (see App.tsx).
 */
import { useEffect, useMemo, useState } from "react";
import {
  Box,
  Chip,
  CircularProgress,
  Container,
  Grid2,
  InputAdornment,
  MenuItem,
  Pagination,
  Select,
  type SelectChangeEvent,
  Skeleton,
  Stack,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import { SkillCard } from "../components/LibraryItem/SkillCard";
import { useLibraryItems } from "../hooks/useLibraryItems";
import type { LibraryFilters } from "../api/library";

// ---------------------------------------------------------------------------
// Sub-component: filter bar
// ---------------------------------------------------------------------------

interface FilterBarProps {
  searchValue: string;
  onSearchChange: (value: string) => void;
  typeValue: string;
  onTypeChange: (value: string) => void;
  targetAiOptions: string[];
  targetAiValue: string;
  onTargetAiChange: (value: string) => void;
  allTags: string[];
  selectedTags: string[];
  onTagToggle: (tag: string) => void;
}

function FilterBar({
  searchValue,
  onSearchChange,
  typeValue,
  onTypeChange,
  targetAiOptions,
  targetAiValue,
  onTargetAiChange,
  allTags,
  selectedTags,
  onTagToggle,
}: FilterBarProps) {
  return (
    <Stack spacing={2} sx={{ mb: 3 }}>
      {/* Search */}
      <TextField
        fullWidth
        placeholder="Search skills and prompts…"
        value={searchValue}
        onChange={(e) => {
          onSearchChange(e.target.value);
        }}
        size="small"
        slotProps={{
          input: {
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" />
              </InputAdornment>
            ),
          },
          htmlInput: { "aria-label": "Search library" },
        }}
      />

      <Stack direction="row" flexWrap="wrap" alignItems="center" gap={2}>
        {/* Content type toggle */}
        <ToggleButtonGroup
          value={typeValue}
          exclusive
          onChange={(_event, newValue: string | null) => {
            onTypeChange(newValue ?? "");
          }}
          size="small"
          aria-label="Filter by content type"
        >
          <ToggleButton value="" aria-label="All types">
            All
          </ToggleButton>
          <ToggleButton value="Skill" aria-label="Skills only">
            Skill
          </ToggleButton>
          <ToggleButton value="Prompt" aria-label="Prompts only">
            Prompt
          </ToggleButton>
        </ToggleButtonGroup>

        {/* Target AI filter */}
        {targetAiOptions.length > 0 && (
          <Select
            value={targetAiValue}
            onChange={(e: SelectChangeEvent) => {
              onTargetAiChange(e.target.value);
            }}
            displayEmpty
            size="small"
            sx={{ minWidth: 160 }}
            inputProps={{ "aria-label": "Filter by target AI" }}
          >
            <MenuItem value="">All AI assistants</MenuItem>
            {targetAiOptions.map((ai) => (
              <MenuItem key={ai} value={ai}>
                {ai}
              </MenuItem>
            ))}
          </Select>
        )}
      </Stack>

      {/* Tag chips */}
      {allTags.length > 0 && (
        <Stack direction="row" flexWrap="wrap" gap={0.5} aria-label="Filter by tag">
          {allTags.map((tag) => (
            <Chip
              key={tag}
              label={tag}
              onClick={() => {
                onTagToggle(tag);
              }}
              color={selectedTags.includes(tag) ? "primary" : "default"}
              variant={selectedTags.includes(tag) ? "filled" : "outlined"}
              size="small"
              aria-pressed={selectedTags.includes(tag)}
              clickable
            />
          ))}
        </Stack>
      )}
    </Stack>
  );
}

// ---------------------------------------------------------------------------
// Loading skeletons
// ---------------------------------------------------------------------------

function LoadingGrid() {
  return (
    <Grid2 container spacing={2}>
      {Array.from({ length: 6 }).map((_, i) => (
        <Grid2 key={i} size={{ xs: 12, sm: 6, md: 4 }}>
          <Skeleton variant="rectangular" height={180} sx={{ borderRadius: 1 }} />
        </Grid2>
      ))}
    </Grid2>
  );
}

// ---------------------------------------------------------------------------
// LibraryPage
// ---------------------------------------------------------------------------

// Stable empty filters object for the options catalogue query.
const CATALOGUE_FILTERS: LibraryFilters = { size: 100 };

export function LibraryPage() {
  const [typeFilter, setTypeFilter] = useState<string>("");
  const [targetAiFilter, setTargetAiFilter] = useState<string>("");
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [searchInput, setSearchInput] = useState<string>("");
  const [debouncedQ, setDebouncedQ] = useState<string>("");
  const [currentPage, setCurrentPage] = useState<number>(1);

  // Debounce search input — 300ms (AC 4); reset page on new search
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQ(searchInput);
      setCurrentPage(1);
    }, 300);
    return () => {
      clearTimeout(timer);
    };
  }, [searchInput]);

  const filters: LibraryFilters = useMemo(
    () => ({
      type: typeFilter || undefined,
      target_ai: targetAiFilter || undefined,
      tags: selectedTags.length > 0 ? selectedTags : undefined,
      q: debouncedQ || undefined,
      page: currentPage,
      size: 20,
    }),
    [typeFilter, targetAiFilter, selectedTags, debouncedQ, currentPage],
  );

  const { data, isLoading } = useLibraryItems(filters);

  // Separate unfiltered query for building option lists (AC 7, 8).
  // Uses a module-level stable object so TanStack Query caches it as a single key.
  const { data: catalogueData } = useLibraryItems(CATALOGUE_FILTERS);

  const targetAiOptions = useMemo(
    () =>
      [
        ...new Set(
          (catalogueData?.items ?? []).map((i) => i.target_ai).filter(Boolean) as string[],
        ),
      ].sort(),
    [catalogueData],
  );

  const allTags = useMemo(
    () => [...new Set((catalogueData?.items ?? []).flatMap((i) => i.tags))].sort(),
    [catalogueData],
  );

  // Reset page when filters change (except page itself)
  const resetPage = () => {
    setCurrentPage(1);
  };

  const handleTagToggle = (tag: string) => {
    resetPage();
    setSelectedTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag],
    );
  };

  return (
    <Container maxWidth="lg" disableGutters>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" fontWeight={700} gutterBottom>
          AI Skills &amp; Prompts Library
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          Browse, search, and filter the full collection of AI skills and prompt templates.
        </Typography>
      </Box>

      <FilterBar
        searchValue={searchInput}
        onSearchChange={setSearchInput}
        typeValue={typeFilter}
        onTypeChange={(v) => {
          setTypeFilter(v);
          resetPage();
        }}
        targetAiOptions={targetAiOptions}
        targetAiValue={targetAiFilter}
        onTargetAiChange={(v) => {
          setTargetAiFilter(v);
          resetPage();
        }}
        allTags={allTags}
        selectedTags={selectedTags}
        onTagToggle={handleTagToggle}
      />

      {/* Loading state */}
      {isLoading && <LoadingGrid />}

      {/* Empty state (AC 5) */}
      {!isLoading && data && data.total === 0 && (
        <Box
          display="flex"
          flexDirection="column"
          alignItems="center"
          justifyContent="center"
          py={8}
          aria-live="polite"
        >
          <Typography variant="h6" color="text.secondary" gutterBottom>
            No results found
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Try adjusting your search or filters.
          </Typography>
        </Box>
      )}

      {/* Results grid (AC 1, 2) */}
      {!isLoading && data && data.total > 0 && (
        <>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {data.total} {data.total === 1 ? "result" : "results"}
          </Typography>
          <Grid2 container spacing={2}>
            {data.items.map((item) => (
              <Grid2 key={item.slug} size={{ xs: 12, sm: 6, md: 4 }}>
                <SkillCard item={item} />
              </Grid2>
            ))}
          </Grid2>
          {data.pages > 1 && (
            <Box display="flex" justifyContent="center" mt={4}>
              <Pagination
                count={data.pages}
                page={currentPage}
                onChange={(_event, page) => {
                  setCurrentPage(page);
                }}
                color="primary"
                aria-label="Library page navigation"
              />
            </Box>
          )}
        </>
      )}

      {/* Spinner while initially loading before any data arrives */}
      {isLoading && (
        <Box display="flex" justifyContent="center" py={4}>
          <CircularProgress aria-label="Loading library items" />
        </Box>
      )}
    </Container>
  );
}
