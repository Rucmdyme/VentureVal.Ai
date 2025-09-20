import React, { useState } from "react";
import { Box, Typography, Button, Grid, Chip, Stack } from "@mui/material";
import DownloadIcon from "@mui/icons-material/Download";
import { ArrowBack } from "@mui/icons-material";
import LocationOnIcon from "@mui/icons-material/LocationOn";
import EventIcon from "@mui/icons-material/Event";
import InvestmentScore from "../../components/investmentScore";
import CustomTabs from "../../components/customTabs";
import { tabsConfig } from "./constant";
import {
  marketData,
  revenueData,
} from "../../components/dealSummary/constants";
import DealNoteSummary from "../../components/dealSummary/dealSummary";
import { useNavigate } from "react-router-dom";
import BenchmarkingTable from "../../components/dealSummary/benchmarking/benchmarking";

export default function Dashboard() {
  const [tab, setTab] = useState("summary");
  const navigate = useNavigate();

  return (
    <Box sx={{ p: 2, background: "#fafafa" }}>
      <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
        <ArrowBack
          sx={{ mr: 1, cursor: "pointer", fontSize: 18 }}
          onClick={() => navigate("/")}
        />
        <Typography>Back to Upload</Typography>
        <Button
          sx={{
            ml: "auto",
            bgcolor: "black",
            color: "white",
            borderRadius: 2,
            textTransform: "none",
          }}
          size="small"
          variant="outlined"
          startIcon={<DownloadIcon />}
        >
          Download Report
        </Button>
      </Box>
      <Box
        sx={{
          mb: 3,
          backgroundImage: "linear-gradient(to right,#e9f2ff,#dce9ff)",
          borderRadius: 4,
          border: "1px solid #b3ccef",
          p: 2,
        }}
      >
        <Grid container spacing={2}>
          <Grid item size={{ xs: 12, md: 8.5 }}>
            <Box>
              <Typography sx={{ fontSize: 24, fontWeight: 600, mb: 0.5 }}>
                TechStart AI
              </Typography>
              <Stack direction="row" spacing={1}>
                <Chip
                  size="small"
                  label="AI-Powered SaaS Platform"
                  variant="outlined"
                  sx={{
                    color: "rgba(156, 39, 176, 1)",
                    borderColor: "rgba(156, 39, 176, 0.5)",
                    backgroundColor: "rgba(156, 39, 176, 0.04)",
                  }}
                />
                <Chip
                  size="small"
                  label="Series A"
                  variant="outlined"
                  sx={{
                    color: "rgba(156, 39, 176, 1)",
                    borderColor: "rgba(156, 39, 176, 0.5)",
                    backgroundColor: "rgba(156, 39, 176, 0.04)",
                  }}
                />
              </Stack>
              <Stack
                direction="row"
                spacing={3}
                alignItems="center"
                sx={{ color: "#444444", fontSize: 14, my: 1 }}
              >
                <Stack direction="row" spacing={0.5} alignItems="center">
                  <LocationOnIcon sx={{ fontSize: 18 }} />
                  <Typography variant="body2">Bangalore, India</Typography>
                </Stack>
                <Stack direction="row" spacing={0.5} alignItems="center">
                  <EventIcon sx={{ fontSize: 18 }} />
                  <Typography variant="body2">Founded Q4 2023</Typography>
                </Stack>
              </Stack>
            </Box>
            <Typography sx={{ pr: 16, mt: 4, fontSize: 14 }}>
              Sia operates in the high-growth AI/ML, Data Analytics, and
              Enterprise SaaS sectors, aiming to provide advanced data solutions
              for businesses. As a seed-stage company, it targets enterprises
              seeking to leverage data for improved decision-making and
              operational efficiency. While specific products are not detailed,
              its focus is likely on platforms or tools that streamline data
              analysis and machine learning integration. With 6 existing
              customers, Sia is attempting to establish its market presence,
              despite currently reporting no revenue. The competitive landscape
              includes established players like Alteryx and Dataiku,
              necessitating a strong differentiation strategy to capture a share
              of the $300 billion market.
            </Typography>
          </Grid>
          <Grid
            item
            size={{ xs: 12, md: 3.5 }}
            sx={{ alignItems: "center", display: "flex" }}
          >
            <Box>
              <Box
                sx={{
                  mb: 4,
                  display: "flex",
                  alignItems: "center",
                }}
              >
                <Chip
                  size="small"
                  label="CONSIDER"
                  color="primary"
                  sx={{ p: 0.5, fontSize: 12, mr: 2 }}
                />
                <Typography sx={{ fontSize: 16 }}>
                  Investment Recommendation
                </Typography>
              </Box>
              <InvestmentScore score={8.1} />
            </Box>
          </Grid>
        </Grid>
      </Box>

      <CustomTabs tab={tab} setTab={setTab} tabsConfig={tabsConfig} />

      {tab === "summary" && (
        <DealNoteSummary revenueData={revenueData} marketData={marketData} />
      )}
      {tab === "benchmarks" && <BenchmarkingTable />}
    </Box>
  );
}
