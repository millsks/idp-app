/**
 * HomePage — Public landing page for the Integrated Developer Portal.
 *
 * Auth-conditional CTA (AC-8) will be wired to AuthContext in Story 2.3.
 * Until then, `isAuthenticated` is hardcoded false so the Sign In CTA is always shown.
 */
import {
  Box,
  Button,
  Card,
  CardActionArea,
  CardContent,
  Chip,
  Container,
  Grid2,
  Link,
  Stack,
  Typography,
} from "@mui/material";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import StorefrontIcon from "@mui/icons-material/Storefront";
import BuildIcon from "@mui/icons-material/Build";
import RocketLaunchIcon from "@mui/icons-material/RocketLaunch";
import SecurityIcon from "@mui/icons-material/Security";
import GitHubIcon from "@mui/icons-material/GitHub";
import { Link as RouterLink } from "react-router-dom";

interface Pillar {
  icon: React.ReactElement;
  title: string;
  description: string;
  live: boolean;
  href?: string;
}

const PILLARS: Pillar[] = [
  {
    icon: <AutoAwesomeIcon fontSize="large" />,
    title: "AI Skills & Prompts Library",
    description:
      "Browse, search, and copy a curated collection of AI skills and prompt templates — ready to drop into any AI assistant.",
    live: true,
    href: "/library",
  },
  {
    icon: <StorefrontIcon fontSize="large" />,
    title: "Software Marketplace",
    description:
      "Discover vetted libraries, frameworks, and developer tools to accelerate your projects.",
    live: false,
  },
  {
    icon: <BuildIcon fontSize="large" />,
    title: "Developer Utilities",
    description: "Handy utilities and scripts that streamline common development workflows.",
    live: false,
  },
  {
    icon: <RocketLaunchIcon fontSize="large" />,
    title: "Application Accelerators",
    description: "Scaffolded project templates and blueprints to launch new applications fast.",
    live: false,
  },
  {
    icon: <SecurityIcon fontSize="large" />,
    title: "Vulnerability Library",
    description: "Searchable NVD vulnerability database with contextual guidance for developers.",
    live: false,
  },
];

export function HomePage() {
  return (
    <Box>
      {/* Hero section */}
      <Container maxWidth="md" disableGutters sx={{ py: { xs: 4, md: 8 }, textAlign: "center" }}>
        <Typography variant="h3" component="h1" fontWeight={700} gutterBottom>
          The Integrated Developer Portal
        </Typography>
        <Typography variant="h6" color="text.secondary" sx={{ mb: 4, fontWeight: 400 }}>
          A community-built, open-source portal bringing together AI skills, curated tools,
          application accelerators, and security insights — everything a developer needs, in one
          place.
        </Typography>

        <Stack
          direction={{ xs: "column", sm: "row" }}
          spacing={2}
          justifyContent="center"
          alignItems="center"
        >
          {/* Story 2.3: replace with auth-conditional CTA (Sign In ↔ Browse Library) */}
          <Button
            component={RouterLink}
            to="/login"
            variant="contained"
            size="large"
            aria-label="Sign in to the developer portal"
          >
            Sign In
          </Button>

          <Link
            href="https://github.com/millsks/idp-app"
            target="_blank"
            rel="noopener noreferrer"
            sx={{ display: "flex", alignItems: "center", gap: 0.5, fontWeight: 600 }}
          >
            <GitHubIcon fontSize="small" />
            Open Source on GitHub
          </Link>
        </Stack>
      </Container>

      {/* Capability pillars */}
      <Box sx={{ mt: 2 }}>
        <Typography variant="h5" component="h2" fontWeight={600} gutterBottom sx={{ mb: 3 }}>
          What&rsquo;s inside
        </Typography>

        <Grid2 container spacing={3}>
          {PILLARS.map((pillar) => (
            <Grid2 key={pillar.title} size={{ xs: 12, sm: 6, md: 4 }}>
              <Card
                sx={{
                  height: "100%",
                  display: "flex",
                  flexDirection: "column",
                  position: "relative",
                  border: pillar.live ? "2px solid" : "1px solid",
                  borderColor: pillar.live ? "primary.main" : "divider",
                  opacity: pillar.live ? 1 : 0.75,
                }}
                aria-label={
                  pillar.live ? `${pillar.title} — available now` : `${pillar.title} — coming soon`
                }
              >
                {!pillar.live && (
                  <Chip
                    label="Coming Soon"
                    size="small"
                    color="default"
                    sx={{
                      position: "absolute",
                      top: 12,
                      right: 12,
                      fontWeight: 600,
                      fontSize: "0.7rem",
                    }}
                  />
                )}
                {pillar.href ? (
                  <CardActionArea
                    component={RouterLink}
                    to={pillar.href}
                    sx={{
                      flexGrow: 1,
                      display: "flex",
                      flexDirection: "column",
                      alignItems: "flex-start",
                    }}
                    aria-label={`Go to ${pillar.title}`}
                  >
                    <CardContent sx={{ flexGrow: 1, width: "100%" }}>
                      <Box sx={{ mb: 2, color: "primary.main" }}>{pillar.icon}</Box>
                      <Typography variant="h6" gutterBottom fontWeight={600}>
                        {pillar.title}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {pillar.description}
                      </Typography>
                    </CardContent>
                  </CardActionArea>
                ) : (
                  <CardContent sx={{ flexGrow: 1 }}>
                    <Box
                      sx={{
                        mb: 2,
                        color: pillar.live ? "primary.main" : "text.disabled",
                      }}
                    >
                      {pillar.icon}
                    </Box>
                    <Typography variant="h6" gutterBottom fontWeight={600}>
                      {pillar.title}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {pillar.description}
                    </Typography>
                  </CardContent>
                )}
              </Card>
            </Grid2>
          ))}
        </Grid2>
      </Box>
    </Box>
  );
}
