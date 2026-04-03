# DA-MACAÉ v2 — Multi-Agent Custom Automation Engine

> **D**ata-migration **A**ssistant — **M**ulti-**A**gent **C**oordination and **A**utomated **É**xecution
>
> Redesigned as a Multi-Agent Custom Automation Engine following the
> [Microsoft MACAE Solution Accelerator](https://github.com/microsoft/Multi-Agent-Custom-Automation-Engine-Solution-Accelerator) pattern.

---

## Solution Overview

DA-MACAÉ v2 is an AI-driven multi-agent orchestration engine focused on
**data migration** automation. It leverages Azure AI Foundry's Agent Framework,
Azure OpenAI, Azure Cosmos DB, and Azure Container Apps to create an intelligent
migration pipeline where specialized AI agents plan, execute, and validate
complex database migration tasks.

### Key Differentiators from v1

| Aspect | v1 (Java/Vaadin) | v2 (Python/React) |
|--------|-------------------|---------------------|
| Backend | Spring Boot 3.3 + Semantic Kernel Java | FastAPI + Azure AI Agent Framework |
| Frontend | Vaadin 24 (server-side) | React + Vite + Fluent UI 2 |
| Agent Framework | Custom BaseAgent + SK | agent_framework (FoundryAgentTemplate) |
| Orchestration | Custom MigrationWorkflowExecutor | Magentic orchestration (plan→approve→execute) |
| Team Config | Hardcoded 8 agents | Dynamic JSON team configuration |
| Communication | REST polling | WebSocket streaming |
| Human-in-loop | Approval gates only | ProxyAgent for clarification + approval |
| Safety | None | RAI validation (Responsible AI) |
| Tool Access | SK Plugins | MCP (Model Context Protocol) |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    React + Fluent UI 2 Frontend                  │
│         (Vite · TypeScript · WebSocket · Plan/Chat UI)           │
├─────────────────────────────────────────────────────────────────┤
│                   Frontend Server (Python/FastAPI)                │
│              Static file serving · Config endpoint                │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌───────────────────── Backend API (FastAPI) ──────────────────┐│
│  │ /api/v1/process_request  · /api/v1/plans · /api/v1/plan      ││
│  │ /api/v1/plan_approval    · /api/v1/agent_message             ││
│  │ /api/v1/team_configs     · /api/v1/select_team               ││
│  │ /api/v1/init_team        · /api/v1/user_clarification        ││
│  │ WebSocket: /ws/{user_id}                                      ││
│  └──────────┬──────────────────────────────────┬────────────────┘│
│             │                                  │                  │
│  ┌──────────▼──────────┐   ┌──────────────────▼────────────────┐│
│  │ Orchestration Manager│   │        Team Service               ││
│  │ • MagenticBuilder    │   │ • Load/Save team configs          ││
│  │ • HumanApproval Mgr  │   │ • Agent CRUD                     ││
│  │ • Plan→MPlan convert │   │ • Starting tasks                 ││
│  └──────────┬──────────┘   └──────────────────┬────────────────┘│
│             │                                  │                  │
│  ┌──────────▼──────────────────────────────────▼────────────────┐│
│  │              Agent Factory (MagenticAgentFactory)             ││
│  │  Creates agents from team JSON config at runtime:             ││
│  │  • FoundryAgentTemplate (AI agents with RAG/MCP/Code Interp) ││
│  │  • ProxyAgent (human clarification)                           ││
│  │  • ReasoningAgent (o1/o3 models)                              ││
│  └──────────┬──────────────────────────────────┬────────────────┘│
│             │                                  │                  │
│  ┌──────────▼──────────┐   ┌──────────────────▼────────────────┐│
│  │   Agent Registry     │   │      RAI Validation Service       ││
│  │ Lifecycle management │   │ Safety checks before execution    ││
│  │ for all agent        │   │ Content filtering                 ││
│  │ instances             │   │                                   ││
│  └──────────────────────┘   └───────────────────────────────────┘│
│                                                                   │
├─────────────────────────────────────────────────────────────────┤
│                     MCP Server (FastMCP)                          │
│  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐ │
│  │ Database Tools    │ │ Cloud Storage     │ │ Pipeline Tools   │ │
│  ├──────────────────┤ ├──────────────────┤ ├──────────────────┤ │
│  │ SQL Server        │ │ Azure Blob        │ │ ADF Linked Svc   │ │
│  │ PostgreSQL        │ │ ADLS Gen2         │ │ Synapse          │ │
│  │ MySQL/MariaDB     │ │ CSV/Parquet/JSON  │ │ Fabric           │ │
│  │ Oracle            │ │                    │ │                  │ │
│  │ MongoDB           │ │ Security Tools     │ │ Transformation   │ │
│  │ Cosmos DB         │ ├──────────────────┤ │ Templates        │ │
│  │ Snowflake         │ │ Security Scan      │ │                  │ │
│  │ Databricks SQL    │ │ Report Generator   │ │                  │ │
│  │ BigQuery          │ │                    │ │                  │ │
│  └──────────────────┘ └──────────────────┘ └──────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│                     Data Layer                                    │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐ │
│  │ Azure Cosmos  │ │ Azure OpenAI │ │ Azure AI Search           │ │
│  │ DB (NoSQL)    │ │ (GPT-4o)     │ │ (RAG indexes)             │ │
│  ├──────────────┤ ├──────────────┤ ├──────────────────────────┤ │
│  │ Plans         │ │ Chat Complet.│ │ Migration knowledge base  │ │
│  │ Team configs  │ │ Embeddings   │ │ Schema documentation      │ │
│  │ Agent messages│ │ Assistants   │ │ Best practices             │ │
│  │ Sessions      │ │              │ │                            │ │
│  └──────────────┘ └──────────────┘ └──────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
da-macae/
├── src/
│   ├── backend/                          # Python FastAPI backend
│   │   ├── app.py                        # FastAPI entry point
│   │   ├── requirements.txt              # Python dependencies
│   │   ├── common/                       # Shared utilities
│   │   │   ├── config/
│   │   │   │   └── app_config.py         # Environment-based configuration
│   │   │   ├── database/
│   │   │   │   ├── database_base.py      # Abstract database interface
│   │   │   │   ├── database_factory.py   # Database provider factory
│   │   │   │   ├── cosmosdb.py           # Cosmos DB implementation
│   │   │   │   └── in_memory.py          # In-memory DB for local dev
│   │   │   ├── models/
│   │   │   │   └── messages.py           # Pydantic data models
│   │   │   └── utils/
│   │   │       └── utils.py              # RAI validation, team helpers
│   │   └── v1/                           # API version 1
│   │       ├── api/
│   │       │   └── router.py             # FastAPI route handlers
│   │       ├── config/
│   │       │   └── agent_registry.py     # Global agent registry
│   │       ├── common/
│   │       │   └── services/
│   │       │       └── team_service.py   # Team configuration CRUD
│   │       ├── magentic_agents/          # Agent implementations
│   │       │   ├── foundry_agent.py      # FoundryAgentTemplate
│   │       │   ├── proxy_agent.py        # Human clarification proxy
│   │       │   ├── magentic_agent_factory.py  # Dynamic agent creation
│   │       │   ├── common/
│   │       │   │   ├── lifecycle.py           # AzureAgentBase lifecycle
│   │       │   │   ├── claude_mcp_runner.py   # Claude MCP tool runner
│   │       │   │   ├── openai_mcp_runner.py   # OpenAI MCP tool runner
│   │       │   │   └── doc_generator.py       # Documentation generator
│   │       │   └── models/
│   │       │       └── agent_models.py   # MCPConfig, SearchConfig
│   │       └── orchestration/
│   │           ├── orchestration_manager.py   # Magentic workflow manager
│   │           ├── human_approval_manager.py  # Plan approval workflow
│   │           └── helper/
│   │               └── plan_to_mplan_converter.py  # Plan text parser
│   │
│   ├── frontend/                         # React + TypeScript frontend
│   │   ├── index.html
│   │   ├── package.json
│   │   ├── vite.config.ts
│   │   ├── tsconfig.json
│   │   └── src/
│   │       ├── App.tsx
│   │       ├── main.tsx
│   │       ├── api/
│   │       │   ├── apiClient.tsx         # HTTP client
│   │       │   └── apiService.tsx        # API service layer
│   │       ├── models/
│   │       │   ├── index.tsx             # Model exports
│   │       │   ├── enums.tsx             # Agent types, plan status
│   │       │   ├── Team.tsx              # Agent, Team, TeamConfig
│   │       │   └── plan.tsx              # Plan, MPlan, Step models
│   │       ├── services/
│   │       │   └── WebSocketService.tsx  # WebSocket manager
│   │       ├── pages/
│   │       │   ├── HomePage.tsx          # Team selection + task input
│   │       │   ├── PlanPage.tsx          # Plan view + chat + execution
│   │       │   └── HistoryPage.tsx       # Plan history view
│   │       └── components/
│   │           └── FormattedContent.tsx  # Markdown/content rendering
│   │
│   └── mcp_server/                       # Model Context Protocol server
│       ├── server.py                     # FastMCP entry point
│       ├── requirements.txt
│       ├── linked_service_templates.py   # ADF linked service templates
│       ├── security_assessment_tools.py  # Security scanning tools
│       ├── security_excel_generator.py   # Security report generator
│       └── transformation_templates.py   # Data transformation templates
│
├── data/
│   ├── agent_teams/                      # Pre-built team JSON configs
│   │   ├── migration_team.json           # Data migration team
│   │   └── security_assessment_team.json # Security assessment team
│   └── seed/                             # Seed data for local dev
│
├── deployment/                           # Azure infrastructure
│   ├── bicep/
│   │   ├── main.bicep                    # Main deployment
│   │   ├── main.json                     # ARM template output
│   │   ├── modules/
│   │   │   ├── acr.bicep                 # Container Registry
│   │   │   ├── adf.bicep                 # Azure Data Factory
│   │   │   ├── aks.bicep                 # Container Apps
│   │   │   ├── appconfig.bicep           # App Configuration
│   │   │   ├── cosmosdb.bicep            # Cosmos DB
│   │   │   ├── keyvault.bicep            # Key Vault
│   │   │   ├── monitoring.bicep          # Application Insights
│   │   │   ├── openai.bicep              # Azure OpenAI
│   │   │   ├── servicebus.bicep          # Service Bus
│   │   │   └── storage.bicep             # Storage Account
│   │   └── parameters/
│   │       ├── dev.bicepparam            # Development parameters
│   │       ├── staging.bicepparam        # Staging parameters
│   │       └── prod.bicepparam           # Production parameters
│   ├── container-apps/
│   │   └── main.bicep                    # Container Apps deployment
│   └── kubernetes/                       # K8s deployment (future)
│
├── docs/
│   └── examples/                         # Usage examples
│
├── docker-compose.yml                    # Local development
├── Dockerfile                            # Root container definition
├── azure.yaml                            # Azure Developer CLI config
└── README.md
```

---

## Technology Stack

| Component | Technology | Version |
|-----------|------------|---------|
| **Backend Runtime** | Python | 3.12+ |
| **Backend Framework** | FastAPI + Uvicorn | 0.115+ / 0.34+ |
| **AI Agent Framework** | agent_framework (Microsoft) | latest |
| **AI Client** | agent_framework_azure_ai | latest |
| **AI Service** | Azure OpenAI (GPT-4o / o3-mini) | 2024-12-01 |
| **AI Foundry** | Azure AI Foundry | latest |
| **Database** | Azure Cosmos DB (NoSQL) | latest |
| **Search** | Azure AI Search | latest |
| **Frontend** | React 18 + TypeScript | 18.3+ |
| **Frontend Build** | Vite | 6+ |
| **UI Library** | Fluent UI React v9 | 9.55+ |
| **WebSocket** | FastAPI WebSocket | built-in |
| **MCP Server** | FastMCP (Python) | latest |
| **Observability** | Azure Monitor + OpenTelemetry | latest |
| **Auth** | Azure AD / Entra ID | latest |
| **IaC** | Bicep | latest |
| **Containers** | Azure Container Apps | latest |
| **Package Manager** | uv (Python) / npm (Node) | latest |
| **Local Dev** | Docker Compose | latest |

---

## Agent Architecture

### Agent Types

1. **FoundryAgentTemplate** — Full AI agent backed by Azure AI Foundry
   - Supports RAG (Azure AI Search index)
   - Supports MCP tools
   - Supports Code Interpreter
   - Supports Bing search
   - Supports reasoning models (o1/o3)

2. **ProxyAgent** — Human-in-the-loop clarification agent
   - Sends questions to user via WebSocket
   - Waits for response with configurable timeout
   - Bridges agent workflow ↔ human interaction

3. **RAI Agent** — Responsible AI safety validator
   - Evaluates user input and team configs for safety
   - Returns TRUE (block) or FALSE (safe) classification

### Pre-configured Migration Team

The migration team includes 8 specialist agents, each with domain-specific
system prompts and capabilities:

| Agent | Role | Capabilities |
|-------|------|-------------|
| **DiscoveryAgent** | Schema and metadata discovery | MCP (SQL/PG tools), RAG |
| **AnalysisAgent** | Complexity and risk analysis | RAG (migration knowledge) |
| **MappingAgent** | Source→target schema mapping | MCP, Code Interpreter |
| **TransformationAgent** | Data transformation rules | MCP, Code Interpreter |
| **PipelineAgent** | ADF/Synapse pipeline generation | Code Interpreter |
| **DataQualityAgent** | Validation rule generation | MCP (SQL/PG tools) |
| **InfrastructureAgent** | Azure resource provisioning | MCP (Azure tools) |
| **ReportingAgent** | Migration report generation | RAG, Code Interpreter |
| **ProxyAgent** | Human clarification | WebSocket |

---

## Orchestration Flow

```
User Input ("Migrate AdventureWorks from SQL Server to PostgreSQL")
    │
    ▼
┌─────────────────┐
│ RAI Validation   │──── Blocked? → Return safety error
└────────┬────────┘
         │ Safe
         ▼
┌─────────────────┐
│ Planner (LLM)   │──── Creates execution plan with agent assignments
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Human Approval   │──── User reviews plan via WebSocket
│ Gate             │──── Approve / Reject / Modify
└────────┬────────┘
         │ Approved
         ▼
┌─────────────────┐     ┌─────────────────┐
│ Magentic         │────▶│ Agent Execution  │
│ Orchestrator     │     │ (step by step)   │
│                  │◀────│                   │
└────────┬────────┘     └─────────────────┘
         │                      │
         │              ┌───────▼────────┐
         │              │ ProxyAgent     │ ← Human clarification if needed
         │              └───────┬────────┘
         │                      │
         ▼
┌─────────────────┐
│ Final Synthesis  │──── Combines all agent outputs
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ WebSocket Stream │──── Real-time results to UI
└─────────────────┘
```

---

## Data Model (Cosmos DB)

All documents stored in a single Cosmos DB container, partitioned by `user_id`:

| Document Type | Key Fields |
|--------------|------------|
| `session` | `id`, `user_id`, `created_at` |
| `plan` | `id`, `plan_id`, `user_id`, `initial_goal`, `overall_status`, `m_plan` |
| `m_plan` | `id`, `plan_id`, `task`, `steps[]`, `status` |
| `agent_message` | `id`, `plan_id`, `agent`, `content`, `agent_type` |
| `team_config` | `id`, `user_id`, `name`, `description`, `agents[]`, `starting_tasks[]` |
| `user_current_team` | `id`, `user_id`, `team_id` |

---

## WebSocket Protocol

Messages between frontend and backend use typed JSON:

```typescript
// Server → Client
{ type: "plan_update", data: MPlan }
{ type: "agent_response", data: { agent: string, content: string } }
{ type: "streaming_content", data: { content: string } }
{ type: "human_clarification_request", data: { question: string } }
{ type: "plan_complete", data: { summary: string } }
{ type: "error", data: { message: string } }

// Client → Server
{ type: "user_clarification_response", data: { response: string } }
{ type: "plan_approval", data: { approved: boolean } }
```

---

## Deployment

### Local Development
```bash
docker compose up -d              # Start all services
cd src/backend && uv run uvicorn app:app --port 8000
cd src/frontend && npm run dev    # Vite dev server on :3001
cd src/mcp_server && uv run python server.py      # MCP on :8100
```

### Azure Deployment
```bash
azd auth login
azd up                            # Deploy all resources via Bicep
```

### Azure Resources
- **Azure Container Apps** — Backend, Frontend, MCP Server
- **Azure Cosmos DB** (NoSQL) — Plans, configs, messages
- **Azure OpenAI** — GPT-4o, embeddings
- **Azure AI Search** — RAG indexes
- **Azure AI Foundry** — Agent management
- **Azure Container Registry** — Container images
- **Azure Data Factory** — Data pipeline orchestration
- **Azure Service Bus** — Async messaging
- **Azure App Configuration** — Feature flags, settings
- **Azure Key Vault** — Secrets
- **Azure Monitor** — Telemetry + Application Insights
