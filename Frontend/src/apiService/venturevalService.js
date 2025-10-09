import { API_ENDPOINTS } from "../apiService/constants";
import API_SERVICE from "../apiService/apiService";

const { DOCUMENTS, ANALYSIS, AGENT, USER } = API_SERVICE;
const {
  DOCUMENTS: { PRESIGNED_URL },
  ANALYSIS: { START },
  AGENT: { CHAT },
  USER: { SIGNUP, LOGIN },
} = API_ENDPOINTS;

export const getPresignedUrl = (body = {}) => {
  return DOCUMENTS.post(PRESIGNED_URL, body).then((resp) => resp);
};

export const startAnalysis = (body = {}) => {
  return ANALYSIS.post(START, body).then((resp) => resp);
};
export const getAnalysisData = (analysis_id) => {
  return ANALYSIS.get(`${analysis_id}`).then((resp) => resp);
};

export const getChatbotResponse = (body = {}) => {
  return AGENT.post(CHAT, body).then((resp) => resp);
};

export const signUpUser = (body = {}) => {
  return USER.post(SIGNUP, body).then((resp) => resp);
};
export const loginUser = (body = {}) => {
  return USER.post(LOGIN, body).then((resp) => resp);
};
