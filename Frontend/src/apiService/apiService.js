import axios from "axios";
import { SERVICES } from "./constants";

const API_SERVICE = {};

SERVICES.forEach(({ service_name, baseURL, service_key }) => {
  const instance = axios.create({
    baseURL: `${baseURL}/${service_key}`,
    headers: { "Content-Type": "application/json" },
  });
  instance.interceptors.response.use(
    (response) => {
      // 2xx responses
      return response.data;
    },
    (error) => {
      // Non-2xx responses
      if (error.response && error.response.data) {
        // Return the error data but resolve it, not reject
        return Promise.resolve(error.response.data);
      }
      // Network or unexpected errors: rethrow
      return Promise.reject(error);
    }
  );

  API_SERVICE[service_name] = instance;
});

export default API_SERVICE;
