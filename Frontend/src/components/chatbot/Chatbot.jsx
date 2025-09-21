import React, { useState, useEffect, useRef } from "react";
import {
  Fab,
  Drawer,
  Box,
  Paper,
  Stack,
  Avatar,
  Typography,
  TextField,
  Button,
  IconButton,
  CircularProgress,
} from "@mui/material";
import ChatIcon from "@mui/icons-material/Chat";
import CloseIcon from "@mui/icons-material/Close";
import SendIcon from "@mui/icons-material/Send";
import BoltIcon from "@mui/icons-material/Bolt";

const API_ENDPOINT =
  "https://ventureval-be-1094484866096.asia-south1.run.app/agent/agent/chat";

const ChatBot = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const [suggestedQuestions, setSuggestedQuestions] = useState([
    "What are the key risk factors in my pitch deck?",
    "How does my valuation compare to similar companies?",
    "What benchmarks should I focus on?",
    "What additional information would tip the decision?",
  ]);
  const [analysisId, setAnalysisId] = useState(
    "analysis_49a4cf6c9ee845ed8753eef2b8e6d1fa"
  );

  const [showSuggestedQuestions, setShowSuggestedQuestions] = useState(false);
  const [typingInterval, setTypingInterval] = useState(null);

  const messagesEndRef = useRef(null);
  const chatDrawerRef = useRef(null);

  const getCurrentTime = () => {
    return new Date().toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  useEffect(() => {
    if (isOpen && messages.length === 0) {
      const welcomeMessage = {
        id: "welcome-message",
        text: "Hi! I'm  Dealio, your AI assistant for pitch deck analysis. I can help you understand your analysis results, provide insights, and answer questions about your startup's performance. What would you like to know?",
        sender: "bot",
        timestamp: getCurrentTime(),
        fullText:
          "Hi! I'm  Dealio, your AI assistant for pitch deck analysis. I can help you understand your analysis results, provide insights, and answer questions about your startup's performance. What would you like to know?",
        typedText:
          "Hi! I'm  Dealio, your AI assistant for pitch deck analysis. I can help you understand your analysis results, provide insights, and answer questions about your startup's performance. What would you like to know?",
      };
      setMessages([welcomeMessage]);
    }
  }, [isOpen]);

  useEffect(() => {
    if (typingInterval) {
      clearInterval(typingInterval);
    }

    const lastMessage = messages[messages.length - 1];

    if (lastMessage && lastMessage.sender === "bot" && lastMessage.isTyping) {
      let i = 0;
      const interval = setInterval(() => {
        setMessages((prevMessages) => {
          const newMessages = [...prevMessages];
          const currentMessage = newMessages[newMessages.length - 1];

          if (i < currentMessage.fullText.length) {
            currentMessage.typedText += currentMessage.fullText.charAt(i);
            i++;
          } else {
            clearInterval(interval);
            currentMessage.isTyping = false;
          }
          return newMessages;
        });
      }, 10);
      setTypingInterval(interval);
    }
    return () => {
      if (typingInterval) {
        clearInterval(typingInterval);
      }
    };
  }, [messages.length]);

  // Re-implemented scroll behavior for Case 1
  useEffect(() => {
    if (showSuggestedQuestions && !isLoading) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [showSuggestedQuestions, isLoading]);

  const handleSendMessage = async (text) => {
    if (!text.trim()) return;

    const userMessage = {
      id: Date.now(),
      text: text,
      sender: "user",
      timestamp: getCurrentTime(),
    };

    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    setInputValue("");
    setIsLoading(true);
    setShowSuggestedQuestions(false);

    try {
      const response = await fetch(API_ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: text,
          analysis_id: analysisId,
          chat_history: updatedMessages.map((msg) => ({
            role: msg.sender === "user" ? "user" : "assistant",
            content: msg.text,
          })),
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      const botMessage = {
        id: Date.now(),
        text: data.response,
        sender: "bot",
        timestamp: getCurrentTime(),
        fullText: data.response,
        typedText: "",
        isTyping: true,
      };

      setMessages((prevMessages) => [...prevMessages, botMessage]);
      setSuggestedQuestions(data.suggested_questions);
      setAnalysisId(data.analysis_id);
    } catch (error) {
      console.error("Error fetching data from API:", error);
      const errorMessage = {
        id: Date.now(),
        text: "Sorry, I couldn't get a response. Please try again.",
        sender: "bot",
        timestamp: getCurrentTime(),
        fullText: "Sorry, I couldn't get a response. Please try again.",
        typedText: "Sorry, I couldn't get a response. Please try again.",
      };
      setMessages((prevMessages) => [...prevMessages, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleBlur = (e) => {
    if (
      chatDrawerRef.current &&
      !chatDrawerRef.current.contains(e.relatedTarget)
    ) {
      setShowSuggestedQuestions(false);
    }
  };

  return (
    <>
      <Fab
        color="primary"
        aria-label="chat"
        onClick={() => setIsOpen(true)}
        sx={{
          position: "fixed",
          bottom: 20,
          right: 20,
          background: "linear-gradient(135deg, #007bff, #5a5ae5)",
          boxShadow: "0 4px 12px rgba(0, 0, 0, 0.25)",
          transition: "transform 0.3s ease",
          zIndex: 1000,
        }}
      >
        <ChatIcon />
      </Fab>

      <Drawer
        anchor="right"
        open={isOpen}
        onClose={() => setIsOpen(false)}
        variant="temporary"
        sx={{
          "& .MuiDrawer-paper": {
            width: { xs: "100%", sm: 400 },
            boxSizing: "border-box",
            borderRadius: "16px 0 0 16px",
            background: "linear-gradient(180deg, #f0f4f9 0%, #e0e8f2 100%)",
          },
        }}
      >
        <Box
          ref={chatDrawerRef}
          sx={{ height: "100%", display: "flex", flexDirection: "column" }}
        >
          <Paper
            elevation={4}
            sx={{
              py: 1,
              px: 2,
              background: "linear-gradient(135deg, #9c27b0, #2979ff)",
              color: "white",
              borderRadius: "16px 0 0 0",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
            }}
          >
            <Stack direction="row" spacing={2} alignItems="center">
              <Avatar sx={{ bgcolor: "#fff", color: "#5a5ae5" }}>🤖</Avatar>
              <Box>
                <Typography sx={{ fontWeight: "bold" }}>Dealio</Typography>
                <Box sx={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <Typography sx={{ fontSize: 12, opacity: 0.8 }}>
                    {isLoading
                      ? " Dealio is thinking..."
                      : "Always here to help"}
                  </Typography>
                </Box>
              </Box>
            </Stack>
            <IconButton
              onClick={() => setIsOpen(false)}
              sx={{ color: "white" }}
            >
              <CloseIcon />
            </IconButton>
          </Paper>

          <Box
            sx={{
              flex: 1,
              overflowY: "auto",
              p: 2,
              display: "flex",
              flexDirection: "column",
              gap: 1.5,
            }}
          >
            {messages.map((msg) => (
              <Box
                key={msg.id}
                sx={{
                  alignSelf: msg.sender === "user" ? "flex-end" : "flex-start",
                  maxWidth: "80%",
                }}
              >
                <Paper
                  sx={{
                    px: 1.5,
                    py: 1,
                    borderRadius: "16px",
                    background:
                      msg.sender === "user"
                        ? "linear-gradient(135deg, #9c27b0, #2979ff)"
                        : "white",
                    color: msg.sender === "user" ? "white" : "#333",
                    boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
                  }}
                >
                  <Typography
                    sx={{
                      wordBreak: "break-word",
                      whiteSpace: "pre-wrap",
                      fontSize: 14,
                    }}
                  >
                    {msg.sender === "bot" && msg.isTyping
                      ? msg.typedText
                      : msg.text}
                  </Typography>
                  <Typography
                    variant="caption"
                    sx={{ display: "block", opacity: 0.7 }}
                  >
                    {msg.timestamp}
                  </Typography>
                </Paper>
              </Box>
            ))}
            {isLoading && (
              <Box sx={{ alignSelf: "flex-start", maxWidth: "80%" }}>
                <Paper
                  sx={{
                    p: 1.5,
                    borderRadius: "16px",
                    backgroundColor: "#e3e6e9",
                    color: "#333",
                    boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
                    display: "flex",
                    alignItems: "center",
                    gap: "4px",
                  }}
                >
                  <Typography variant="body1">...</Typography>
                  <CircularProgress size={12} color="inherit" />
                </Paper>
              </Box>
            )}
            <Box ref={messagesEndRef} />
          </Box>

          {showSuggestedQuestions &&
            !isLoading &&
            suggestedQuestions.length > 0 && (
              <Box sx={{ p: 2, borderTop: "1px solid #e1e1e1" }}>
                <Stack
                  direction="row"
                  alignItems="center"
                  spacing={1}
                  sx={{ mb: 1 }}
                >
                  <Avatar
                    sx={{
                      bgcolor: "white",
                      color: "#7e57c2",
                      width: 24,
                      height: 24,
                      fontSize: "14px",
                      background: "linear-gradient(135deg, #007bff, #5a5ae5)",
                      boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
                    }}
                  >
                    <BoltIcon sx={{ color: "#fff" }} />
                  </Avatar>
                  <Typography variant="body2" fontWeight="bold">
                    Suggested questions:
                  </Typography>
                </Stack>
                <Stack direction="column" spacing={1}>
                  {suggestedQuestions.map((question, index) => (
                    <Button
                      key={index}
                      variant="contained"
                      onClick={() => handleSendMessage(question)}
                      sx={{
                        py: 1.5,
                        borderRadius: "24px",
                        background: "white",
                        color: "#2c3e50",
                        boxShadow: "0 2px 4px rgba(0,0,0,0.05)",
                        textTransform: "none",
                        textAlign: "left",
                        justifyContent: "flex-start",
                        "&:hover": {
                          background: "#f0f0f0",
                          transform: "translateY(-2px)",
                          boxShadow: "0 4px 8px rgba(0,0,0,0.1)",
                        },
                        transition: "transform 0.2s, box-shadow 0.2s",
                      }}
                    >
                      {question}
                    </Button>
                  ))}
                </Stack>
              </Box>
            )}

          <Paper
            elevation={4}
            sx={{
              p: 2,
              boxShadow: "0 -2px 8px rgba(0,0,0,0.1)",
            }}
          >
            <Stack direction="row" alignItems="center" spacing={1}>
              <TextField
                size="small"
                fullWidth
                multiline
                maxRows={8}
                variant="outlined"
                placeholder="Ask Dealio about your pitch deck..."
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage(inputValue);
                  }
                }}
                onFocus={() => setShowSuggestedQuestions(true)}
                onBlur={handleBlur}
                sx={{
                  "& .MuiOutlinedInput-root": {
                    borderRadius: "12px",
                    background: "#eeeeee",
                  },
                  "& .MuiOutlinedInput-notchedOutline": {
                    border: "none",
                  },
                }}
              />
              <IconButton
                color="primary"
                onClick={() => handleSendMessage(inputValue)}
                disabled={!inputValue.trim()}
                sx={{
                  width: 36,
                  height: 36,
                  borderRadius: "50%",
                  background: "linear-gradient(135deg, #9c27b0, #2979ff)",
                  boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
                  transition: "background 0.3s ease",
                }}
              >
                <SendIcon sx={{ color: "white", fontSize: 16 }} />
              </IconButton>
            </Stack>
          </Paper>
        </Box>
      </Drawer>
    </>
  );
};

export default ChatBot;
