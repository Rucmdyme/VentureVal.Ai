import { Box, Typography } from "@mui/material";
import NoDataComponent from "../noDataComponent";

const sentimentMap = {
  positive: {
    color: "#2e7d32",
    bg: "#e8f5e9",
  },
  negative: {
    color: "#c62828",
    bg: "#ffebee",
  },
  neutral: {
    color: "#1565c0",
    bg: "#e3f2fd",
  },
};

export default function Insights({ insightsData }) {
  return insightsData?.length ? (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
        gap: 2,
      }}
    >
      {insightsData.map((insight, idx) => {
        const sentiment =
          sentimentMap[insight.sentiment] || sentimentMap.neutral;

        return (
          <Box
            key={idx}
            sx={{
              border: `1px solid ${sentiment.color}`,
              bgcolor: sentiment.bg,
              borderRadius: 2,
              p: 2,
            }}
          >
            <Typography
              variant="subtitle1"
              sx={{
                fontWeight: 600,
                color: sentiment.color,
              }}
            >
              {insight.parameter}
            </Typography>
            <Typography variant="body2" sx={{ mt: 1 }}>
              {insight.value}
            </Typography>
          </Box>
        );
      })}
    </Box>
  ) : (
    <Box sx={{ p: 2, border: "1px solid #e0e0e0", borderRadius: 4 }}>
      <NoDataComponent />
    </Box>
  );
}
