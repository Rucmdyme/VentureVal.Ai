import React, { useRef, useState } from "react";
import {
  Box,
  Button,
  Card,
  CardContent,
  Grid,
  Typography,
} from "@mui/material";
import logo from "../../assets/logo.jpg";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import { ref, uploadBytes } from "firebase/storage";
import { v4 as uuidv4 } from "uuid";
import { storage } from "../../firebase/firebaseconfig";
import WeightsSection from "../../components/weightSection/weightsSection";
import FileUpload from "../../components/fileUpload";
import { materialTypes, whatYouWllGet } from "./constants";
import { PRESETS } from "../../components/weightSection/constants";
import { getMuiIcons } from "../../components/getMuiIcons";
import ProgressTracker from "./progressTracker";

function HomePage() {
  const [weights, setWeights] = useState(PRESETS["Default (Custom)"]);
  const [preset, setPreset] = useState("Default (Custom)");
  const [selectedFiles, setSelectedFiles] = useState({
    pitchDeck: [],
    callTranscript: [],
    founderUpdate: [],
    emailComm: [],
  });
  const [showAnalyzing, setShowAnalyzing] = useState(false);
  const [uploading, setUploading] = useState(false);
  const uploadRef = useRef(null);

  const handleScroll = () => {
    uploadRef.current.scrollIntoView({ behavior: "smooth" });
  };

  const handleFileChange = (key, files) => {
    setSelectedFiles((prev) => ({ ...prev, [key]: files }));
  };
  const handleUpload = async () => {
    const total = Object.values(weights).reduce((a, b) => a + b, 0);
    if (total !== 100) {
      alert("Total weights must equal 100%");
      return;
    }
    setUploading(true);
    const uniqueId = uuidv4();
    const uploadPromises = Object.entries(selectedFiles).map(([key, file]) => {
      if (file?.length) {
        const fileData = file[0];
        const fileRef = ref(
          storage,
          `Deal Material/${uniqueId}/${key}-${fileData.name}`
        );
        return uploadBytes(fileRef, fileData);
      }
      return null;
    });

    const results = await Promise.all(uploadPromises.filter(Boolean));
    setUploading(false);
    setShowAnalyzing(true);
    console.log("All uploads done:", results);
  };

  if (showAnalyzing) {
    return <ProgressTracker />;
  }

  return (
    <Box sx={{ mx: 2 }}>
      <Box
        sx={{
          py: 10,
        }}
      >
        <Grid container spacing={{ xs: 8, md: 24 }} alignItems="center">
          <Grid item size={{ xs: 12, md: 5 }}>
            <Typography
              sx={{ fontWeight: "bold", fontSize: { xs: 28, md: 40 } }}
              mb={2}
            >
              Transform Your Deal Flow with{" "}
              <Box component="span" color="#2979ff">
                AI-Powered Analysis
              </Box>
            </Typography>
            <Typography sx={{ color: "#666666" }} mb={3}>
              Upload pitch decks, call transcripts, founder updates, and emails
              to generate structured deal notes instantly.
            </Typography>
            <Button
              variant="contained"
              size="large"
              onClick={handleScroll}
              sx={{ borderRadius: 2, bgcolor: "#2979ff" }}
              endIcon={<ArrowForwardIcon />}
            >
              Upload Deal Materials
            </Button>
          </Grid>

          <Grid item size={{ xs: 12, md: 7 }}>
            <Box
              component="img"
              src={logo}
              alt="AI Lightbulb"
              sx={{
                width: "100%",
                borderRadius: 3,
                boxShadow: 3,
              }}
            />
          </Grid>
        </Grid>
      </Box>

      <Box
        ref={uploadRef}
        sx={{ py: 4, px: { xs: 2, md: 8 }, bgcolor: "#FAFAFA" }}
      >
        <Typography
          align="center"
          sx={{ fontSize: 24, fontWeight: "bold", mb: 1 }}
        >
          Upload Your Deal Materials
        </Typography>
        <Typography align="center" sx={{ color: "#666666", mb: 6 }}>
          Drop your documents below and let our Al analyze them to generate
          comprehensive deal notes
        </Typography>
        <Grid container spacing={4}>
          {materialTypes.map((item) => (
            <Grid item size={{ xs: 12, md: 6 }} key={item.key}>
              <Card
                variant="outlined"
                sx={{
                  textAlign: "center",
                  px: 4,
                  py: 1,
                  borderRadius: 3,
                }}
              >
                <CardContent sx={{ flexGrow: 1 }}>
                  <Box
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      mb: 4,
                    }}
                  >
                    {getMuiIcons({
                      iconName: item.icon,
                    })}
                    <Box textAlign="left" ml={1.5}>
                      <Typography
                        sx={{ fontSize: 16, fontWeight: 600, lineHeight: 1.2 }}
                      >
                        {item.title}
                      </Typography>
                      <Typography sx={{ fontSize: 14, color: "#666666" }}>
                        {item.desc}
                      </Typography>
                    </Box>
                  </Box>
                  <FileUpload
                    uploadKey={item.key}
                    formats={item.formats}
                    files={selectedFiles[item.key]}
                    onFileChange={(files) => handleFileChange(item.key, files)}
                  />
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
        <Box sx={{ mt: 4 }}>
          <Typography
            align="center"
            sx={{ fontSize: 24, fontWeight: "bold", mb: 1 }}
          >
            Customize Your Investment Weights
          </Typography>
          <Typography variant="body1" align="center" color="text.secondary">
            Adjust the importance of each factor to see your real-time deal
            score.
          </Typography>
          <WeightsSection
            weights={weights}
            setWeights={setWeights}
            preset={preset}
            setPreset={setPreset}
          />
        </Box>

        <Box textAlign="center">
          <Button
            variant="contained"
            size="large"
            sx={{ borderRadius: 2, bgcolor: "#2979ff" }}
            onClick={handleUpload}
            disabled={uploading}
          >
            {uploading ? "Uploading documents..." : "Get Deal Notes"}
          </Button>
        </Box>
      </Box>

      <Box sx={{ py: 4, px: { xs: 2, md: 20 } }}>
        <Typography
          align="center"
          sx={{ fontSize: 24, fontWeight: "bold", mb: 1 }}
        >
          What You'll Get
        </Typography>
        <Typography align="center" mb={6} sx={{ color: "#666666" }}>
          Comprehensive analysis tailored for investment decisions
        </Typography>
        <Grid container spacing={4}>
          {whatYouWllGet.map((item, i) => (
            <Grid item size={{ xs: 12, md: 4 }} key={i}>
              <Card
                variant="outlined"
                sx={{
                  p: 4,
                  borderRadius: 3,
                }}
              >
                <Typography sx={{ fontSize: 18, fontWeight: 600, mb: 1 }}>
                  {item.title}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {item.desc}
                </Typography>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Box>
    </Box>
  );
}

export default HomePage;
