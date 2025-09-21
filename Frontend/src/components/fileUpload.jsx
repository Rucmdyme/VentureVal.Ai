import React from "react";
import {
  Box,
  Typography,
  Button,
  IconButton,
  List,
  ListItem,
  ListItemText,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";

function FileUpload({
  uploadKey,
  onFileChange,
  formats = ".pdf,.txt,.jpg,.jpeg,.png",
  files = [],
  maxFiles = 1,
}) {
  const inputId = `fileInput-${uploadKey}`;
  const handleFiles = (newFiles) => {
    const fileList = Array.from(newFiles).slice(0, maxFiles);
    onFileChange(fileList);
  };

  const handleBrowse = (e) => {
    handleFiles(e.target.files);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    handleFiles(e.dataTransfer.files);
  };

  const removeFile = (index) => {
    const updated = files.filter((_, i) => i !== index);
    onFileChange(updated);
  };

  return (
    <Box
      sx={{
        border: "2px dashed",
        borderColor: "grey.400",
        borderRadius: 2,
        p: 4,
        bgcolor: "#FAFAFA",
        textAlign: "center",
        cursor: "pointer",
      }}
      onDragOver={(e) => e.preventDefault()}
      onDrop={handleDrop}
    >
      <input
        type="file"
        accept=".pdf,.txt,.jpg,.jpeg,.png"
        style={{ display: "none" }}
        id={inputId}
        onChange={handleBrowse}
      />

      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
        Drag and drop your file here,{" "}
        {files.length < maxFiles && (
          <label htmlFor={inputId} style={{ cursor: "pointer" }}>
            <Button component="span" size="small" sx={{ color: "#2979ff" }}>
              Browse
            </Button>
          </label>
        )}
      </Typography>

      <Typography variant="caption" color="text.disabled">
        {formats} (Max {maxFiles} file{maxFiles > 1 ? "s" : ""})
      </Typography>

      {files.length > 0 && (
        <List dense sx={{ mt: 2, bgcolor: "white", borderRadius: 2 }}>
          {files.map((file, idx) => (
            <ListItem
              key={idx}
              secondaryAction={
                <IconButton
                  edge="end"
                  size="small"
                  onClick={() => removeFile(idx)}
                >
                  <CloseIcon fontSize="small" />
                </IconButton>
              }
            >
              <ListItemText primary={file.name} />
            </ListItem>
          ))}
        </List>
      )}
    </Box>
  );
}

export default FileUpload;
