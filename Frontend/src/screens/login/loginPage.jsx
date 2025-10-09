import React, { useState } from "react";
import { Container, Box, Typography, TextField, Button } from "@mui/material";
import { useNavigate } from "react-router-dom";
import { loginUser } from "../../apiService/venturevalService";
import { toast } from "react-toastify";

export default function LoginPage() {
  const [form, setForm] = useState({ email: "", password: "" });
  const [errors, setErrors] = useState({});
  const navigate = useNavigate();

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    setErrors((prev) => ({ ...prev, [name]: "" }));
  };

  const validate = () => {
    const newErrors = {};
    if (!form.email.trim()) newErrors.email = "Email is required";
    if (!form.password.trim()) newErrors.password = "Password is required";
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleLogin = async () => {
    if (!validate()) return;
    const body = {
      ...form,
    };
    const { message, success, data } = await loginUser(body);

    if (success) {
      localStorage.setItem("venture_auth_token", data.user_auth_token);
      navigate("/");
    } else {
      toast.error(message);
    }
  };

  return (
    <Container maxWidth="sm">
      <Box
        display="flex"
        flexDirection="column"
        alignItems="center"
        justifyContent="center"
        minHeight="95vh"
      >
        <Typography variant="h4" fontWeight="bold">
          VentureVal
        </Typography>
        <Typography variant="subtitle1" color="text.secondary" sx={{ mb: 4 }}>
          AI-Powered Insights for Smarter Startup Evaluation
        </Typography>

        <Box sx={{ p: 3, borderRadius: 3, boxShadow: 2, width: "100%" }}>
          <TextField
            label="Email"
            name="email"
            type="email"
            value={form.email}
            onChange={handleChange}
            fullWidth
            size="small"
            margin="normal"
            error={!!errors.email}
            helperText={errors.email}
          />
          <TextField
            label="Password"
            name="password"
            type="password"
            value={form.password}
            onChange={handleChange}
            fullWidth
            size="small"
            margin="normal"
            error={!!errors.password}
            helperText={errors.password}
          />

          <Button
            variant="contained"
            fullWidth
            sx={{
              mt: 3,
              borderRadius: 2,
              textTransform: "none",
              fontWeight: "bold",
            }}
            onClick={handleLogin}
          >
            Sign In
          </Button>

          <Typography textAlign="center" variant="body2" sx={{ mt: 2 }}>
            Don’t have an account?{" "}
            <Button
              variant="text"
              sx={{
                textTransform: "none",
                p: 0,
                minWidth: "auto",
                color: "#2979ff",
              }}
              onClick={() => navigate("/signup")}
            >
              Sign up
            </Button>
          </Typography>
        </Box>
      </Box>
    </Container>
  );
}
