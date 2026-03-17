"""Base lifecycle management for Azure AI Foundry agents."""

from __future__ import annotations

import asyncio
import random
from typing import Any, Optional

import structlog

from v1.magentic_agents.common.claude_mcp_runner import run_agent_with_claude
from v1.magentic_agents.common.openai_mcp_runner import run_agent_with_openai

logger = structlog.get_logger(__name__)


# ── Local-mode simulated outputs per agent type ─────────────────────

_SIMULATED_OUTPUTS: dict[str, str] = {
    "DiscoveryAgent": """## Source Database Schema Discovery

**Database**: SQL Server 2019 (source-db.contoso.com)
**Total Tables**: 47 | **Views**: 12 | **Stored Procedures**: 23

### Key Tables Discovered
| Table | Rows | Size (MB) | Primary Key | Foreign Keys |
|-------|------|-----------|-------------|--------------|
| dbo.Customers | 1,245,890 | 342 | CustomerID (int) | — |
| dbo.Orders | 8,934,221 | 1,240 | OrderID (bigint) | CustomerID → Customers |
| dbo.OrderItems | 28,102,445 | 2,100 | ItemID (bigint) | OrderID → Orders, ProductID → Products |
| dbo.Products | 15,420 | 18 | ProductID (int) | CategoryID → Categories |
| dbo.Inventory | 892,310 | 156 | InventoryID (int) | ProductID → Products |
| dbo.Payments | 6,234,100 | 890 | PaymentID (bigint) | OrderID → Orders |

### Data Types Summary
- varchar/nvarchar: 124 columns
- int/bigint: 89 columns
- datetime/datetime2: 34 columns
- decimal/money: 22 columns
- binary/varbinary: 8 columns (LOB data)

### Relationships: 38 foreign key constraints identified
### Indexes: 92 indexes (47 clustered, 45 non-clustered)

✅ Schema discovery completed successfully.""",

    "InfrastructureAgent": """## Target Environment Verification & Provisioning

### Azure Resources Status
| Resource | Status | Details |
|----------|--------|---------|
| Resource Group (rg-migration-prod) | ✅ Exists | East US 2 |
| Azure SQL Database (sql-target-prod) | ✅ Provisioned | Gen5, 8 vCores, 32GB |
| Azure Data Factory (adf-migration-prod) | ✅ Provisioned | V2, Managed VNET enabled |
| Azure Key Vault (kv-migration-prod) | ✅ Provisioned | Secrets configured |
| Storage Account (stmigrationprod) | ✅ Provisioned | LRS, Hot tier |
| Azure Monitor (log-migration-prod) | ✅ Provisioned | 30-day retention |

### Network Configuration
- Private Endpoints: Configured for SQL Database and Storage
- NSG Rules: Inbound from ADF Managed VNET only
- DNS: Private DNS zones linked to migration VNET

### Credentials & Secrets
- SQL admin credentials stored in Key Vault ✅
- Storage account keys stored in Key Vault ✅
- ADF Managed Identity granted access to all resources ✅

✅ Target environment is ready for migration.""",

    "AnalysisAgent": """## Migration Complexity Analysis

### Overall Risk Assessment: **MEDIUM**

### Complexity Breakdown
| Factor | Score | Notes |
|--------|-------|-------|
| Schema Complexity | 7/10 | 47 tables, 38 FK relationships, circular refs in 2 table groups |
| Data Volume | 6/10 | ~45M rows, ~4.7 GB total, largest table 2.1 GB |
| Data Type Compatibility | 4/10 | Most types map directly; 8 varbinary columns need attention |
| Stored Procedure Migration | 8/10 | 23 stored procs, 5 use SQL Server-specific syntax (CROSS APPLY, CTE) |
| Index Strategy | 5/10 | 92 indexes; recommend consolidation to 67 for target |
| Downtime Tolerance | 3/10 | Business allows 4-hour maintenance window |

### Key Risks Identified
1. ⚠️ **Circular FK references** between `Orders ↔ Payments` — need deferred constraints
2. ⚠️ **LOB columns** in `dbo.Documents` (avg 2.4 MB per row) — may slow bulk copy
3. ⚠️ **CROSS APPLY** in 5 stored procedures — needs rewrite for Azure SQL compatibility
4. ℹ️ **Computed columns** in 3 tables — verify expression compatibility
5. ℹ️ **Temporal tables** — `dbo.AuditLog` uses system-versioning

### Estimated Migration Duration
- Schema migration: ~15 minutes
- Data migration (parallel): ~2.5 hours
- Validation: ~45 minutes
- **Total estimated**: ~3.5 hours (within 4-hour window)

✅ Analysis complete — migration is feasible within constraints.""",

    "MappingAgent": """## Source-to-Target Schema Mapping

### Mapping Summary
- **Tables mapped**: 47/47 (100%)
- **Columns mapped**: 277/282 (5 columns marked for transformation)
- **Direct mappings**: 264 columns (no change needed)
- **Type conversions**: 13 columns

### Key Type Conversions
| Source Column | Source Type | Target Type | Reason |
|--------------|-------------|-------------|--------|
| Customers.Phone | varchar(20) | nvarchar(20) | Unicode support |
| Orders.OrderDate | datetime | datetime2(3) | Higher precision |
| Payments.Amount | money | decimal(19,4) | Standard decimal |
| Products.Weight | float | decimal(10,3) | Precision control |
| Documents.Content | varbinary(max) | varbinary(max) | Direct (with chunking) |

### Schema Differences Applied
- Target uses `datetime2` instead of `datetime` (13 columns)
- Target uses `nvarchar` instead of `varchar` for text columns (8 columns)
- Collation: Source `SQL_Latin1_General_CP1_CI_AS` → Target `Latin1_General_100_CI_AS_SC_UTF8`

### Generated DDL Scripts
- `01_create_schemas.sql` — Schema creation statements
- `02_create_tables.sql` — All 47 tables with mapped types
- `03_create_constraints.sql` — PKs, FKs, unique constraints
- `04_create_indexes.sql` — 67 optimized indexes

✅ Schema mapping completed — DDL scripts generated.""",

    "TransformationAgent": """## Data Transformation Rules

### Transformation Pipeline
| Rule # | Source Table | Transformation | Details |
|--------|-------------|---------------|---------|
| T-001 | Customers | Collation conversion | CP1 → UTF8 for all text columns |
| T-002 | Customers | Phone normalization | Strip non-numeric, add country code |
| T-003 | Orders | Date precision upgrade | datetime → datetime2(3) |
| T-004 | Payments | Currency conversion | money → decimal(19,4) |
| T-005 | Products | Weight standardization | float → decimal(10,3), round to 3 places |
| T-006 | Documents | LOB chunking | Split > 4MB blobs into 4MB chunks |
| T-007 | AuditLog | Temporal table rebuild | Recreate system-versioning on target |
| T-008 | All tables | Identity reseed | Reset identity columns after migration |
| T-009 | OrderItems | Computed column | Recalculate LineTotal = Qty × UnitPrice |

### Stored Procedure Conversions
| Procedure | Change | Status |
|-----------|--------|--------|
| sp_GetCustomerOrders | CROSS APPLY → LEFT JOIN subquery | ✅ Converted |
| sp_CalculateRevenue | CTE syntax compatible | ✅ No change needed |
| sp_UpdateInventory | MERGE statement compatible | ✅ No change needed |
| sp_GenerateReport | STRING_AGG instead of FOR XML | ✅ Converted |
| sp_CleanupExpired | DELETE TOP → batch delete pattern | ✅ Converted |

### Generated Scripts
- `transform_data.sql` — Transformation logic
- `converted_procedures.sql` — 5 rewritten stored procedures

✅ All transformation rules defined and validated.""",

    "DataQualityAgent": """## Data Quality Validation Report

### Pre-Migration Validation (Source)
| Check | Tables | Result | Issues |
|-------|--------|--------|--------|
| Null constraints | 47 | ✅ Pass | 0 violations |
| FK integrity | 38 relationships | ⚠️ 3 orphans | Orders → Customers (3 rows) |
| Unique constraints | 52 | ✅ Pass | 0 violations |
| Data type ranges | 277 columns | ✅ Pass | 0 out-of-range values |
| String length | 124 text cols | ⚠️ 12 truncation risks | Max length approaches limit |
| Date validity | 34 date cols | ✅ Pass | 0 invalid dates |

### Data Profiling Summary
- **Total rows analyzed**: 45,424,386
- **Null percentage**: 2.1% overall (within acceptable range)
- **Duplicate detection**: 0 exact duplicates found
- **Encoding issues**: 4 rows with non-UTF8 characters in `Products.Description`

### Remediation Actions
1. 🔧 Fix 3 orphan records in Orders (CustomerID references deleted customers)
2. 🔧 Truncate 12 near-limit strings to ensure safe migration
3. 🔧 Convert 4 encoding issues in Products.Description to UTF-8

### Post-Migration Validation Plan
- Row count comparison per table
- Checksum validation on all tables
- Spot-check 1000 random rows per table
- FK integrity re-validation

✅ Source data quality is GOOD — 3 minor issues identified and remediated.""",

    "PipelineGenerationAgent": """## Migration Pipeline Definitions

### Azure Data Factory Pipeline Generated
**Pipeline**: `pl_full_migration_sqlserver_to_azuresql`

### Linked Services Created
| Service | Type | Target |
|---------|------|--------|
| ls_source_sqlserver | SQL Server | source-db.contoso.com |
| ls_target_azuresql | Azure SQL Database | sql-target-prod.database.windows.net |
| ls_staging_blob | Azure Blob Storage | stmigrationprod.blob.core.windows.net |

### Pipeline Activities (14 total)
| # | Activity | Type | Parallelism |
|---|----------|------|-------------|
| 1 | Pre-flight checks | Validation | — |
| 2 | Create target schema | Script | — |
| 3 | Copy Customers | Copy Data | Batch 1 |
| 4 | Copy Products | Copy Data | Batch 1 |
| 5 | Copy Categories | Copy Data | Batch 1 |
| 6 | Copy Orders | Copy Data | Batch 2 |
| 7 | Copy OrderItems | Copy Data | Batch 2 (chunked) |
| 8 | Copy Payments | Copy Data | Batch 2 |
| 9 | Copy Inventory | Copy Data | Batch 3 |
| 10 | Copy Documents | Copy Data | Batch 3 (LOB) |
| 11 | Copy remaining 39 tables | ForEach + Copy | Batch 4 |
| 12 | Apply constraints & indexes | Script | — |
| 13 | Run stored procedures | Script | — |
| 14 | Post-migration validation | Validation | — |

### Performance Settings
- DIU (Data Integration Units): 32 for large tables, 8 for small
- Parallel copies: 4 per activity
- Staging enabled for LOB data via Blob Storage

✅ Pipeline definitions generated — ready for deployment to ADF.""",

    "ReportingAgent": """## Migration Summary Report

### Executive Summary
Migration plan for **SQL Server 2019 → Azure SQL Database** has been fully prepared.

### Migration Scope
| Metric | Value |
|--------|-------|
| Source Database | SQL Server 2019 on-premise |
| Target Database | Azure SQL Database (Gen5, 8 vCores) |
| Tables | 47 |
| Total Rows | 45,424,386 |
| Total Data Size | 4.7 GB |
| Stored Procedures | 23 (5 require conversion) |
| Views | 12 |
| Indexes | 92 → 67 (optimized) |

### Risk Summary
| Risk | Level | Mitigation |
|------|-------|-----------|
| Circular FK references | Medium | Deferred constraints during load |
| LOB data migration | Low | Chunked copy with staging |
| Stored procedure syntax | Medium | 5 procedures rewritten and tested |
| Data quality issues | Low | 3 orphan records fixed pre-migration |

### Estimated Timeline
| Phase | Duration |
|-------|----------|
| Schema deployment | 15 min |
| Data migration | 2.5 hours |
| Post-migration validation | 45 min |
| Stored procedure deployment | 15 min |
| Smoke testing | 30 min |
| **Total** | **~4 hours** |

### Generated Artifacts
1. 📄 Schema DDL scripts (4 files)
2. 📄 Transformation scripts (2 files)
3. 📄 ADF Pipeline definition (1 pipeline, 14 activities)
4. 📄 Validation queries (pre and post)
5. 📄 Rollback procedures

### Recommendation
✅ **READY TO EXECUTE** — All pre-migration checks passed. Recommend scheduling during the approved 4-hour maintenance window.

---
*Report generated by DA-Macae Migration Assistant*""",
}

