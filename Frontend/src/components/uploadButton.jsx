import { Button, CircularProgress, Box } from "@mui/material";

export default function UploadButton({ uploading, handleUpload, isDisabled }) {
  return (
    <Box sx={{ position: "relative", display: "inline-flex" }}>
      <Button
        variant="contained"
        sx={{ borderRadius: 2, bgcolor: "#2979ff", minWidth: 200 }}
        onClick={handleUpload}
        disabled={isDisabled}
      >
        {uploading ? "Uploading documents" : "Get Deal Notes"}
      </Button>

      {uploading && (
        <CircularProgress
          size={24}
          sx={{
            color: "#2979ff",
            position: "absolute",
            top: "50%",
            left: "50%",
            marginTop: "-12px",
            marginLeft: "-12px",
          }}
        />
      )}
    </Box>
  );
}
