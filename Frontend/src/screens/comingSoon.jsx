import { Box, Typography } from "@mui/material";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";

export default function ComingSoon() {
  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        height: "100vh",
        textAlign: "center",
      }}
    >
      <PictureAsPdfIcon sx={{ fontSize: 80, color: "error.main", mb: 2 }} />
      <Typography
        variant="h3"
        sx={{ fontWeight: 700, color: "text.secondary", mb: 1 }}
      >
        Coming Soon
      </Typography>
      <Typography variant="body1" color="text.disabled">
        Download PDF feature will be available shortly.
      </Typography>
    </Box>
  );
}
