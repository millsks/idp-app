/**
 * Axios HTTP client pre-configured to communicate with the FastAPI backend.
 *
 * Base URL: /api/v1 (proxied by Vite dev server → http://localhost:8000)
 */

import axios from "axios";

export const apiClient = axios.create({
  baseURL: "/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
});

// Attach the JWT access token from localStorage (if present) to every request
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Global error handling — redirect to /login on 401
apiClient.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    if (axios.isAxiosError(error)) {
      if (error.response?.status === 401) {
        localStorage.removeItem("access_token");
        globalThis.location.href = "/login";
      }
      throw error; // AxiosError extends Error ✓
    }
    // Wrap non-Error rejections so callers always receive an Error
    throw error instanceof Error ? error : new Error(String(error));
  },
);
