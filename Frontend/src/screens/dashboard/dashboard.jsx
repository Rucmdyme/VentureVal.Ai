import React, { useState } from "react";
import { Box, Typography, Button, Grid, Chip, Stack } from "@mui/material";
import DownloadIcon from "@mui/icons-material/Download";
import { ArrowBack } from "@mui/icons-material";
import LocationOnIcon from "@mui/icons-material/LocationOn";
import EventIcon from "@mui/icons-material/Event";
import InvestmentScore from "../../components/investmentScore";
import CustomTabs from "../../components/customTabs";
import { tabsConfig } from "./constant";
import DealNoteSummary from "../../components/dealSummary/dealSummary";
import { useLocation, useNavigate } from "react-router-dom";
import BenchmarkingTable from "../../components/dealSummary/benchmarking/benchmarking";
import Insights from "../../components/insights/insights";
import RiskAssessmentRadar from "../../components/risks/riskAssesmentRadar";
import ChatBot from "../../components/chatbot/Chatbot";

export default function Dashboard() {
  const location = useLocation();
  const { finalAnalysis, analysisId } = location.state || {};
  const {
    benchmarking,
    deal_note: dealNote,
    risk_assessment: riskAssessment,
    weighted_scores: weightedScores,
  } = finalAnalysis;

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
                {dealNote?.company_name || "NA"}
              </Typography>
              <Stack direction="row" spacing={1}>
                {finalAnalysis?.deal_note?.summary_stats?.sector && (
                  <Chip
                    size="small"
                    label={finalAnalysis.deal_note.summary_stats.sector}
                    variant="outlined"
                    sx={{
                      color: "rgba(156, 39, 176, 1)",
                      borderColor: "rgba(156, 39, 176, 0.5)",
                      backgroundColor: "rgba(156, 39, 176, 0.04)",
                    }}
                  />
                )}
                {finalAnalysis?.deal_note?.summary_stats?.stage && (
                  <Chip
                    size="small"
                    label={finalAnalysis.deal_note.summary_stats.stage}
                    variant="outlined"
                    sx={{
                      color: "rgba(156, 39, 176, 1)",
                      borderColor: "rgba(156, 39, 176, 0.5)",
                      backgroundColor: "rgba(156, 39, 176, 0.04)",
                    }}
                  />
                )}
              </Stack>
              <Stack
                direction="row"
                spacing={3}
                alignItems="center"
                sx={{ color: "#444444", fontSize: 14, my: 1 }}
              >
                {dealNote?.summary_stats?.geography && (
                  <Stack
                    direction="row"
                    spacing={0.5}
                    alignItems="center"
                    sx={{ maxWidth: "620px" }}
                  >
                    <LocationOnIcon sx={{ fontSize: 18 }} />
                    <Typography variant="body2">
                      {dealNote?.summary_stats?.geography}
                    </Typography>
                  </Stack>
                )}
                {dealNote?.summary_stats?.founded_year && (
                  <Stack direction="row" spacing={0.5} alignItems="center">
                    <EventIcon sx={{ fontSize: 18 }} />
                    <Typography variant="body2">{`Founded in ${dealNote?.summary_stats?.founded_year}`}</Typography>
                  </Stack>
                )}
              </Stack>
            </Box>
            {dealNote?.company_description && (
              <Typography sx={{ pr: { xs: 0, md: 16 }, mt: 4, fontSize: 14 }}>
                {dealNote?.company_description}
              </Typography>
            )}
          </Grid>
          <Grid
            item
            size={{ xs: 12, md: 3.5 }}
            sx={{ alignItems: "center", display: "flex" }}
          >
            <Box>
              {dealNote?.summary_stats?.recommendation_tier && (
                <Box
                  sx={{
                    mb: 4,
                    display: "flex",
                    alignItems: "center",
                  }}
                >
                  <Chip
                    size="small"
                    label={dealNote?.summary_stats?.recommendation_tier}
                    sx={{
                      p: 0.5,
                      fontSize: 12,
                      mr: 2,
                      bgcolor:
                        dealNote?.summary_stats?.recommendation_tier ===
                        "CONSIDER"
                          ? "primary.main"
                          : dealNote?.summary_stats?.recommendation_tier ===
                            "PASS"
                          ? "#d32f2f"
                          : "#2e7d32",
                      color: "white",
                    }}
                  />
                  <Typography sx={{ fontSize: 16 }}>
                    Investment Recommendation
                  </Typography>
                </Box>
              )}
              {dealNote?.summary_stats?.overall_score && (
                <InvestmentScore
                  score={dealNote?.summary_stats?.overall_score}
                />
              )}
            </Box>
          </Grid>
        </Grid>
      </Box>

      <CustomTabs tab={tab} setTab={setTab} tabsConfig={tabsConfig} />

      {tab === "summary" && (
        <DealNoteSummary dealNote={dealNote} weightedScores={weightedScores} />
      )}
      {tab === "risk" && (
        <RiskAssessmentRadar riskAssessment={riskAssessment} />
      )}
      {tab === "benchmarks" && (
        <BenchmarkingTable benchMarking={benchmarking} />
      )}
      {tab === "insights" && <Insights insightsData={benchmarking?.insights} />}
      <ChatBot analysisId={analysisId} />
    </Box>
  );
}
