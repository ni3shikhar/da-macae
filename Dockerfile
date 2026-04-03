# =============================================================================
# DA-MACAÉ v2 :: Multi-stage Dockerfile
# =============================================================================
# Targets: backend (Python/FastAPI), frontend (React/Nginx), mcp-server
#
# Build individual targets:
#   docker build --target backend -t da-macae-backend .
#   docker build --target frontend -t da-macae-frontend .
#   docker build --target mcp-server -t da-macae-mcp .
# =============================================================================

# ── Stage: Backend (Python / FastAPI) ────────────────────────────────────────
FROM python:3.12-slim AS backend

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY src/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY src/backend/ .
COPY data/ /app/data/

# Non-root user
RUN groupadd -r damacae && useradd -r -g damacae damacae && \
    chown -R damacae:damacae /app
USER damacae

EXPOSE 8000

LABEL maintainer="DA-MACAÉ Team" \
      version="2.0.0" \
      description="DA-MACAÉ Backend — FastAPI Multi-Agent Orchestration"

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]


# ── Stage: Frontend Build ────────────────────────────────────────────────────
FROM node:22-alpine AS frontend-build

WORKDIR /app
COPY src/frontend/package.json src/frontend/package-lock.json* ./
RUN npm install
COPY src/frontend/ .
RUN npm run build


# ── Stage: Frontend (Nginx serving static build) ─────────────────────────────
FROM nginx:1.27-alpine AS frontend

# Copy built assets
COPY --from=frontend-build /app/dist /usr/share/nginx/html

# Nginx config: SPA routing + API/WS proxy
RUN cat > /etc/nginx/conf.d/default.conf << 'EOF'
server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    # API proxy to backend
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # WebSocket proxy — rewrite /ws/ to /api/v1/ws/ to match backend router prefix
    location /ws/ {
        proxy_pass http://backend:8000/api/v1/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }

    # Cache-bust index.html so new deploys are picked up immediately
    location = /index.html {
        add_header Cache-Control "no-cache, no-store, must-revalidate";
        add_header Pragma "no-cache";
        add_header Expires "0";
    }

    # Hashed assets can be cached forever
    location /assets/ {
        add_header Cache-Control "public, max-age=31536000, immutable";
    }

    # SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }
}
EOF

EXPOSE 80

LABEL maintainer="DA-MACAÉ Team" \
      version="2.0.0" \
      description="DA-MACAÉ Frontend — React + Fluent UI"

CMD ["nginx", "-g", "daemon off;"]


# ── Stage: MCP Server ───────────────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS mcp-server

WORKDIR /app

# System deps for ODBC (SQL Server) and build tools for native wheels
# Use FreeTDS as ODBC driver instead of msodbcsql18 to avoid corporate proxy SSL issues
RUN apt-get update && apt-get install -y --no-install-recommends \
    unixodbc-dev tdsodbc freetds-dev freetds-bin \
    gcc g++ curl \
    && rm -rf /var/lib/apt/lists/* \
    && echo "[FreeTDS]\nDescription = FreeTDS ODBC Driver\nDriver = /usr/lib/x86_64-linux-gnu/odbc/libtdsodbc.so\nSetup = /usr/lib/x86_64-linux-gnu/odbc/libtdsS.so" > /etc/odbcinst.ini

COPY src/mcp_server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y gcc g++ && apt-get autoremove -y || true

COPY src/mcp_server/ .

# Non-root user
RUN groupadd -r damacae && useradd -r -g damacae damacae && \
    chown -R damacae:damacae /app
USER damacae

EXPOSE 8001

LABEL maintainer="DA-MACAÉ Team" \
      version="2.0.0" \
      description="DA-MACAÉ MCP Tool Server"

CMD ["python", "server.py"]
