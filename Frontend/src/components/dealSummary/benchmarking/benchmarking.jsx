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
import RadarIcon from "@mui/icons-material/Radar";

import { BENCHMARKING_DATA } from "./constants";

export default function BenchmarkingTable() {
  return (
    <Box sx={{ p: 2, border: "1px solid #e0e0e0", borderRadius: 4 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 2 }}>
        <Box>
          <Box sx={{ display: "flex", alignItems: "center" }}>
            <RadarIcon sx={{ fontSize: 24, color: "blue", mr: 1 }} />
            <Typography sx={{ fontSize: 18, fontWeight: "bold" }}>
              Competitive Benchmarking
            </Typography>
          </Box>
          <Typography sx={{ fontSize: 14, color: "#666666" }}>
            Evaluate where your startup stands in the market
          </Typography>
        </Box>
        <Box sx={{ textAlign: "center" }}>
          <Typography sx={{ fontWeight: 600, fontSize: 18 }}>45%</Typography>
          <Typography sx={{ fontSize: 14, color: "#666666" }}>
            Overall Percentile
          </Typography>
        </Box>
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
                <Typography fontWeight="bold">Metric</Typography>
              </TableCell>
              <TableCell align="center">
                <Typography fontWeight="bold">Company</Typography>
              </TableCell>
              <TableCell align="center">
                <Typography fontWeight="bold">Sector Median</Typography>
              </TableCell>
              <TableCell align="center">
                <Typography fontWeight="bold">Percentile</Typography>
              </TableCell>
              <TableCell align="center">
                <Typography fontWeight="bold">Performance</Typography>
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {BENCHMARKING_DATA.map((row, index) => (
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
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}
