/**
 * SkillCard — displays a single library item in the browse grid.
 *
 * Shows: title, description snippet (truncated to 3 lines), content_type badge,
 * tags chips, and target AI chip.
 */
import { Box, Card, CardContent, Chip, Stack, Typography } from "@mui/material";
import type { LibraryItem } from "../../api/library";

interface SkillCardProps {
  item: LibraryItem;
}

export function SkillCard({ item }: SkillCardProps) {
  const contentTypeColor = item.content_type === "Skill" ? "primary" : "secondary";

  return (
    <Card
      variant="outlined"
      sx={{ height: "100%", display: "flex", flexDirection: "column" }}
      aria-label={item.title}
    >
      <CardContent sx={{ flexGrow: 1, display: "flex", flexDirection: "column", gap: 1 }}>
        {/* Header row: title + content_type badge */}
        <Stack direction="row" alignItems="flex-start" justifyContent="space-between" gap={1}>
          <Typography
            variant="h6"
            component="h2"
            sx={{ fontSize: "1rem", fontWeight: 600, lineHeight: 1.3 }}
          >
            {item.title}
          </Typography>
          <Chip
            label={item.content_type}
            color={contentTypeColor}
            size="small"
            sx={{ flexShrink: 0 }}
            aria-label={`Content type: ${item.content_type}`}
          />
        </Stack>

        {/* Description snippet */}
        <Typography
          variant="body2"
          color="text.secondary"
          sx={{
            display: "-webkit-box",
            WebkitLineClamp: 3,
            WebkitBoxOrient: "vertical",
            overflow: "hidden",
            flexGrow: 1,
          }}
        >
          {item.description || "No description available."}
        </Typography>

        {/* Target AI chip */}
        {item.target_ai && (
          <Box>
            <Chip
              label={item.target_ai}
              variant="outlined"
              size="small"
              aria-label={`Target AI: ${item.target_ai}`}
            />
          </Box>
        )}

        {/* Tags */}
        {item.tags.length > 0 && (
          <Stack direction="row" flexWrap="wrap" gap={0.5} aria-label="Tags">
            {item.tags.map((tag) => (
              <Chip key={tag} label={tag} size="small" variant="outlined" color="default" />
            ))}
          </Stack>
        )}
      </CardContent>
    </Card>
  );
}
