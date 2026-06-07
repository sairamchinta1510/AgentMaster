import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export const api = axios.create({ baseURL: API_BASE });

export const createSession = (objective: string) =>
  api.post<{ session_id: string; phase: string; objective: string }>("/api/sessions", {
    objective,
  });

export const getSession = (sessionId: string) =>
  api.get(`/api/sessions/${sessionId}`);

export const listLibrary = () =>
  api.get<{ id: string; name: string; domain: string; quality_score: number; objective: string }[]>(
    "/api/library"
  );

export const searchLibrary = (q: string) =>
  api.get(`/api/library/search?q=${encodeURIComponent(q)}`);

export const provideInput = (sessionId: string, inputName: string, value: string) =>
  api.post(`/api/sessions/${sessionId}/input`, { input_name: inputName, value });
