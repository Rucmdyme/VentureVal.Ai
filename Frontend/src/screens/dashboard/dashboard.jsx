import React, { useState } from "react";
import {
  Box,
  Typography,
  Button,
  Card,
  CardContent,
  Grid,
  Chip,
  Divider,
  Tabs,
  Tab,
} from "@mui/material";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import DownloadIcon from "@mui/icons-material/Download";

// Dummy Data
const revenueData = [
  { month: "Jan", revenue: 45000 },
  { month: "Feb", revenue: 50000 },
  { month: "Mar", revenue: 60000 },
  { month: "Apr", revenue: 72000 },
  { month: "May", revenue: 85000 },
  { month: "Jun", revenue: 100000 },
];

const marketData = [
  { name: "Serviceable Obtainable Market", value: 35 },
  { name: "Serviceable Addressable Market", value: 15000 },
  { name: "Total Addressable Market", value: 50000 },
];

const COLORS = ["#4CAF50", "#7E57C2", "#42A5F5"];

export default function Dashboard() {
  const [tab, setTab] = useState(0);

  return (
    <Box sx={{ p: 3, bgcolor: "#F9FAFB", minHeight: "100vh" }}>
      {/* Header */}
      <Box
        display="flex"
        justifyContent="space-between"
        alignItems="center"
        mb={3}
      >
        <Typography variant="h5" fontWeight="bold">
          TechStart AI
        </Typography>
        <Button variant="outlined" startIcon={<DownloadIcon />}>
          Download PDF
        </Button>
      </Box>

      {/* Score + Company Info */}
      <Grid container spacing={2} mb={3}>
        <Grid item xs={12} md={3}>
          <Card sx={{ bgcolor: "#E3F2FD" }}>
            <CardContent>
              <Typography variant="h4" fontWeight="bold" color="primary">
                8.2 / 10
              </Typography>
              <Chip label="PURSUE" color="success" sx={{ mt: 1 }} />
              <Typography variant="body2" sx={{ mt: 1 }}>
                Investment Recommendation
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={9}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary">
                Company Summary
              </Typography>
              <Typography variant="body2" sx={{ mt: 1 }}>
                TechStart AI is a B2B SaaS platform offering AI-powered
                analytics solutions to mid-market enterprises. With $1.2M ARR
                and 42% YoY growth, the startup has strong product-market fit
                across 50+ enterprise customers.
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Key Metrics */}
      <Grid container spacing={2} mb={3}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary">
                Key Metrics
              </Typography>
              <Typography>
                <b>Monthly Revenue:</b> $98K
              </Typography>
              <Typography>
                <b>Growth Rate:</b>{" "}
                <span style={{ color: "green" }}>42% YoY</span>
              </Typography>
              <Typography>
                <b>Team Size:</b> 12 employees
              </Typography>
              <Typography>
                <b>Market Position:</b> Top 15%
              </Typography>
              <Typography>
                <b>Runway:</b> 18 months
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary">
                Revenue Growth Trajectory
              </Typography>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={revenueData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" />
                  <YAxis />
                  <Tooltip />
                  <Line
                    type="monotone"
                    dataKey="revenue"
                    stroke="#2979ff"
                    strokeWidth={2}
                  />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary">
                Market Opportunity
              </Typography>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={marketData}
                    dataKey="value"
                    cx="50%"
                    cy="50%"
                    outerRadius={70}
                    label
                  >
                    {marketData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Strengths and Risks */}
      <Grid container spacing={2} mb={3}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary">
                Strengths
              </Typography>
              <ul>
                <li>Strong Product-Market Fit</li>
                <li>Experienced Team</li>
                <li>Scalable Technology</li>
              </ul>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary">
                Key Risks
              </Typography>
              <ul>
                <li>Market Competition</li>
                <li>Customer Concentration</li>
                <li>Regulatory Changes</li>
              </ul>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Tabs Section */}
      <Card>
        <CardContent>
          <Tabs value={tab} onChange={(e, v) => setTab(v)} centered>
            <Tab label="Summary" />
            <Tab label="Risks" />
            <Tab label="Benchmarks" />
            <Tab label="Recommendations" />
            <Tab label="Next Steps" />
          </Tabs>
          <Divider sx={{ my: 2 }} />
          <Typography variant="body2">
            {tab === 0 && "This is a summary of TechStart AI's analysis."}
            {tab === 1 &&
              "These are the key risks associated with TechStart AI."}
            {tab === 2 && "Benchmark comparison with industry peers."}
            {tab === 3 && "Recommended actions for investors."}
            {tab === 4 && "Next steps for follow-up analysis."}
          </Typography>
        </CardContent>
      </Card>
    </Box>
  );
}
