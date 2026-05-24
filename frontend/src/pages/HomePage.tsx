import { Box, Card, CardContent, Grid2, Typography } from "@mui/material";
import DeveloperModeIcon from "@mui/icons-material/DeveloperMode";
import StorageIcon from "@mui/icons-material/Storage";
import SpeedIcon from "@mui/icons-material/Speed";
import { PublicPreviewStrip } from "../components/LandingPreview/PublicPreviewStrip";

interface FeatureCard {
  icon: React.ReactElement;
  title: string;
  description: string;
}

const FEATURES: FeatureCard[] = [
  {
    icon: <DeveloperModeIcon fontSize="large" color="primary" />,
    title: "Developer Tools",
    description: "Centralised access to all development resources, documentation, and tooling.",
  },
  {
    icon: <StorageIcon fontSize="large" color="primary" />,
    title: "Service Catalog",
    description: "Discover and manage microservices, APIs, and infrastructure components.",
  },
  {
    icon: <SpeedIcon fontSize="large" color="primary" />,
    title: "Metrics & Observability",
    description: "Real-time dashboards and alerts for system health and performance.",
  },
];

export function HomePage() {
  return (
    <Box>
      <Typography variant="h4" gutterBottom fontWeight={700}>
        Welcome to the Developer Portal
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Your single pane of glass for all developer resources, services, and tooling.
      </Typography>

      <Grid2 container spacing={3}>
        {FEATURES.map((feature) => (
          <Grid2 key={feature.title} size={{ xs: 12, sm: 6, md: 4 }}>
            <Card sx={{ height: "100%", display: "flex", flexDirection: "column" }}>
              <CardContent sx={{ flexGrow: 1 }}>
                <Box sx={{ mb: 2 }}>{feature.icon}</Box>
                <Typography variant="h6" gutterBottom>
                  {feature.title}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {feature.description}
                </Typography>
              </CardContent>
            </Card>
          </Grid2>
        ))}
      </Grid2>

      <PublicPreviewStrip />
    </Box>
  );
}