# Delay ranges per agent (seconds) to simulate realistic work duration
_SIMULATED_DELAYS: dict[str, tuple[float, float]] = {
    "DiscoveryAgent": (3.0, 6.0),
    "InfrastructureAgent": (4.0, 8.0),
    "AnalysisAgent": (3.0, 5.0),
    "MappingAgent": (2.5, 5.0),
    "TransformationAgent": (3.0, 5.0),
    "DataQualityAgent": (3.0, 6.0),
    "PipelineGenerationAgent": (4.0, 7.0),
    "ReportingAgent": (2.0, 4.0),
}


class AzureAgentBase:
    """Manages the lifecycle of an Azure AI Foundry agent instance.

    Handles agent creation, thread management, and cleanup.
    When Azure AI Foundry is not available but an OpenAI client is
    provided, the agent uses Azure OpenAI + MCP tool calling instead
    of returning simulated outputs.
    """

    def __init__(
        self,
        name: str,
        model: str,
        instructions: str,
        *,
        project_client: Any | None = None,
        openai_client: Any | None = None,
        anthropic_client: Any | None = None,
        anthropic_model: str = "",
        mcp_server_url: str = "",
        mcp_tool_names: list[str] | None = None,
    ) -> None:
        self.name = name
        self.model = model
        self.instructions = instructions
        self._project_client = project_client
        self._openai_client = openai_client
        self._anthropic_client = anthropic_client
        self._anthropic_model = anthropic_model
        self._mcp_server_url = mcp_server_url
        self._mcp_tool_names = mcp_tool_names or []
        self._agent: Any | None = None
        self._agent_id: str | None = None

    @property
    def agent_id(self) -> Optional[str]:
        return self._agent_id

    async def create(self, **kwargs: Any) -> str:
        """Create the agent in Azure AI Foundry and return the agent ID."""
        if self._project_client is None:
            logger.warning("agent_create_skipped", name=self.name, reason="no_client")
            self._agent_id = f"local-{self.name}"
            return self._agent_id

        try:
            # _project_client is an AgentsClient directly (v2 SDK)
            self._agent = await self._project_client.create_agent(
                model=self.model,
                name=self.name,
                instructions=self.instructions,
                **kwargs,
            )
            self._agent_id = self._agent.id
            logger.info(
                "agent_created",
                name=self.name,
                agent_id=self._agent_id,
                model=self.model,
            )
            return self._agent_id
        except Exception:
            logger.exception("agent_create_failed", name=self.name)
            raise

    async def delete(self) -> None:
        """Delete the agent from Azure AI Foundry."""
        if self._agent_id and self._project_client:
            try:
                await self._project_client.delete_agent(self._agent_id)
                logger.info("agent_deleted", name=self.name, agent_id=self._agent_id)
            except Exception:
                logger.exception("agent_delete_failed", name=self.name)
        self._agent = None
        self._agent_id = None

    async def run(
        self,
        task: str,
        *,
        thread_id: str | None = None,
        on_progress: Any | None = None,
    ) -> str:
        """Run the agent with a task and return the response.

        Execution modes (in priority order):
        1. Azure AI Foundry (project_client available)
        2. Azure OpenAI + MCP tools (openai_client available)
        3. Simulated output (fallback for offline dev)
        """
        if self._project_client is None:
            # ── Mode 2a: Anthropic Claude + MCP tool calling ───────
            if self._anthropic_client and self._mcp_server_url:
                claude_model = self._anthropic_model or "claude-opus-4-20250514"
                logger.info(
                    "agent_run_claude_mcp",
                    name=self.name,
                    model=claude_model,
                    tools_count=len(self._mcp_tool_names),
                    task=task[:200],
                )
                return await run_agent_with_claude(
                    anthropic_client=self._anthropic_client,
                    model=claude_model,
                    system_prompt=self.instructions,
                    task=task,
                    mcp_server_url=self._mcp_server_url,
                    tool_names=self._mcp_tool_names,
                    agent_name=self.name,
                    on_progress=on_progress,
                )

            # ── Mode 2b: Azure OpenAI + MCP tool calling ──────────
            if self._openai_client and self._mcp_server_url:
                logger.info(
                    "agent_run_openai_mcp",
                    name=self.name,
                    model=self.model,
                    tools_count=len(self._mcp_tool_names),
                    task=task[:200],
                )
                return await run_agent_with_openai(
                    openai_client=self._openai_client,
                    model=self.model,
                    system_prompt=self.instructions,
                    task=task,
                    mcp_server_url=self._mcp_server_url,
                    tool_names=self._mcp_tool_names,
                    agent_name=self.name,
                    on_progress=on_progress,
                )

            # ── Mode 3: Simulated (no clients available) ───────────
            lo, hi = _SIMULATED_DELAYS.get(self.name, (2.0, 4.0))
            delay = random.uniform(lo, hi)
            logger.info(
                "agent_run_local_simulated",
                name=self.name,
                task=task[:100],
                simulated_delay=f"{delay:.1f}s",
            )
            await asyncio.sleep(delay)

            simulated = _SIMULATED_OUTPUTS.get(self.name)
            if simulated:
                return f"[SIMULATED] {simulated}"
            return f"[SIMULATED] [{self.name}] Task completed: {task[:200]}"

        try:
            # _project_client is an AgentsClient directly (v2 SDK)
            client = self._project_client

            # Create or reuse thread
            if thread_id is None:
                thread = await client.threads.create()
                thread_id = thread.id

            # Add user message
            await client.messages.create(
                thread_id=thread_id,
                role="user",
                content=task,
            )

            # Run the agent and wait for completion
            run = await client.runs.create_and_process(
                thread_id=thread_id,
                agent_id=self._agent_id,
            )

            if run.status == "failed":
                logger.error(
                    "agent_run_failed",
                    name=self.name,
                    error=run.last_error,
                )
                return f"Agent {self.name} failed: {run.last_error}"

            # Get the last assistant message (v2 SDK helper)
            from azure.ai.agents.models import MessageRole

            last_msg = await client.messages.get_last_message_text_by_role(
                thread_id=thread_id,
                role=MessageRole.AGENT,
            )
            return last_msg.text if last_msg else ""
        except Exception:
            logger.exception("agent_run_error", name=self.name)
            raise
