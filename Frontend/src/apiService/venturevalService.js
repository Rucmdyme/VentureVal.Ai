import { API_ENDPOINTS } from "../apiService/constants";
import API_SERVICE from "../apiService/apiService";

const { DOCUMENTS, ANALYSIS } = API_SERVICE;
const {
  DOCUMENTS: { PRESIGNED_URL },
  ANALYSIS: { START },
} = API_ENDPOINTS;

export const getPresignedUrl = (body = {}) => {
  return DOCUMENTS.post(PRESIGNED_URL, body).then((resp) => resp.data);
};

export const startAnalysis = (body = {}) => {
  return ANALYSIS.post(START, body).then((resp) => resp.data);
};
export const getAnalysisData = (analysis_id) => {
  return ANALYSIS.get(`${analysis_id}`).then((resp) => resp.data);
};
