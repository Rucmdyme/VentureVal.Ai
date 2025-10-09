import React, { useState } from "react";
import {
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Typography,
  TextField,
  Button,
  Box,
  Card,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { CONTACT_US_CONFIG, FAQS } from "./constants";
import { toast } from "react-toastify";

const ContactUsPage = () => {
  const [messageDetails, setMessageDetails] = useState({});
  const handleChange = (key, value) => {
    setMessageDetails((prev) => {
      return { ...prev, [key]: value };
    });
  };
  const checkIsDisabled = () => {
    return CONTACT_US_CONFIG.some(
      (item) => item.required && !messageDetails[item.key]
    );
  };

  const onSend = () => {
    toast.success("Message sent successfully, we'll contact you in 24hrs");
    setMessageDetails({});
  };

  return (
    <Box sx={{ maxWidth: "800px", mx: "auto", p: 3 }}>
      <Typography
        sx={{ fontWeight: "bold", textAlign: "center", mb: 1, fontSize: 22 }}
      >
        Frequently Asked Questions
      </Typography>

      {FAQS.map((faq, index) => (
        <Accordion
          key={index}
          sx={{
            mb: 1,
            borderRadius: 2,
            "::before": {
              height: 0,
            },
          }}
        >
          <AccordionSummary
            expandIcon={<ExpandMoreIcon />}
            sx={{ borderTop: "none" }}
          >
            <Typography sx={{ color: "#1f2839d9" }}>{faq.question}</Typography>
          </AccordionSummary>
          <AccordionDetails sx={{ background: "#f9f9f9" }}>
            <Typography sx={{ fontSize: 14 }}>{faq.answer}</Typography>
          </AccordionDetails>
        </Accordion>
      ))}

      <Box sx={{ mt: 6 }}>
        <Typography
          sx={{ fontWeight: "bold", textAlign: "center", mb: 1, fontSize: 22 }}
        >
          Get in Touch
        </Typography>
        <Typography
          variant="body1"
          sx={{ color: "text.secondary", textAlign: "center", mb: 3 }}
        >
          Have questions or want to get started? Send us a message and our team
          will reach out within 24 hours.
        </Typography>

        <Card sx={{ borderRadius: 3, p: 4, boxShadow: 2 }}>
          <Box
            component="form"
            sx={{
              display: "flex",
              flexDirection: "column",
              gap: 2,
            }}
          >
            {CONTACT_US_CONFIG.map((item) => (
              <TextField
                key={item.key}
                value={messageDetails[item.key] || ""}
                label={item.label}
                multiline={item.multiline}
                rows={item.rows || 1}
                required={item.required}
                onChange={(e) => {
                  handleChange(item.key, e.target.value);
                }}
                fullWidth
              />
            ))}

            <Button
              variant="contained"
              size="large"
              onClick={onSend}
              disabled={checkIsDisabled()}
              sx={{
                background: "#2979ff",
                borderRadius: 2,
                textTransform: "none",
                mt: 1,
              }}
            >
              Send Message
            </Button>
          </Box>
        </Card>
      </Box>
    </Box>
  );
};

export default ContactUsPage;
