import axios from "axios";
import API_BASE_URL from "../constants/api";

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: { "Content-Type": "application/json" },
});

// Injeta o token JWT em todas as requisições autenticadas
api.interceptors.request.use((config) => {
  // O token é lido do store de autenticação em tempo de execução
  const token = global.__authToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default api;
