export const SERVICES = [
  {
    service_key: "api/documents",
    service_name: "DOCUMENTS",
    baseURL: "http://localhost:8000",
  },
  {
    service_key: "api/analysis",
    service_name: "ANALYSIS",
    baseURL: "http://localhost:8000",
  },
];

export const API_ENDPOINTS = {
  DOCUMENTS: {
    PRESIGNED_URL: "/generate-upload-url",
  },
  ANALYSIS: {
    START: "/start",
  },
};
