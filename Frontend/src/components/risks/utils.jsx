import AttachMoneyIcon from "@mui/icons-material/AttachMoney";
import GroupIcon from "@mui/icons-material/Group";
import BusinessIcon from "@mui/icons-material/Business";
import RocketLaunchIcon from "@mui/icons-material/RocketLaunch";
import TrendingDownIcon from "@mui/icons-material/TrendingDown";

export const categoryMap = {
  financial: { title: "Financial Risk", icon: <AttachMoneyIcon /> },
  market: { title: "Market Risk", icon: <TrendingDownIcon /> },
  team: { title: "Team Risk", icon: <GroupIcon /> },
  product: { title: "Product Risk", icon: <RocketLaunchIcon /> },
  operational: { title: "Operational Risk", icon: <BusinessIcon /> },
};

export const getSeverityLabel = (avg) => {
  if (avg >= 8) return "Critical";
  if (avg >= 5) return "High";
  if (avg > 3) return "Medium";
  return "Low";
};

export const severityColors = {
  Low: "success",
  Medium: "#f9a825",
  High: "warning",
  Critical: "error",
};

export const transformRisks = (risk) => {
  return Object.entries(risk)
    .map(([key, items], idx) => {
      if (!items || items.length === 0) return null; // skip empty

      const { title, icon } = categoryMap[key] || {};
      const scores = items.map((i) => i.severity || 0);
      const avgScore =
        scores.reduce((sum, val) => sum + val, 0) / (scores.length || 1);

      return {
        id: idx + 1,
        title,
        icon,
        severity: getSeverityLabel(avgScore),
        score: Number(avgScore.toFixed(1)),
        details: items.map((i) => i.type),
      };
    })
    .filter(Boolean); // remove nulls
};
