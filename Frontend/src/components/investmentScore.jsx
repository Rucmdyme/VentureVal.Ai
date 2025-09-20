// src/components/InvestmentScore.js
import React from "react";
import { Box, Typography, CircularProgress } from "@mui/material";

const InvestmentScore = ({ score }) => {
  let color = "#2e7d32";
  if (score < 6) color = "#d32f2f";
  else if (score < 7.5) color = "#ed6c08";

  return (
    <Box display="flex" alignItems="center" gap={2}>
      {/* Circular progress wrapper */}
      <Box position="relative" display="inline-flex">
        {/* Background track */}
        <CircularProgress
          variant="determinate"
          value={100}
          size={70}
          thickness={5}
          sx={{ color: (theme) => theme.palette.grey[300] }}
        />
        {/* Foreground arc */}
        <CircularProgress
          variant="determinate"
          value={(score / 10) * 100}
          size={70}
          thickness={5}
          sx={{
            color: color,
            position: "absolute",
            left: 0,
          }}
        />
        {/* Inner content with padding */}
        <Box
          position="absolute"
          top={0}
          left={0}
          bottom={0}
          right={0}
          display="flex"
          alignItems="center"
          justifyContent="center"
          flexDirection="column"
          sx={{ p: 1 }}
        >
          <Typography variant="h6" fontWeight="bold" sx={{ lineHeight: 1.2 }}>
            {score}
          </Typography>
          <Typography variant="caption">/10</Typography>
        </Box>
      </Box>

      {/* Labels */}
      <Box>
        <Typography sx={{ fontSize: 16 }}>Overall Score</Typography>
      </Box>
    </Box>
  );
};

export default InvestmentScore;
