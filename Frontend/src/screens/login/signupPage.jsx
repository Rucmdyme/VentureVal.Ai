import React, { useState } from "react";
import {
  Container,
  Box,
  Typography,
  TextField,
  Button,
  MenuItem,
  FormControl,
  InputLabel,
  Select,
  Checkbox,
  ListItemText,
  OutlinedInput,
  FormHelperText,
} from "@mui/material";
import { useNavigate } from "react-router-dom";
import { LOGIN_FORM_CONFIG } from "./constants";
import { signUpUser } from "../../apiService/venturevalService";
import { toast } from "react-toastify";

export default function SignupPage() {
  const [role, setRole] = useState("");
  const [form, setForm] = useState({});
  const [errors, setErrors] = useState({});
  const navigate = useNavigate();

  const loadPage = () => {
    setRole("");
    setForm({});
    setErrors({});
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    setErrors((prev) => ({ ...prev, [name]: "" }));
  };

  const validate = () => {
    const newErrors = {};
    const requiredFields = LOGIN_FORM_CONFIG.common;

    requiredFields.forEach((field) => {
      if (!form[field.name] || form[field.name].trim() === "") {
        newErrors[field.name] = `${field.label} is required`;
      }
    });

    if (!role) newErrors.role = "Please select a role";
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSignup = async () => {
    if (!validate()) return;
    const body = {
      full_name: form.full_name,
      email: form.email,
      password: form.password,
      role_details: {
        role,
      },
    };
    try {
      const { message, success } = await signUpUser(body);
      if (success) {
        toast.success(message);
        loadPage();
        navigate("/signup-success");
      } else toast.error(message);
    } catch (error) {
      toast.error(error?.message || "something went wrong");
    }
  };

  const renderField = (field) => {
    const { name, label, type, placeholder, options } = field;
    const error = !!errors[name];

    switch (type) {
      case "text":
      case "email":
      case "password":
        return (
          <TextField
            key={name}
            label={label}
            name={name}
            type={type}
            placeholder={placeholder || ""}
            value={form[name] || ""}
            onChange={handleChange}
            fullWidth
            size="small"
            margin="normal"
            error={error}
            helperText={errors[name]}
          />
        );
      case "select":
        return (
          <FormControl
            key={name}
            fullWidth
            size="small"
            margin="normal"
            error={error}
          >
            <InputLabel>{label}</InputLabel>
            <Select
              name={name}
              value={form[name] || ""}
              onChange={handleChange}
              label={label}
            >
              {options.map((opt) => (
                <MenuItem key={opt} value={opt}>
                  {opt}
                </MenuItem>
              ))}
            </Select>
            {error && <FormHelperText>{errors[name]}</FormHelperText>}
          </FormControl>
        );
      case "multiselect":
        return (
          <FormControl
            key={name}
            fullWidth
            size="small"
            margin="normal"
            error={error}
          >
            <InputLabel>{label}</InputLabel>
            <Select
              multiple
              name={name}
              value={form[name] || []}
              onChange={handleChange}
              input={<OutlinedInput label={label} />}
              renderValue={(selected) => selected.join(", ")}
            >
              {options.map((opt) => (
                <MenuItem key={opt} value={opt}>
                  <Checkbox checked={form[name]?.includes(opt)} />
                  <ListItemText primary={opt} />
                </MenuItem>
              ))}
            </Select>
            {error && <FormHelperText>{errors[name]}</FormHelperText>}
          </FormControl>
        );
      default:
        return null;
    }
  };

  const roleSpecificFields = role
    ? LOGIN_FORM_CONFIG.roleSpecific[role] || []
    : [];

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
          Create your account to get started
        </Typography>

        <Box sx={{ p: 3, borderRadius: 3, boxShadow: 2, width: "100%" }}>
          {LOGIN_FORM_CONFIG.common.map(renderField)}

          <FormControl
            margin="normal"
            fullWidth
            size="small"
            error={!!errors.role}
          >
            <InputLabel>What best describes you?</InputLabel>
            <Select
              value={role}
              onChange={(e) => {
                setRole(e.target.value);
                setErrors((prev) => ({ ...prev, role: "" }));
              }}
              label="What best describes you?"
            >
              {LOGIN_FORM_CONFIG.roles.map((r) => (
                <MenuItem key={r} value={r}>
                  {r}
                </MenuItem>
              ))}
            </Select>
            {errors.role && <FormHelperText>{errors.role}</FormHelperText>}
          </FormControl>

          {roleSpecificFields.map(renderField)}

          <Button
            variant="contained"
            fullWidth
            sx={{
              mt: 3,
              borderRadius: 2,
              textTransform: "none",
              fontWeight: "bold",
            }}
            onClick={handleSignup}
          >
            Sign Up
          </Button>

          <Typography textAlign="center" variant="body2" sx={{ mt: 2 }}>
            Already have an account?{" "}
            <Button
              variant="text"
              sx={{
                textTransform: "none",
                p: 0,
                minWidth: "auto",
                color: "#2979ff",
              }}
              onClick={() => navigate("/login")}
            >
              Sign in
            </Button>
          </Typography>
        </Box>
      </Box>
    </Container>
  );
}
