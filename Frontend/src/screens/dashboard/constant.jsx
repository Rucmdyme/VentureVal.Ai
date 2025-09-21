import ShowChartIcon from "@mui/icons-material/ShowChart";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import BarChartIcon from "@mui/icons-material/BarChart";
import LightbulbIcon from "@mui/icons-material/Lightbulb";

export const tabsConfig = [
  {
    key: "summary",
    label: "Summary",
    icon: <ShowChartIcon fontSize="small" />,
  },
  { key: "risk", label: "Risk", icon: <WarningAmberIcon fontSize="small" /> },
  {
    key: "benchmarks",
    label: "Benchmarks",
    icon: <BarChartIcon fontSize="small" />,
  },
  {
    key: "insights",
    label: "Insights",
    icon: <LightbulbIcon fontSize="small" />,
  },
];
