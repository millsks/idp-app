import { Outlet } from "react-router-dom";
import {
  AppBar,
  Box,
  Container,
  Drawer,
  IconButton,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Typography,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import MenuIcon from "@mui/icons-material/Menu";
import HomeIcon from "@mui/icons-material/Home";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

const DRAWER_WIDTH = 240;

interface NavItem {
  label: string;
  path: string;
  icon: React.ReactElement;
}

const NAV_ITEMS: NavItem[] = [{ label: "Home", path: "/", icon: <HomeIcon /> }];

/**
 * Root layout: top AppBar + collapsible side Drawer + main content area.
 * Nested routes are rendered via <Outlet />.
 */
export function Layout() {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("md"));
  const [drawerOpen, setDrawerOpen] = useState(!isMobile);
  const navigate = useNavigate();

  const handleDrawerToggle = () => {
    setDrawerOpen((prev) => !prev);
  };

  const drawerContent = (
    <Box>
      <Toolbar />
      <List>
        {NAV_ITEMS.map((item) => (
          <ListItem key={item.path} disablePadding>
            <ListItemButton
              onClick={() => {
                void navigate(item.path);
                if (isMobile) setDrawerOpen(false);
              }}
            >
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
    </Box>
  );

  return (
    <Box sx={{ display: "flex" }}>
      {/* Top app bar */}
      <AppBar position="fixed" sx={{ zIndex: (t) => t.zIndex.drawer + 1 }}>
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="toggle navigation drawer"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2 }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" noWrap component="div">
            Integrated Developer Portal
          </Typography>
        </Toolbar>
      </AppBar>

      {/* Side navigation drawer */}
      <Drawer
        variant={isMobile ? "temporary" : "persistent"}
        open={drawerOpen}
        onClose={handleDrawerToggle}
        ModalProps={{ keepMounted: true }}
        sx={{
          width: DRAWER_WIDTH,
          flexShrink: 0,
          "& .MuiDrawer-paper": {
            width: DRAWER_WIDTH,
            boxSizing: "border-box",
          },
        }}
      >
        {drawerContent}
      </Drawer>

      {/* Main content */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          mt: "64px", // AppBar height
          transition: (t) =>
            t.transitions.create("margin", {
              easing: t.transitions.easing.sharp,
              duration: t.transitions.duration.leavingScreen,
            }),
        }}
      >
        <Container maxWidth="xl">
          <Outlet />
        </Container>
      </Box>
    </Box>
  );
}
