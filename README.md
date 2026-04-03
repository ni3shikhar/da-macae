# DA-MACAÉ v2 — Multi-Agent Custom Automation Engine

> **D**ata-migration **A**ssistant — **M**ulti-**A**gent **C**oordination and **A**utomated **É**xecution

An AI-driven multi-agent orchestration engine for **data migration** automation, built on the [Microsoft MACAE Solution Accelerator](https://github.com/microsoft/Multi-Agent-Custom-Automation-Engine-Solution-Accelerator) pattern.

---

## Overview

DA-MACAÉ v2 uses Azure AI Foundry's Agent Framework, Azure OpenAI, and specialized AI agents to plan, execute, and validate complex database migration tasks. Agents collaborate through a Magentic orchestration workflow with human-in-the-loop approval and real-time WebSocket streaming.

### Key Features

- **Multi-agent orchestration** — 8+ specialist agents (Discovery, Analysis, Mapping, Transformation, Pipeline, Data Quality, Infrastructure, Reporting)
- **Human-in-the-loop** — Plan approval gates and ProxyAgent for clarification
- **Real-time streaming** — WebSocket-based updates to the UI
- **MCP tools** — Model Context Protocol server for database introspection and pipeline management (SQL Server, PostgreSQL, MySQL, Oracle, MongoDB, Cosmos DB, Snowflake, BigQuery, Databricks, ADLS Gen2, CSV/Parquet/JSON, Azure Blob Storage) plus Azure Data Factory and Synapse Analytics pipeline tools
- **Security assessment** — MCSB v2 cloud security benchmark assessment team with 13 domain-specialist agents producing Excel reports
- **Responsible AI** — RAI validation before execution
- **Dynamic team configuration** — JSON-based team definitions with agent customization
- **Azure-native deployment** — Container Apps, Cosmos DB, AI Foundry, OpenAI

---

## Agent Teams

Two pre-built team configurations are included in `data/agent_teams/`:

### Data Migration Team (`migration_team.json`)

End-to-end migration across all supported data sources — 8 specialist agents:

| Agent | Responsibility |
|-------|----------------|
| `DiscoveryAgent` | Schema discovery, row counts, data profiling across all sources |
| `AnalysisAgent` | Data quality analysis and source/target compatibility assessment |
| `MappingAgent` | Schema mapping between source and target |
| `TransformationAgent` | DDL generation and data type conversion scripts |
| `PipelineAgent` | ADF / Synapse / Microsoft Fabric pipeline generation |
| `DataQualityAgent` | Post-migration validation and row-count reconciliation |
| `InfrastructureAgent` | Target infrastructure provisioning (databases, schemas) |
| `ReportingAgent` | Final migration summary, timelines, and recommendations |

### Cloud Security Assessment Team (`security_assessment_team.json`)

Microsoft Cloud Security Benchmark (MCSB) v2 Azure subscription assessment — 13 specialist agents:

| Agent | MCSB Domain |
|-------|-------------|
| `SecurityCoordinatorAgent` | Orchestration + Executive Summary |
| `NetworkSecurityAgent` | NS — Network Security |
| `IdentityManagementAgent` | IM — Identity Management |
| `DataProtectionAgent` | DP — Data Protection |
| `PrivilegedAccessAgent` | PA — Privileged Access |
| `AssetManagementAgent` | AM — Asset Management |
| `LoggingDetectionAgent` | LT — Logging & Threat Detection |
| `IncidentResponseAgent` | IR — Incident Response |
| `PostureVulnMgmtAgent` | PV — Posture & Vulnerability Management |
| `EndpointSecurityAgent` | ES — Endpoint Security |
| `BackupRecoveryAgent` | BR — Backup & Recovery |
| `DevOpsSecurityAgent` | DS — DevOps Security |
| `GovernanceStrategyAgent` | GS — Governance & Strategy |

Outputs a comprehensive Excel report with per-control findings, severity ratings (Critical/High/Medium/Low), recommendations, and MCSB control mappings.

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| Backend | Python 3.12 · FastAPI · Uvicorn |
| Frontend | React 18 · TypeScript · Vite · Fluent UI v9 |
| AI | Azure OpenAI (GPT-4o) · Azure AI Foundry · Anthropic Claude |
| Session Store | Azure Cosmos DB (NoSQL) / In-Memory |
| Data Sources | SQL Server · PostgreSQL · MySQL · Oracle · MongoDB · Cosmos DB · Snowflake · Databricks · BigQuery · ADLS Gen2 · Azure Blob |
| MCP Server | FastMCP (Python) — database tools + ADF/Synapse pipeline tools + MCSB security tools |
| Observability | Azure Monitor · OpenTelemetry |
| IaC | Bicep · Azure Developer CLI (`azd`) |
| Containers | Docker · Docker Compose · Azure Container Apps |

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (v4+)
- [Node.js](https://nodejs.org/) 22+ (for local frontend development)
- [Python](https://www.python.org/) 3.12+ (for local backend development)
- [Azure Developer CLI (`azd`)](https://learn.microsoft.com/azure/developer/azure-developer-cli/) (for Azure deployment)

---

## Quick Start (Docker)

```bash
# Clone the repository
git clone <repo-url>
cd da-macae

# Start all services (backend, frontend, MCP server, databases)
docker compose up -d --build

# Check service status
docker ps
```

Once running, open your browser:

| Service | URL |
|---------|-----|
| **Frontend** | http://localhost:3001 |
| **Backend API** | http://localhost:8000/api/v1/health |
| **MCP Server** | http://localhost:8001 |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│           React + Fluent UI 2 Frontend (:3001)          │
├─────────────────────────────────────────────────────────┤
│             Nginx (API/WS proxy → backend)              │
├─────────────────────────────────────────────────────────┤
│           FastAPI Backend (:8000)                        │
│   Orchestration Manager · Agent Factory · Team Service  │
├──────────────────────┬──────────────────────────────────┤
│  MCP Server (:8001)  │       Azure AI Services          │
│  DB tools · Storage  │  OpenAI · AI Foundry · AI Search │
├──────────────────────┴──────────────────────────────────┤
│                   Data Layer                             │
│  Cosmos DB · SQL Server · PostgreSQL · MySQL · MongoDB  │
│  Azurite (Azure Storage Emulator)                       │
└─────────────────────────────────────────────────────────┘
```

---

## Services (Docker Compose)

| Container | Image | Port | Purpose |
|-----------|-------|------|---------|
| `da-macae-backend` | Python 3.12 / FastAPI | 8000 | API + orchestration engine |
| `da-macae-frontend` | Nginx (React build) | 3001 | UI + API/WS reverse proxy |
| `da-macae-mcp` | Python 3.12 / FastMCP | 8001 | MCP tool server |
| `da-macae-sqlserver` | SQL Server 2022 | 1433 | Migration source database |
| `da-macae-postgres` | PostgreSQL 16 | 5432 | Migration target database |
| `da-macae-mysql` | MySQL 8.0 | 3306 | Migration source database |
| `da-macae-mongodb` | MongoDB 7.0 | 27017 | Migration source database |
| `da-macae-cosmosdb` | Cosmos DB Emulator | 8081 | Session/plan storage |
| `da-macae-azurite` | Azurite | 10000-10002 | Azure Storage emulator |

---

## Project Structure

```
da-macae/
├── src/
│   ├── backend/               # Python FastAPI backend
│   │   ├── app.py             # Entry point
│   │   ├── common/            # Config, database, models, utils
│   │   └── v1/               # API v1
│   │       ├── api/           # Route handlers
│   │       ├── orchestration/ # Orchestration manager, approval
│   │       ├── magentic_agents/  # Agent implementations
│   │       └── common/services/  # Team service
│   ├── frontend/              # React + TypeScript frontend
│   │   ├── src/
│   │   │   ├── pages/         # HomePage, PlanPage
│   │   │   ├── api/           # API client + service
│   │   │   ├── models/        # TypeScript models
│   │   │   └── services/      # WebSocket service
│   │   └── package.json
│   └── mcp_server/            # MCP tool server
│       ├── server.py                    # FastMCP entry point (data source tools)
│       ├── security_assessment_tools.py # MCSB v2 Azure security assessment tools
│       ├── security_excel_generator.py  # Excel report generation for security findings
│       ├── transformation_templates.py  # Data transformation and DDL helpers
│       └── linked_service_templates.py  # ADF / Synapse linked service templates
├── data/agent_teams/          # Team configuration JSON files
├── deployment/
│   ├── bicep/                 # Azure Bicep IaC modules
│   └── kubernetes/            # K8s manifests
├── docker-compose.yml         # Local development stack
├── Dockerfile                 # Multi-stage build (backend/frontend/mcp)
├── azure.yaml                 # Azure Developer CLI config
└── ARCHITECTURE-V2.md         # Detailed architecture documentation
```

---

## Local Development

### Run with Docker (recommended)

```bash
docker compose up -d --build     # Build and start all services
docker compose logs -f backend   # Follow backend logs
docker compose down -v           # Stop and remove volumes
```

### Run without Docker

```bash
# Backend
cd src/backend
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000

# Frontend
cd src/frontend
npm install
npm run dev                      # Vite dev server on :3001

# MCP Server
cd src/mcp_server
pip install -r requirements.txt
python server.py                 # MCP server on :8001
```

---

## Environment Variables

Key environment variables (configured in `docker-compose.yml` for local dev):

| Variable | Description |
|----------|-------------|
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key |
| `AZURE_OPENAI_CHAT_DEPLOYMENT` | Deployment name (e.g., `gpt-4o`) |
| `AZURE_OPENAI_API_VERSION` | API version (default: `2024-12-01-preview`) |
| `AZURE_AI_FOUNDRY_PROJECT_CONNECTION_STRING` | AI Foundry project connection |
| `ANTHROPIC_API_KEY` | Anthropic Claude API key (alternative LLM) |
| `ANTHROPIC_MODEL` | Claude model name (default: `claude-opus-4-20250514`) |
| `DATABASE_BACKEND` | `cosmosdb` or `in_memory` (default: `in_memory`) |
| `COSMOS_ENDPOINT` | Cosmos DB endpoint |
| `COSMOS_KEY` | Cosmos DB key |
| `MCP_SERVER_URL` | MCP server URL (default: `http://mcp-server:8001`) |
| `SQLSERVER_DSN` | SQL Server ODBC connection string |
| `POSTGRES_HOST` / `POSTGRES_PORT` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | PostgreSQL connection |
| `MYSQL_HOST` / `MYSQL_PORT` / `MYSQL_USER` / `MYSQL_PASSWORD` | MySQL connection |
| `ORACLE_DSN` / `ORACLE_USER` / `ORACLE_PASSWORD` | Oracle Database connection (optional) |
| `MONGODB_URI` | MongoDB connection URI |
| `SNOWFLAKE_ACCOUNT` / `SNOWFLAKE_USER` / `SNOWFLAKE_PASSWORD` | Snowflake connection (optional) |
| `ADLS_ACCOUNT_NAME` / `ADLS_ACCOUNT_KEY` | Azure Data Lake Storage Gen2 (optional) |
| `DATABRICKS_HOST` / `DATABRICKS_HTTP_PATH` / `DATABRICKS_TOKEN` | Databricks SQL (optional) |
| `BIGQUERY_PROJECT` / `GOOGLE_APPLICATION_CREDENTIALS` | Google BigQuery (optional) |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription for ADF/Synapse/security tools |
| `ADF_RESOURCE_GROUP` / `ADF_FACTORY_NAME` | Azure Data Factory (optional) |
| `SYNAPSE_WORKSPACE_ENDPOINT` | Azure Synapse Analytics workspace (optional) |
| `LOG_LEVEL` | Logging level (default: `INFO`) |

---

## Azure Deployment

### Quick Deploy (Recommended)

Use the deployment script for a guided deployment experience:

```powershell
# Deploy to dev environment
.\deploy.ps1 -Environment dev

# Deploy to production
.\deploy.ps1 -Environment prod -Location westus2

# Deploy containers only (skip infrastructure)
.\deploy.ps1 -Environment dev -SkipInfra
```

### Manual Deploy with AZD

```bash
# Authenticate
azd auth login

# Deploy all resources
azd up
```

### Environment Configuration

1. Copy `.env.template` to `.env.dev` (or `.env.staging`, `.env.prod`)
2. Fill in your secrets (API keys, connection strings)
3. The deployment script automatically loads these values

### Teardown Resources

```powershell
# Remove all resources (with confirmation)
.\teardown.ps1 -Environment dev

# Force remove + purge soft-deleted resources
.\teardown.ps1 -Environment dev -Force -Purge
```

### Azure Resources Provisioned

- Azure Container Apps — Backend, Frontend, MCP Server
- Azure Cosmos DB (NoSQL) — Plans, configs, messages
- Azure OpenAI — GPT-4o, embeddings
- Azure AI Search — RAG indexes
- Azure AI Foundry — Agent management
- Azure Container Registry — Container images
- Azure Key Vault — Secrets
- Azure Monitor — Telemetry + Application Insights

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/health` | Health check |
| POST | `/api/v1/process_request` | Submit a migration task |
| GET | `/api/v1/plans` | List all plans |
| GET | `/api/v1/plan/{plan_id}` | Get plan details |
| POST | `/api/v1/plan_approval` | Approve/reject a plan |
| POST | `/api/v1/user_clarification` | Respond to agent clarification |
| GET | `/api/v1/team_configs` | List team configurations |
| POST | `/api/v1/select_team` | Select active team |
| POST | `/api/v1/init_team` | Initialize team agents |
| WS | `/ws/{user_id}` | WebSocket connection |

---

## Orchestration Flow

1. **User submits** a migration request (e.g., *"Migrate AdventureWorks from SQL Server to PostgreSQL"*)
2. **RAI validation** checks the request for safety
3. **Planner (LLM)** creates an execution plan with agent assignments
4. **Human approval** — user reviews and approves the plan via WebSocket
5. **Magentic orchestrator** executes steps, delegating to specialized agents
6. **ProxyAgent** requests clarification from the user if needed
7. **Final synthesis** combines all agent outputs
8. **Results streamed** to the UI in real time

---

## License

Private — All rights reserved.
