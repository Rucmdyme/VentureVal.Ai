import React from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Typography,
  Box,
} from "@mui/material";

import { performanceColors } from "./constants";
import { snakeCaseToTitleCase } from "../../../utils";
import NoDataComponent from "../../noDataComponent";

const BenchmarkingTable = ({ benchMarking }) => {
  const mapBenchmarkingData = (percentiles) => {
    return Object.entries(percentiles || {}).map(([metric, data]) => ({
      metric: snakeCaseToTitleCase(metric),
      company: data?.value,
      sector: data?.benchmark_median,
      percentile: `${data?.percentile}%`,
      performance: {
        label: data.relative_performance,
        ...(performanceColors[data.relative_performance] || {}),
      },
    }));
  };

  const benchmarkingData = mapBenchmarkingData(benchMarking.percentiles);

  return (
    <Box sx={{ p: 2, border: "1px solid #e0e0e0", borderRadius: 4 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 2 }}>
        <Box>
          <Typography sx={{ fontSize: 18, fontWeight: "bold" }}>
            Competitive Benchmarking
          </Typography>

          <Typography sx={{ fontSize: 14, color: "#666666" }}>
            Evaluate where your startup stands in the market
          </Typography>
        </Box>
        {benchMarking?.overall_score?.score && (
          <Box sx={{ textAlign: "center" }}>
            <Typography sx={{ fontWeight: 600, fontSize: 18 }}>
              {`${benchMarking?.overall_score?.score}%`}
            </Typography>
            <Typography sx={{ fontSize: 14, color: "#666666" }}>
              Overall Percentile
            </Typography>
          </Box>
        )}
      </Box>
      <TableContainer
        component={Paper}
        sx={{
          borderRadius: 4,
          boxShadow: "0px 1px 3px rgba(0, 0, 0, 0.1)",
        }}
      >
        <Table>
          <TableHead>
            <TableRow>
              <TableCell align="center">
                <Typography fontWeight="550">Metric</Typography>
              </TableCell>
              <TableCell align="center">
                <Typography fontWeight="550">Company</Typography>
              </TableCell>
              <TableCell align="center">
                <Typography fontWeight="550">Sector Median</Typography>
              </TableCell>
              <TableCell align="center">
                <Typography fontWeight="550">Percentile</Typography>
              </TableCell>
              <TableCell align="center">
                <Typography fontWeight="550">Performance</Typography>
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {benchmarkingData?.length ? (
              benchmarkingData.map((row, index) => (
                <TableRow
                  key={index}
                  sx={{
                    "&:hover": {
                      backgroundColor: "rgba(0, 0, 0, 0.04)",
                    },
                  }}
                >
                  <TableCell align="center">{row.metric}</TableCell>
                  <TableCell align="center">{row.company}</TableCell>
                  <TableCell align="center">{row.sector}</TableCell>
                  <TableCell align="center">{row.percentile}</TableCell>
                  <TableCell align="center">
                    <Chip
                      label={row.performance.label}
                      sx={{
                        color: row.performance.color,
                        bgcolor: row.performance.backgroundColor,
                        border: `1px solid ${row.performance.color}`,
                      }}
                      variant="outlined"
                    />
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={5} align="center">
                  <NoDataComponent />
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default BenchmarkingTable;
