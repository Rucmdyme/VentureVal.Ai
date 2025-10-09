// src/components/Navbar.jsx
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  IconButton,
  Box,
  Drawer,
  List,
  ListItem,
  ListItemText,
  Avatar,
} from "@mui/material";
import MenuIcon from "@mui/icons-material/Menu";
import AccountCircleIcon from "@mui/icons-material/AccountCircle";
import { useEffect, useState } from "react";
import venturevalLogo from "../../assets/ventureval.jpg";
import { useLocation, NavLink, useNavigate } from "react-router-dom";
import { scroller, Events } from "react-scroll";

const navLinks = [
  { label: "Home", target: "home", type: "scroll" },
  { label: "Analyze Startup", target: "analyze", type: "scroll" },
  { label: "Features", target: "features", type: "scroll" },
  { label: "Contact Us", target: "/contact", type: "route" },
];

function Navbar() {
  const location = useLocation();
  const isHome = location.pathname === "/" || "/contact";
  const [open, setOpen] = useState(false);
  const [isLogin, setIsLogin] = useState(false);
  const [active, setActive] = useState("home");
  const navigate = useNavigate();

  useEffect(() => {
    Events.scrollEvent.register("begin", (to) => {
      setActive(to);
    });
    const ventureAuthToken = localStorage.getItem("venture_auth_token");
    setIsLogin(!!ventureAuthToken);

    return () => {
      Events.scrollEvent.remove("begin");
    };
  }, []);
  useEffect(() => {
    if (location.pathname === "/contact") {
      setActive("");
    }
  }, [location]);

  const handleNavClick = (target) => {
    if (location.pathname !== "/") {
      // Navigate back to home, then scroll after navigation
      navigate("/", { replace: false });
      setTimeout(() => {
        scroller.scrollTo(target, {
          smooth: true,
          duration: 500,
          offset: -80,
        });
      }, 100); // small delay so page loads before scroll
    } else {
      // Already on home, just scroll
      scroller.scrollTo(target, {
        smooth: true,
        duration: 500,
        offset: -80,
      });
    }
  };

  return (
    <>
      <AppBar
        position="fixed"
        color="inherit"
        elevation={1}
        sx={{ background: "linear-gradient(135deg, #9c27b0, #2979ff)" }}
      >
        <Toolbar sx={{ justifyContent: "space-between" }}>
          <Box display="flex" alignItems="center" gap={1}>
            <Avatar
              src={venturevalLogo}
              alt="logo"
              sx={{ width: 36, height: 36 }}
            />
            <Typography variant="h6" fontWeight="bold" sx={{ color: "white" }}>
              VentureVal
            </Typography>
          </Box>

          {isHome && (
            <Box sx={{ display: { xs: "none", md: "flex" }, gap: 3 }}>
              {navLinks.map((link) =>
                link.type === "scroll" ? (
                  <Button
                    key={link.target}
                    onClick={() => handleNavClick(link.target)}
                    className={active === link.target ? "active" : ""}
                    sx={{
                      color: "white",
                      textTransform: "none",
                      "&.active": {
                        fontWeight: "bold",
                        borderBottom: "2px solid white",
                      },
                    }}
                  >
                    {link.label}
                  </Button>
                ) : (
                  <Button
                    key={link.target}
                    component={NavLink}
                    to={link.target}
                    className={({ isActive }) => (isActive ? "active" : "")}
                    sx={{
                      color: "white",
                      textTransform: "none",
                      "&.active": {
                        fontWeight: "bold",
                        borderBottom: "2px solid white",
                      },
                    }}
                  >
                    {link.label}
                  </Button>
                )
              )}
            </Box>
          )}

          {/* Right Side */}
          <Box display="flex" alignItems="center" gap={2}>
            {!isLogin ? (
              <Button
                onClick={() => {
                  navigate("/login");
                }}
                sx={{
                  color: "white",
                  textTransform: "none",
                  display: { xs: "none", sm: "inline-flex" },
                }}
              >
                Sign In
              </Button>
            ) : (
              <IconButton sx={{ color: "white" }}>
                <AccountCircleIcon sx={{ fontSize: 32 }} />
              </IconButton>
            )}
            {/* Hamburger (mobile only) */}
            <IconButton
              sx={{ display: { md: "none" } }}
              onClick={() => setOpen(true)}
            >
              <MenuIcon />
            </IconButton>
          </Box>
        </Toolbar>
      </AppBar>

      {/* Mobile Drawer */}
      <Drawer anchor="right" open={open} onClose={() => setOpen(false)}>
        <Box sx={{ width: 250, mt: 2 }}>
          <List>
            {navLinks.map((link) => (
              <ListItem
                button
                key={link.path}
                component={NavLink}
                to={link.path}
                onClick={() => {
                  setOpen(false);
                  if (link.type === "scroll") {
                    handleNavClick(link.target);
                  }
                }}
              >
                <ListItemText primary={link.label} />
              </ListItem>
            ))}
          </List>
        </Box>
      </Drawer>
    </>
  );
}

export default Navbar;
