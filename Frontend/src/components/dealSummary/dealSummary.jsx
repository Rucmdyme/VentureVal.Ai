// src/components/DealNoteSummary.js
import React from "react";
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Chip,
} from "@mui/material";
import {
  ResponsiveContainer,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
} from "recharts";
import FiberManualRecordIcon from "@mui/icons-material/FiberManualRecord";
import { COLORS, concerns, strengths } from "./constants";
import { snakeCaseToTitleCase } from "../../utils";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import EqualizerIcon from "@mui/icons-material/Equalizer";
import RadarIcon from "@mui/icons-material/Radar";
import AttachMoneyIcon from "@mui/icons-material/AttachMoney";

const keyMetrics = {
  monthly_revenue: "$98K",
  growth_rate: "42% YoY",
  team_size: "120 employees",
  market_position: "Top 15%",
  runway: "18 months",
  funding_raised: "$5M",
  customers: "2",
  funding_seeking: "$3M",
};

const detailedScoreBreakdown = {
  team_quality: 6,
  market_opportunity: 7.3,
  product_technology: 5,
  growth_potential: 8,
  financial_metrics: 6.5,
  competitive_position: 7,
};

const DealNoteSummary = ({ revenueData, marketData }) => {
  return (
    <Grid container spacing={2} mb={3}>
      <Grid item size={{ xs: 12, md: 12 }}>
        <Card variant="outlined" sx={{ borderRadius: 3, p: 2 }}>
          <CardContent>
            <Typography sx={{ mb: 2, fontSize: 18, fontWeight: "bold" }}>
              Executive Summary
            </Typography>

            <Grid container spacing={4}>
              <Grid item size={{ xs: 12, md: 9 }} sx={{ pr: 20 }}>
                <Typography variant="body2" sx={{ mb: 2 }}>
                  Sia presents a high-risk investment due to its critical
                  financial state, with only 6 months of runway and zero
                  reported revenue despite having 6 customers. The company
                  urgently needs to secure a $600,000 funding round to avoid
                  insolvency, making it a highly speculative venture at this
                  seed stage.
                </Typography>
                <Typography variant="body2" sx={{ mb: 2 }}>
                  Operating in the competitive $300 billion AI/ML and Data
                  Analytics market, Sia faces established players like Alteryx
                  and Dataiku. Without clear product differentiation or proven
                  revenue traction, sustainable growth and market penetration
                  appear challenging under current financial constraints.
                </Typography>
                <Typography variant="body2">
                  Given the severe financial distress, lack of revenue, and
                  immediate capital need, the investment recommendation is a
                  clear PASS. The current risk profile significantly outweighs
                  potential upside, making it unsuitable without substantial
                  de-risking and a proven business model.
                </Typography>
              </Grid>

              <Grid item size={{ xs: 12, md: 3 }}>
                <Box mb={2}>
                  <Typography sx={{ fontSize: 16, fontWeight: "bold" }}>
                    Key Strengths
                  </Typography>
                  <List dense>
                    {strengths.map((strength, idx) => (
                      <ListItem key={idx} disableGutters sx={{ py: 0 }}>
                        <ListItemIcon sx={{ minWidth: 24 }}>
                          <FiberManualRecordIcon
                            sx={{ fontSize: 10, color: "green" }}
                          />
                        </ListItemIcon>
                        <ListItemText primary={strength} />
                      </ListItem>
                    ))}
                  </List>
                </Box>

                <Box>
                  <Typography sx={{ fontSize: 16, fontWeight: "bold" }}>
                    Key Concerns
                  </Typography>
                  <List dense>
                    {concerns.map((concern, idx) => (
                      <ListItem key={idx} disableGutters sx={{ py: 0 }}>
                        <ListItemIcon sx={{ minWidth: 24 }}>
                          <FiberManualRecordIcon
                            sx={{ fontSize: 10, color: "red" }}
                          />
                        </ListItemIcon>
                        <ListItemText primary={concern} />
                      </ListItem>
                    ))}
                  </List>
                </Box>
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      </Grid>
      <Grid item size={{ xs: 12, md: 3.5 }}>
        <Card
          sx={{
            borderRadius: 2,
            boxShadow: "0px 1px 3px rgba(0, 0, 0, 0.1)",
            mb: 2,
          }}
        >
          <CardContent>
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                mb: 2,
              }}
            >
              <AttachMoneyIcon sx={{ color: "#2979ff" }} />
              <Typography sx={{ fontWeight: "bold" }}>Key Metrics</Typography>
            </Box>
            {Object.entries(keyMetrics).map(([key, value]) => (
              <Box
                key={key}
                sx={{
                  display: "flex",
                  justifyContent: "space-between",
                  mt: 2,
                }}
              >
                <Typography sx={{ fontSize: 14, color: "#666666" }}>
                  {snakeCaseToTitleCase(key)}
                </Typography>
                {key === "market_position" ? (
                  <Chip
                    size="small"
                    label={value}
                    variant="outlined"
                    sx={{
                      backgroundColor: "#fafafa",
                      fontWeight: "550",
                      p: 0.5,
                    }}
                  />
                ) : (
                  <Typography
                    sx={{
                      fontWeight: "550",
                      fontSize: 16,
                      ...(key === "growth_rate" ? { color: "green" } : {}),
                    }}
                  >
                    {value}
                  </Typography>
                )}
              </Box>
            ))}
          </CardContent>
        </Card>
        <Card
          sx={{ borderRadius: 2, boxShadow: "0px 1px 3px rgba(0, 0, 0, 0.1)" }}
        >
          <CardContent>
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                mb: 2,
                gap: 1,
              }}
            >
              <EqualizerIcon sx={{ color: "#2979ff" }} />
              <Typography sx={{ fontWeight: "bold" }}>
                Detailed Score Breakdown
              </Typography>
            </Box>
            {Object.entries(detailedScoreBreakdown).map(([key, value]) => (
              <Box
                key={key}
                sx={{
                  display: "flex",
                  justifyContent: "space-between",
                  mt: 2,
                }}
              >
                <Typography sx={{ fontSize: 14, color: "#666666" }}>
                  {snakeCaseToTitleCase(key)}
                </Typography>

                <Typography
                  sx={{
                    fontWeight: "550",
                    fontSize: 16,
                  }}
                >
                  {`${value}/10`}
                </Typography>
              </Box>
            ))}
          </CardContent>
        </Card>
      </Grid>

      <Grid item size={{ xs: 12, md: 8.5 }}>
        <Card
          sx={{
            borderRadius: 2,
            boxShadow: "0px 1px 3px rgba(0, 0, 0, 0.1)",
            mb: 2,
          }}
        >
          <CardContent>
            <Typography
              variant="subtitle1"
              fontWeight="bold"
              sx={{ display: "flex", alignItems: "center", mb: 2 }}
            >
              <TrendingUpIcon sx={{ mr: 1, color: "#4caf50" }} />
              Revenue Forecast (2026–2030)
            </Typography>
            <Box>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={revenueData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="year" />
                  <YAxis tickFormatter={(val) => `$${val}M`} domain={[0, 60]} />
                  <Tooltip formatter={(val) => [`$${val}M`, "Revenue"]} />
                  <Bar
                    dataKey="revenue"
                    fill="#2979ff"
                    radius={[6, 6, 0, 0]}
                    barSize={40}
                  />
                </BarChart>
              </ResponsiveContainer>
            </Box>
          </CardContent>
        </Card>
        <Card
          sx={{ borderRadius: 2, boxShadow: "0px 1px 3px rgba(0, 0, 0, 0.1)" }}
        >
          <CardContent>
            <Typography
              variant="subtitle1"
              fontWeight="bold"
              sx={{ display: "flex", alignItems: "center", mb: 2 }}
            >
              <RadarIcon sx={{ mr: 1, color: "#4caf50" }} />
              Market Opportunity
            </Typography>
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={marketData}
                  dataKey="value"
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  label={({ name, value }) => `${name}: $${value}`}
                >
                  {marketData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index]} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );
};

export default DealNoteSummary;
