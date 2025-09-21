import React from "react";
import {
  Box,
  Typography,
  Slider,
  Grid,
  Select,
  MenuItem,
  Card,
  CardContent,
  FormControl,
  InputLabel,
} from "@mui/material";
import { factors, PRESETS } from "./constants";

export default function WeightsSection({
  weights,
  setWeights,
  preset,
  setPreset,
}) {
  const total = Object.values(weights || {}).reduce((a, b) => a + b, 0);

  const handleChange = (factor, value) => {
    setWeights((prev) => ({
      ...prev,
      [factor]: value,
    }));
  };

  const applyPreset = (presetName) => {
    setPreset(presetName);
    setWeights(PRESETS[presetName]);
  };

  return (
    <Box sx={{ py: 6 }}>
      <Card variant="outlined" sx={{ borderRadius: 3, p: 2 }}>
        <CardContent>
          <FormControl sx={{ mb: 4, width: 300 }} size="small">
            <InputLabel>Select Predefined Weights</InputLabel>
            <Select
              value={preset}
              label="Select Predefined Weights"
              onChange={(e) => applyPreset(e.target.value)}
            >
              {Object.keys(PRESETS).map((key) => (
                <MenuItem key={key} value={key}>
                  {key}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <Grid container rowSpacing={4} columnSpacing={16}>
            {factors.map((f) => (
              <Grid item size={{ xs: 12, md: 4 }} key={f.key} sx={{}}>
                <Box display="flex" justifyContent="space-between" mb={1}>
                  <Typography sx={{ fontWeight: 500, ml: 1 }}>
                    {f.label}
                  </Typography>
                  <Typography color={f.color} fontWeight="bold">
                    {weights[f.key]}%
                  </Typography>
                </Box>
                <Slider
                  value={weights[f.key]}
                  onChange={(_, val) => handleChange(f.key, val)}
                  min={0}
                  max={100}
                  step={1}
                  disabled={preset !== "Default (Custom)"}
                  sx={{
                    color: f.color,
                  }}
                />
              </Grid>
            ))}
          </Grid>

          <Box mt={4} textAlign="right">
            <Typography fontWeight="bold">
              Total Weight:{" "}
              <Box component="span" color={total === 100 ? "green" : "#d32f2f"}>
                {total}%
              </Box>
            </Typography>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}
