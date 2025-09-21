// src/components/RiskAssessmentRadar.js
import React from "react";
import {
  Box,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Grid,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";

import CircleIcon from "@mui/icons-material/Circle";
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Tooltip,
} from "recharts";
import { getSeverityLabel, severityColors, transformRisks } from "./utils";

const RiskAssessmentRadar = ({ riskAssessment }) => {
  const risks = transformRisks(riskAssessment?.risk_scores);
  const avgSeverity = getSeverityLabel(riskAssessment?.overall_risk_score);
  const radarData = risks.map((risk) => ({
    subject: risk.title.replace(" Risk", ""),
    score: risk.score,
  }));

  return (
    <Box sx={{ p: 2, border: "1px solid #e0e0e0", borderRadius: 4 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 2 }}>
        <Box>
          <Typography sx={{ fontSize: 18, fontWeight: "bold" }}>
            Risk Assessment Radar
          </Typography>
          <Typography sx={{ fontSize: 14, color: "#666666" }}>
            Multi-dimensional risk analysis across key business areas
          </Typography>
        </Box>
        {riskAssessment?.overall_risk_score && (
          <Box sx={{ textAlign: "center" }}>
            <Typography variant="h5" fontWeight={700}>
              {riskAssessment?.overall_risk_score.toFixed(1)}/10
            </Typography>
            <Chip
              size="small"
              label={`${avgSeverity} Risk`}
              color={severityColors[avgSeverity]}
              sx={{ p: 0.5 }}
            />
          </Box>
        )}
      </Box>

      <Grid container spacing={3}>
        {/* Radar Chart */}
        {risks?.length > 2 && (
          <Grid item size={{ xs: 12, md: 5 }}>
            <Box
              sx={{
                width: "100%",
                display: "flex",
                justifyContent: "center",
              }}
            >
              <RadarChart
                cx={200}
                cy={200}
                outerRadius={120}
                width={400}
                height={400}
                data={radarData}
              >
                <PolarGrid />
                <PolarAngleAxis dataKey="subject" />
                <PolarRadiusAxis angle={30} domain={[0, 10]} />
                <Radar
                  name="Risk Score"
                  dataKey="score"
                  stroke="#f87171"
                  fill="#fca5a5"
                  fillOpacity={0.6}
                />
                <Tooltip />
              </RadarChart>
            </Box>
          </Grid>
        )}

        {/* Risk Breakdown */}
        <Grid item size={{ xs: 12, md: risks?.length > 2 ? 7 : 12 }}>
          {risks?.map((risk) => (
            <Accordion
              key={risk.id}
              sx={{
                mb: 2,
                borderRadius: 2,
                "&:before": {
                  display: "none",
                },
              }}
            >
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 1.5,
                    flexGrow: 1,
                  }}
                >
                  {risk.icon}
                  <Typography sx={{ flexGrow: 1, fontWeight: 550 }}>
                    {risk.title}
                  </Typography>
                  <Chip
                    sx={{ mr: 1 }}
                    label={risk.severity}
                    color={severityColors[risk.severity]}
                    size="small"
                  />
                </Box>
              </AccordionSummary>
              <AccordionDetails sx={{ py: 0.5 }}>
                <List dense disablePadding>
                  {risk.details.map((point, index) => (
                    <ListItem
                      key={index}
                      sx={{
                        py: 0.25,
                        minHeight: "28px",
                      }}
                    >
                      <ListItemIcon sx={{ minWidth: 20 }}>
                        <CircleIcon sx={{ fontSize: 8 }} />
                      </ListItemIcon>
                      <ListItemText
                        primary={point}
                        slotProps={{
                          primary: {
                            typography: { variant: "body2" }, // smaller text
                          },
                        }}
                      />
                    </ListItem>
                  ))}
                </List>
              </AccordionDetails>
            </Accordion>
          ))}
        </Grid>
      </Grid>

      {/* Footer with Score & Legend */}
      <Box sx={{ mt: 3 }}>
        <Box
          sx={{
            mt: 2,
            display: "flex",
            flexDirection: "column",
            bgcolor: "#EBEBEB",
            py: 1,
            px: 2,
            borderRadius: 2,
          }}
        >
          <Typography sx={{ fontWeight: 550, mb: 1 }}>Risk Scale</Typography>
          <Box sx={{ display: "flex", gap: 12 }}>
            <Box>
              <Typography color="success" sx={{ fontSize: 14 }}>
                Low Risk (1–3)
              </Typography>
              <Typography variant="caption" display="block">
                Minimal impact
              </Typography>
            </Box>
            <Box>
              <Typography color="#f9a825" sx={{ fontSize: 14 }}>
                Medium Risk (3–5)
              </Typography>
              <Typography variant="caption" display="block">
                Manageable with mitigation
              </Typography>
            </Box>
            <Box>
              <Typography color="warning" sx={{ fontSize: 14 }}>
                High Risk (5–8)
              </Typography>
              <Typography variant="caption" display="block">
                Needs proactive management
              </Typography>
            </Box>
            <Box>
              <Typography color="error" sx={{ fontSize: 14 }}>
                Critical Risk (8–10)
              </Typography>
              <Typography variant="caption" display="block">
                Needs immediate attention
              </Typography>
            </Box>
          </Box>
        </Box>
      </Box>
    </Box>
  );
};

export default RiskAssessmentRadar;
