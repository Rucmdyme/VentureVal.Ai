export const SERVICES = [
  {
    service_key: "api/documents",
    service_name: "DOCUMENTS",
    baseURL: `${import.meta.env.VITE_API_URL}`,
  },
  {
    service_key: "api/analysis",
    service_name: "ANALYSIS",
    baseURL: `${import.meta.env.VITE_API_URL}`,
  },
];

export const API_ENDPOINTS = {
  DOCUMENTS: {
    PRESIGNED_URL: "/generate-upload-url",
  },
  ANALYSIS: {
    START: "/start",
    ANALYSIS_STATUS: "/",
  },
};
