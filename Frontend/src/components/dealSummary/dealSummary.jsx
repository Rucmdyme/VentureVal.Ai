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
import { COLORS, formatCurrency } from "./constants";
import { snakeCaseToTitleCase } from "../../utils";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import EqualizerIcon from "@mui/icons-material/Equalizer";
import RadarIcon from "@mui/icons-material/Radar";
import AttachMoneyIcon from "@mui/icons-material/AttachMoney";

const DealNoteSummary = ({ dealNote, weightedScores }) => {
  const summaryStats = dealNote?.summary_stats || {};
  const marketData = [
    {
      name: "Serviceable Obtainable Market",
      value: summaryStats?.som || 0,
    },
    {
      name: "Serviceable Addressable Market",
      value: summaryStats?.sam || 0,
    },
    {
      name: "Total Addressable Market",
      value: summaryStats?.tam || 0,
    },
  ];

  let revenueKey = null;
  let revenueValue = null;

  if (summaryStats?.monthly_revenue) {
    revenueKey = "Monthly Revenue";
    revenueValue = summaryStats.monthly_revenue;
  } else if (summaryStats?.annual_revenue) {
    revenueKey = "Annual Revenue";
    revenueValue = summaryStats.annual_revenue;
  } else if (summaryStats?.revenue) {
    revenueKey = "Revenue";
    revenueValue = summaryStats.revenue;
  }
  const keyMetrics = {
    ...(revenueKey ? { [revenueKey]: revenueValue } : {}),
    "Market size": summaryStats?.market_size,
    "Growth Rate": summaryStats?.growth_rate,
    "Burn Rate": summaryStats?.burn_rate,
    "Runway Months": summaryStats?.runway_months,
    "Funding Raised": summaryStats?.funding_raised,
    "Funding Seeking": summaryStats?.funding_seeking,
    Valuation: summaryStats?.valuation,
    "Churn Rate": summaryStats?.churn_rate,
    Customers: summaryStats?.customers,
    "Team Size": summaryStats?.team_size,
    LTV: summaryStats?.ltv,
    CAC: summaryStats?.cac,
    MRR: summaryStats?.mrr,
    ARR: summaryStats?.arr,
    "Gross Margin": summaryStats?.gross_margin,
  };

  const filteredMetrics = Object.entries(keyMetrics || {})
    .filter(
      ([, value]) => value !== null && value !== undefined && value !== ""
    )
    .slice(0, 8);
  return (
    <Grid container spacing={2} mb={3}>
      <Grid item size={{ xs: 12, md: 12 }}>
        <Card variant="outlined" sx={{ borderRadius: 3, p: 2 }}>
          <CardContent>
            <Typography sx={{ mb: 2, fontSize: 18, fontWeight: "bold" }}>
              Executive Summary
            </Typography>

            <Grid container spacing={4}>
              {dealNote?.deal_summary?.length && (
                <Grid item size={{ xs: 12, md: 9 }} sx={{ pr: 20 }}>
                  {dealNote?.deal_summary?.map((summary, idx) => {
                    return (
                      <Typography
                        variant="body2"
                        sx={{
                          mb: idx === dealNote.deal_summary.length - 1 ? 0 : 2,
                        }}
                      >
                        {summary}
                      </Typography>
                    );
                  })}
                </Grid>
              )}

              <Grid item size={{ xs: 12, md: 3 }}>
                {dealNote?.positive_insights?.length && (
                  <Box mb={2}>
                    <Typography sx={{ fontSize: 16, fontWeight: "bold" }}>
                      Key Strengths
                    </Typography>
                    <List dense>
                      {dealNote.positive_insights
                        .slice(0, 4)
                        .map((strength, idx) => (
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
                )}

                {dealNote?.negative_insights?.length && (
                  <Box>
                    <Typography sx={{ fontSize: 16, fontWeight: "bold" }}>
                      Key Concerns
                    </Typography>
                    <List dense>
                      {dealNote.negative_insights
                        .slice(0, 4)
                        .map((concern, idx) => (
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
                )}
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      </Grid>
      <Grid item size={{ xs: 12, md: 3.5 }}>
        {filteredMetrics?.length && (
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
              {filteredMetrics.map(([key, value]) => (
                <Box
                  key={key}
                  sx={{
                    display: "flex",
                    justifyContent: "space-between",
                    mt: 2,
                  }}
                >
                  <Typography sx={{ fontSize: 14, color: "#666666" }}>
                    {key}
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
        )}
        {Object.keys(weightedScores?.dimension_scores || {})?.length && (
          <Card
            sx={{
              borderRadius: 2,
              boxShadow: "0px 1px 3px rgba(0, 0, 0, 0.1)",
            }}
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
              {Object.entries(weightedScores?.dimension_scores || {}).map(
                ([key, value]) => (
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
                )
              )}
            </CardContent>
          </Card>
        )}
      </Grid>

      <Grid item size={{ xs: 12, md: 8.5 }}>
        {summaryStats?.revenue_projections?.length && (
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
                Revenue Forecast
              </Typography>
              <Box>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={summaryStats.revenue_projections}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="year" />
                    <YAxis tickFormatter={formatCurrency} />
                    <Tooltip
                      formatter={(val) => [formatCurrency(val), "Revenue"]}
                    />
                    <Bar
                      dataKey="number"
                      fill="#2979ff"
                      radius={[6, 6, 0, 0]}
                      barSize={40}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </Box>
            </CardContent>
          </Card>
        )}
        {summaryStats?.som && summaryStats?.sam && summaryStats?.tam && (
          <Card
            sx={{
              borderRadius: 2,
              boxShadow: "0px 1px 3px rgba(0, 0, 0, 0.1)",
            }}
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
        )}
      </Grid>
    </Grid>
  );
};

export default DealNoteSummary;
