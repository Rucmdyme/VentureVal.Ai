export const SERVICES = [
  {
    service_key: "documents",
    service_name: "DOCUMENTS",
    baseURL: `${import.meta.env.VITE_API_URL}`,
  },
  {
    service_key: "analysis",
    service_name: "ANALYSIS",
    baseURL: `${import.meta.env.VITE_API_URL}`,
  },
  {
    service_key: "agent",
    service_name: "AGENT",
    baseURL: `${import.meta.env.VITE_API_URL}`,
  },
];

export const API_ENDPOINTS = {
  DOCUMENTS: {
    PRESIGNED_URL: "/generate-upload-url",
  },
  ANALYSIS: {
    START: "/start",
  },
  AGENT: {
    CHAT: "/agent/chat",
  },
};
