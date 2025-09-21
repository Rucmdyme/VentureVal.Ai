import axios from "axios";
import { SERVICES } from "./constants";

const API_SERVICE = {};

SERVICES.forEach(({ service_name, baseURL, service_key }) => {
  API_SERVICE[service_name] = axios.create({
    baseURL: `${baseURL}/${service_key}`,
    headers: { "Content-Type": "application/json" },
  });
});

export default API_SERVICE;
