import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import TrackChangesIcon from "@mui/icons-material/TrackChanges";
import DescriptionIcon from "@mui/icons-material/Description";
import CallIcon from "@mui/icons-material/Call";
import MailOutlineIcon from "@mui/icons-material/MailOutline";

export const getMuiIcons = (props) => {
  const { iconName = "", color = "#2979ff", fontSize = "24px" } = props;

  if (iconName === "trending_up") {
    return <TrendingUpIcon style={{ fontSize: fontSize, color: color }} />;
  }
  if (iconName === "track_changes") {
    return <TrackChangesIcon style={{ fontSize: fontSize, color: color }} />;
  }
  if (iconName === "description") {
    return <DescriptionIcon style={{ fontSize: fontSize, color: color }} />;
  }
  if (iconName === "call") {
    return <CallIcon style={{ fontSize: fontSize, color: color }} />;
  }
  if (iconName === "mail_outline") {
    return <MailOutlineIcon style={{ fontSize: fontSize, color: color }} />;
  }

  return null;
};
