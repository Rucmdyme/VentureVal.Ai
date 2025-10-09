import React from "react";
import { Box, Typography, Button, Paper, Link } from "@mui/material";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import { useNavigate } from "react-router-dom";

export default function SignupSuccess() {
  const navigate = useNavigate();

  const handleLoginRedirect = () => {
    navigate("/login");
  };

  return (
    <Box
      sx={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        minHeight: "100vh",
        bgcolor: "#f5f7fa",
        px: 2,
      }}
    >
      <Paper
        elevation={3}
        sx={{
          maxWidth: 400,
          width: "100%",
          p: 4,
          borderRadius: 3,
          textAlign: "center",
        }}
      >
        <Typography
          variant="h6"
          fontWeight="bold"
          color="#2979ff"
          sx={{ mb: 3 }}
        >
          VentureVal
        </Typography>

        <Box sx={{ display: "flex", justifyContent: "center", mb: 2 }}>
          <CheckCircleOutlineIcon color="success" sx={{ fontSize: 64 }} />
        </Box>

        <Typography variant="h5" fontWeight="bold" gutterBottom>
          Your account has been created!
        </Typography>

        <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
          Welcome aboard. You can now log in and start exploring.
        </Typography>

        <Button
          variant="contained"
          fullWidth
          sx={{
            textTransform: "none",
            borderRadius: 2,
            background: "#2979ff",
          }}
          onClick={handleLoginRedirect}
        >
          Log in now
        </Button>
      </Paper>
    </Box>
  );
}
