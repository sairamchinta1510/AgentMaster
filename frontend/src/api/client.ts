import axios from "axios";
import type { Pipeline, PipelineSummary, Run } from "../types";

const API_BASE = import.meta.env.VITE_API_URL ?? (import.meta.env.PROD ? "" : "http://localhost:8000");
const WS_BASE = (import.meta.env.VITE_WS_URL as string | undefined) ??
  (import.meta.env.PROD
    ? `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}`
    : "ws://localhost:8000");

export const api = axios.create({ baseURL: API_BASE });

// ── WebSocket URL helper ─────────────────────────────────────────────────────

export const wsUrl = (path: string): string => `${WS_BASE}${path}`;

// ── Pipelines ────────────────────────────────────────────────────────────────

export const createPipeline = (objective: string, name?: string) =>
  api.post<Pipeline>("/api/pipelines", { objective, name: name || "" });

export const listPipelines = () =>
  api.get<PipelineSummary[]>("/api/pipelines");

export const getPipeline = (id: string) =>
  api.get<Pipeline>(`/api/pipelines/${id}`);

export const updatePipeline = (id: string, name: string) =>
  api.patch<Pipeline>(`/api/pipelines/${id}`, { name, objective: "" });

export const suggestExtensions = (id: string, extension_objective: string) =>
  api.post(`/api/pipelines/${id}/suggest-extensions`, { extension_objective });

export const deletePipeline = (id: string) =>
  api.delete(`/api/pipelines/${id}`);

// ── Runs ─────────────────────────────────────────────────────────────────────

export const createRun = (pipeline_id: string, inputs: Record<string, string>) =>
  api.post<Run>("/api/runs", { pipeline_id, inputs });

export const getRun = (run_id: string) =>
  api.get<Run>(`/api/runs/${run_id}`);

export const listRunsForPipeline = (pipeline_id: string) =>
  api.get<Run[]>(`/api/runs/by-pipeline/${pipeline_id}`);
