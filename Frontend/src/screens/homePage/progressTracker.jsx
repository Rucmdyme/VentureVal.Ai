import React, { useEffect, useState } from "react";
import {
  Box,
  Typography,
  LinearProgress,
  Stepper,
  Step,
  StepLabel,
  Container,
  Paper,
} from "@mui/material";
import { CheckCircle } from "@mui/icons-material";
import { processingSteps } from "./constants";

export default function ProgressTracker({ onComplete }) {
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState(0);

  const totalDuration = processingSteps.reduce(
    (sum, step) => sum + step.duration,
    0
  );

  useEffect(() => {
    const handleBeforeUnload = (event) => {
      event.preventDefault();
      event.returnValue = "";
    };

    window.addEventListener("beforeunload", handleBeforeUnload);

    return () => {
      window.removeEventListener("beforeunload", handleBeforeUnload);
    };
  }, []);

  useEffect(() => {
    const startTime = Date.now();

    const interval = setInterval(() => {
      const elapsed = Date.now() - startTime;
      const newProgress = Math.min((elapsed / totalDuration) * 100, 100);
      setProgress(newProgress);

      let accumulated = 0;
      for (let i = 0; i < processingSteps.length; i++) {
        accumulated += processingSteps[i].duration;
        if (elapsed < accumulated) {
          setCurrentStep(i);
          break;
        }
        if (i === processingSteps.length - 1) {
          setCurrentStep(processingSteps.length - 1);
        }
      }

      if (elapsed >= totalDuration) {
        clearInterval(interval);
        setProgress(100);
        setCurrentStep(processingSteps.length - 1);
        if (onComplete) onComplete();
      }
    }, 100);

    return () => clearInterval(interval);
  }, [totalDuration, onComplete]);

  const currentStepData = processingSteps[currentStep];
  const CurrentStepIcon = currentStepData?.icon || CheckCircle;

  return (
    <Container maxWidth="md" sx={{ my: 12, textAlign: "center" }}>
      <Typography sx={{ fontSize: 28, fontWeight: "bold", mb: 1 }}>
        Analyzing Your Documents
      </Typography>
      <Typography sx={{ color: "#666666" }}>
        Our AI is processing your files to generate comprehensive deal notes
      </Typography>

      <Paper
        elevation={3}
        sx={{ p: 4, my: 4, borderRadius: 4, textAlign: "center" }}
      >
        <Box display="flex" alignItems="center" justifyContent="center" mb={2}>
          <Box
            sx={{
              width: 48,
              height: 48,
              bgcolor: "#E3F2FD",
              borderRadius: "50%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              mr: 2,
            }}
          >
            <CurrentStepIcon color="primary" />
          </Box>
          <Box>
            <Typography sx={{ fontWeight: 500, fontSize: 18 }}>
              {currentStepData?.label}
            </Typography>
            <Typography sx={{ color: "#666666", fontSize: 14 }}>
              {currentStepData?.description}
            </Typography>
          </Box>
        </Box>

        <Box sx={{ mt: 3 }}>
          <Box display="flex" justifyContent="space-between">
            <Typography sx={{ color: "#666666", fontSize: 14 }}>
              Overall Progress
            </Typography>
            <Typography sx={{ fontWeight: 400, fontSize: 14 }}>
              {Math.round(progress)}%
            </Typography>
          </Box>
          <LinearProgress
            variant="determinate"
            value={progress}
            sx={{ height: 10, borderRadius: 5, mt: 1 }}
          />
        </Box>
      </Paper>

      <Paper elevation={2} sx={{ p: 3, borderRadius: 3 }}>
        <Typography sx={{ fontWeight: 500, mb: 2, fontSize: 18 }}>
          Processing Pipeline
        </Typography>
        <Stepper activeStep={currentStep} alternativeLabel>
          {processingSteps.map((step, index) => {
            const StepIcon = step.icon;
            const isComplete = index < currentStep;
            const isActive = index === currentStep;

            return (
              <Step key={step.id}>
                <StepLabel
                  slots={{
                    stepIcon: () =>
                      isComplete ? (
                        <CheckCircle color="success" />
                      ) : (
                        <StepIcon color={isActive ? "primary" : "disabled"} />
                      ),
                  }}
                >
                  {step.label}
                </StepLabel>
              </Step>
            );
          })}
        </Stepper>
      </Paper>

      <Typography
        sx={{ mt: 4, fontStyle: "italic", color: "#666666", fontSize: 14 }}
      >
        This usually takes 2–3 minutes depending on document size and complexity
      </Typography>
    </Container>
  );
}
