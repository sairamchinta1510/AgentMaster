# ── Stage 1: Build frontend ───────────────────────────────────────────────────
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --prefer-offline
COPY frontend/ ./
# Empty API URL = use relative paths (same origin as backend)
ENV VITE_API_URL=""
RUN npm run build

# ── Stage 2: Python backend ───────────────────────────────────────────────────
FROM python:3.12-slim
WORKDIR /app

# Install Python deps
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ ./

# Copy built frontend into static/ (served by FastAPI)
COPY --from=frontend-build /app/frontend/dist ./static

# SQLite lives in /tmp (writable on Cloud Run)
RUN mkdir -p /tmp/data

ENV DATABASE_URL=sqlite:////tmp/data/agentmaster.db
ENV PORT=8080

EXPOSE 8080

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
