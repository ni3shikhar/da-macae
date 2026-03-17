"""
MCP Server — Exposes data-migration tools for multiple data sources
via the Model Context Protocol so that AI agents can discover and invoke them.

Supported sources:
  - SQL Server (via ODBC / FreeTDS)
  - PostgreSQL (via asyncpg)
  - MySQL / MariaDB (via aiomysql)
  - Oracle Database (via oracledb)
  - MongoDB (via motor)
  - Azure Cosmos DB (via azure-cosmos)
  - Snowflake (via snowflake-connector-python)
  - Azure Data Lake Storage Gen2 (via azure-storage-file-datalake)
  - Databricks SQL (via databricks-sql-connector)
  - Google BigQuery (via google-cloud-bigquery)
  - File-based: CSV, Parquet, JSON (via pandas / pyarrow)
  - Azure Blob Storage (via azure-storage-blob)

Runs as a standalone FastMCP server on port 8001.
"""

from __future__ import annotations

import asyncio
import io
import json
import os
from contextlib import asynccontextmanager
from typing import Any

import aioodbc  # type: ignore
import asyncpg  # type: ignore
from azure.identity.aio import DefaultAzureCredential
from azure.storage.blob.aio import BlobServiceClient
from mcp.server.fastmcp import FastMCP

# ── Initialise MCP server ────────────────────────────────────────────
mcp = FastMCP(
    "da-macae-tools",
    instructions=(
        "MCP tool server for the DA-MACAÉ data-migration accelerator. "
        "Provides tools for SQL Server, PostgreSQL, MySQL, Oracle, MongoDB, "
        "Cosmos DB, Snowflake, ADLS Gen2, Databricks, BigQuery, "
        "CSV/Parquet/JSON files, and Azure Blob Storage. "
        "Also provides pipeline/connection tools for Azure Data Factory, "
        "Synapse Analytics, and Microsoft Fabric."
    ),
    host="0.0.0.0",
    port=int(os.getenv("MCP_PORT", "8001")),
)

# ── Connection helpers ────────────────────────────────────────────────

_sql_pool: aioodbc.Pool | None = None
_pg_pool: asyncpg.Pool | None = None
_blob_client: BlobServiceClient | None = None
_mysql_pool: Any | None = None
_mongo_client: Any | None = None
_cosmos_client: Any | None = None
_datalake_client: Any | None = None


async def _get_sql_pool() -> aioodbc.Pool:
    global _sql_pool
    if _sql_pool is None:
        dsn = os.getenv(
            "SQLSERVER_DSN",
            "DRIVER={ODBC Driver 18 for SQL Server};"
            "SERVER=localhost,1433;"
            "DATABASE=master;"
            "UID=sa;PWD=YourStrong!Passw0rd;"
            "TrustServerCertificate=yes",
        )
        _sql_pool = await aioodbc.create_pool(dsn=dsn, minsize=1, maxsize=5)
    return _sql_pool


async def _get_pg_pool() -> asyncpg.Pool:
    global _pg_pool
    if _pg_pool is None:
        _pg_pool = await asyncpg.create_pool(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "postgres"),
            database=os.getenv("POSTGRES_DB", "postgres"),
            min_size=1,
            max_size=5,
        )
    return _pg_pool


# Cache of per-database pools so we don't create a new one each call
_pg_db_pools: dict[str, asyncpg.Pool] = {}

async def _get_pg_pool_for_db(database: str | None = None) -> asyncpg.Pool:
    """Return a connection pool for a specific database.

    If *database* is None or matches the default POSTGRES_DB env-var,
    the shared default pool is returned.  Otherwise a dedicated pool
    for that database is created (and cached) on the fly.
    """
    default_db = os.getenv("POSTGRES_DB", "postgres")
    if database is None or database == default_db:
        return await _get_pg_pool()

    if database not in _pg_db_pools:
        _pg_db_pools[database] = await asyncpg.create_pool(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "postgres"),
            database=database,
            min_size=1,
            max_size=3,
        )
    return _pg_db_pools[database]


async def _get_blob_client() -> BlobServiceClient:
    global _blob_client
    if _blob_client is None:
        conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        if conn_str:
            # Strip spaces injected by YAML multiline folding
            conn_str = ";".join(part.strip() for part in conn_str.split(";"))
        if conn_str:
            _blob_client = BlobServiceClient.from_connection_string(conn_str)
        else:
            account_url = os.getenv(
                "AZURE_STORAGE_ACCOUNT_URL",
                "http://127.0.0.1:10000/devstoreaccount1",
            )
            _blob_client = BlobServiceClient(account_url, credential=DefaultAzureCredential())
    return _blob_client


async def _get_mysql_pool():
    """Lazy-init MySQL connection pool."""
    global _mysql_pool
    if _mysql_pool is None:
        import aiomysql  # type: ignore

        _mysql_pool = await aiomysql.create_pool(
            host=os.getenv("MYSQL_HOST", "mysql"),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            user=os.getenv("MYSQL_USER", "root"),
            password=os.getenv("MYSQL_PASSWORD", "Dev@Password123!"),
            db=os.getenv("MYSQL_DATABASE", "information_schema"),
            minsize=1,
            maxsize=5,
        )
    return _mysql_pool


def _get_oracle_connection():
    """Create an Oracle DB connection (sync — wrapped in executor)."""
    import oracledb  # type: ignore

    return oracledb.connect(
        user=os.getenv("ORACLE_USER", "system"),
        password=os.getenv("ORACLE_PASSWORD", "Dev@Password123!"),
        dsn=os.getenv("ORACLE_DSN", "oracle:1521/FREEPDB1"),
    )


async def _get_mongo_client():
    """Lazy-init MongoDB async client."""
    global _mongo_client
    if _mongo_client is None:
        from motor.motor_asyncio import AsyncIOMotorClient  # type: ignore

        uri = os.getenv("MONGODB_URI", "mongodb://mongo:27017")
        _mongo_client = AsyncIOMotorClient(uri)
    return _mongo_client


async def _get_cosmos_client():
    """Lazy-init Azure Cosmos DB client (NoSQL API)."""
    global _cosmos_client
    if _cosmos_client is None:
        from azure.cosmos.aio import CosmosClient  # type: ignore

        endpoint = os.getenv("COSMOS_NOSQL_ENDPOINT", "https://cosmosdb:8081/")
        key = os.getenv(
            "COSMOS_NOSQL_KEY",
            "C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw==",
        )
        _cosmos_client = CosmosClient(endpoint, credential=key)
    return _cosmos_client


async def _get_datalake_client():
    """Lazy-init Azure Data Lake Storage Gen2 client."""
    global _datalake_client
    if _datalake_client is None:
        from azure.storage.filedatalake.aio import DataLakeServiceClient  # type: ignore

        conn_str = os.getenv("ADLS_CONNECTION_STRING")
        if conn_str:
            _datalake_client = DataLakeServiceClient.from_connection_string(conn_str)
        else:
            account_url = os.getenv("ADLS_ACCOUNT_URL", "")
            _datalake_client = DataLakeServiceClient(
                account_url, credential=DefaultAzureCredential()
            )
    return _datalake_client


# ── SQL Server Tools ─────────────────────────────────────────────────


@mcp.tool()
async def sql_list_databases() -> str:
    """List all user databases on the SQL Server instance."""
    pool = await _get_sql_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT name, database_id, create_date FROM sys.databases "
                "WHERE database_id > 4 ORDER BY name"
            )
            rows = await cur.fetchall()
            cols = [d[0] for d in cur.description]
            return json.dumps([dict(zip(cols, row)) for row in rows], default=str)


@mcp.tool()
async def sql_list_tables(database: str) -> str:
    """List all user tables in a SQL Server database with row counts."""
    pool = await _get_sql_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(f"USE [{database}]")
            await cur.execute(
                """
                SELECT s.name AS schema_name, t.name AS table_name,
                       p.rows AS row_count
                FROM sys.tables t
                JOIN sys.schemas s ON t.schema_id = s.schema_id
                JOIN sys.partitions p ON t.object_id = p.object_id AND p.index_id IN (0,1)
                ORDER BY s.name, t.name
                """
            )
            rows = await cur.fetchall()
            cols = [d[0] for d in cur.description]
            return json.dumps([dict(zip(cols, row)) for row in rows], default=str)


@mcp.tool()
async def sql_get_table_schema(database: str, schema: str, table: str) -> str:
    """Return column definitions for a SQL Server table."""
    pool = await _get_sql_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(f"USE [{database}]")
            await cur.execute(
                """
                SELECT c.COLUMN_NAME, c.DATA_TYPE, c.CHARACTER_MAXIMUM_LENGTH,
                       c.IS_NULLABLE, c.COLUMN_DEFAULT
                FROM INFORMATION_SCHEMA.COLUMNS c
                WHERE c.TABLE_SCHEMA = ? AND c.TABLE_NAME = ?
                ORDER BY c.ORDINAL_POSITION
                """,
                (schema, table),
            )
            rows = await cur.fetchall()
            cols = [d[0] for d in cur.description]
            return json.dumps([dict(zip(cols, row)) for row in rows], default=str)


@mcp.tool()
async def sql_execute_query(database: str, query: str, max_rows: int = 100) -> str:
    """Execute a read-only SQL query on SQL Server and return results as JSON."""
    if not query.strip().upper().startswith("SELECT"):
        return json.dumps({"error": "Only SELECT queries are permitted"})
    pool = await _get_sql_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(f"USE [{database}]")
            await cur.execute(query)
            rows = await cur.fetchmany(max_rows)
            cols = [d[0] for d in cur.description]
            return json.dumps(
                {"columns": cols, "rows": [dict(zip(cols, r)) for r in rows], "truncated": len(rows) == max_rows},
                default=str,
            )


@mcp.tool()
async def sql_get_relationships(database: str) -> str:
    """Return foreign key relationships between tables."""
    pool = await _get_sql_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(f"USE [{database}]")
            await cur.execute(
                """
                SELECT fk.name AS fk_name,
                       OBJECT_SCHEMA_NAME(fk.parent_object_id) AS parent_schema,
                       OBJECT_NAME(fk.parent_object_id) AS parent_table,
                       COL_NAME(fkc.parent_object_id, fkc.parent_column_id) AS parent_column,
                       OBJECT_SCHEMA_NAME(fk.referenced_object_id) AS ref_schema,
                       OBJECT_NAME(fk.referenced_object_id) AS ref_table,
                       COL_NAME(fkc.referenced_object_id, fkc.referenced_column_id) AS ref_column
                FROM sys.foreign_keys fk
                JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
                ORDER BY parent_table, fk_name
                """
            )
            rows = await cur.fetchall()
            cols = [d[0] for d in cur.description]
            return json.dumps([dict(zip(cols, row)) for row in rows], default=str)


# ── PostgreSQL Tools ─────────────────────────────────────────────────


@mcp.tool()
async def pg_list_databases() -> str:
    """List all databases on the PostgreSQL instance with their schemas.

    Returns each database with its size and the list of non-system schemas.
    **Tip**: Use the database name from this output as the ``database``
    parameter in pg_list_tables, pg_get_table_schema, pg_execute_query, etc.
    to query tables inside that specific database.
    """
    pool = await _get_pg_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT datname, pg_database_size(datname) AS size_bytes "
            "FROM pg_database WHERE datistemplate = false ORDER BY datname"
        )
    results = []
    for r in rows:
        db_name = r["datname"]
        schemas: list[str] = []
        try:
            db_pool = await _get_pg_pool_for_db(db_name)
            async with db_pool.acquire() as db_conn:
                schema_rows = await db_conn.fetch(
                    "SELECT schema_name FROM information_schema.schemata "
                    "WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast') "
                    "ORDER BY schema_name"
                )
                schemas = [sr["schema_name"] for sr in schema_rows]
        except Exception:
            schemas = ["<unable to connect>"]
        results.append({
            "datname": db_name,
            "size_bytes": r["size_bytes"],
            "schemas": schemas,
        })
    return json.dumps(results, default=str)


@mcp.tool()
async def pg_list_schemas(database: str) -> str:
    """List all user schemas in a PostgreSQL database with table counts.

    Args:
        database: The database to connect to (e.g. 'adventureworks').
    """
    pool = await _get_pg_pool_for_db(database or None)
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT s.schema_name,
                   COUNT(t.table_name) AS table_count
            FROM information_schema.schemata s
            LEFT JOIN information_schema.tables t
                ON t.table_schema = s.schema_name AND t.table_type = 'BASE TABLE'
            WHERE s.schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
            GROUP BY s.schema_name
            ORDER BY s.schema_name
            """
        )
        return json.dumps([dict(r) for r in rows], default=str)


@mcp.tool()
async def pg_get_foreign_keys(database: str, schema: str = "public") -> str:
    """List all foreign key relationships in a PostgreSQL database/schema.

    Args:
        database: The database to connect to (e.g. 'adventureworks').
        schema:   Schema to inspect (default 'public'). Pass empty string
                  to return foreign keys from ALL schemas.
    """
    pool = await _get_pg_pool_for_db(database or None)
    async with pool.acquire() as conn:
        if schema:
            rows = await conn.fetch(
                """
                SELECT
                    tc.table_schema,
                    tc.table_name       AS source_table,
                    kcu.column_name     AS source_column,
                    ccu.table_schema    AS target_schema,
                    ccu.table_name      AS target_table,
                    ccu.column_name     AS target_column,
                    tc.constraint_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                   AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage ccu
                    ON tc.constraint_name = ccu.constraint_name
                   AND tc.table_schema = ccu.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY'
                  AND tc.table_schema = $1
                ORDER BY tc.table_name, kcu.column_name
                """,
                schema,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT
                    tc.table_schema,
                    tc.table_name       AS source_table,
                    kcu.column_name     AS source_column,
                    ccu.table_schema    AS target_schema,
                    ccu.table_name      AS target_table,
                    ccu.column_name     AS target_column,
                    tc.constraint_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                   AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage ccu
                    ON tc.constraint_name = ccu.constraint_name
                   AND tc.table_schema = ccu.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY'
                  AND tc.table_schema NOT IN ('pg_catalog', 'information_schema')
                ORDER BY tc.table_schema, tc.table_name, kcu.column_name
                """
            )
        return json.dumps([dict(r) for r in rows], default=str)


@mcp.tool()
async def pg_list_tables(database: str = "", schema: str = "") -> str:
    """List tables in a PostgreSQL database/schema with row-count estimates.

    Args:
        database: Target database name (e.g. 'adventureworks'). Leave empty
                  to use the default connection. **Important**: PostgreSQL
                  requires a separate connection per database, so always
                  specify the database you want to query.
        schema:   Schema name (e.g. 'humanresources'). Leave empty to list
                  tables from ALL user schemas in the database.
    """
    pool = await _get_pg_pool_for_db(database or None)
    async with pool.acquire() as conn:
        if schema:
            rows = await conn.fetch(
                """
                SELECT schemaname, relname AS tablename, n_live_tup AS est_rows
                FROM pg_stat_user_tables
                WHERE schemaname = $1
                ORDER BY schemaname, relname
                """,
                schema,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT schemaname, relname AS tablename, n_live_tup AS est_rows
                FROM pg_stat_user_tables
                ORDER BY schemaname, relname
                """
            )
        return json.dumps([dict(r) for r in rows], default=str)


@mcp.tool()
async def pg_get_table_schema(schema: str, table: str, database: str = "") -> str:
    """Return column definitions for a PostgreSQL table.

    Args:
        schema:   Schema name (e.g. 'public', 'humanresources').
        table:    Table name.
        database: Target database name. Leave empty to use the default
                  connection. Specify the database explicitly when
                  querying a database other than the default.
    """
    pool = await _get_pg_pool_for_db(database or None)
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT column_name, data_type, character_maximum_length,
                   is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = $1 AND table_name = $2
            ORDER BY ordinal_position
            """,
            schema,
            table,
        )
        return json.dumps([dict(r) for r in rows], default=str)


@mcp.tool()
async def pg_execute_query(query: str, database: str = "", max_rows: int = 100) -> str:
    """Execute a read-only SQL query on PostgreSQL and return results as JSON.

    Args:
        query:    A SELECT query to execute.
        database: Target database name. Leave empty to use the default
                  connection. Specify the database when querying tables
                  in a specific database (e.g. 'adventureworks').
        max_rows: Maximum rows to return (default 100).
    """
    if not query.strip().upper().startswith("SELECT"):
        return json.dumps({"error": "Only SELECT queries are permitted"})
    pool = await _get_pg_pool_for_db(database or None)
    async with pool.acquire() as conn:
        async with conn.transaction(readonly=True):
            rows = await conn.fetch(query)
            result = [dict(r) for r in rows[:max_rows]]
            return json.dumps(
                {"rows": result, "truncated": len(rows) > max_rows}, default=str
            )


@mcp.tool()
async def pg_create_table(schema: str, create_ddl: str, database: str = "") -> str:
    """Execute CREATE TABLE DDL on PostgreSQL. Returns success or error.

    Args:
        schema:     Schema name to set as search_path.
        create_ddl: The CREATE TABLE statement.
        database:   Target database name. Leave empty to use the default
                    connection.
    """
    if "DROP" in create_ddl.upper():
        return json.dumps({"error": "DROP statements not allowed"})
    pool = await _get_pg_pool_for_db(database or None)
    async with pool.acquire() as conn:
        await conn.execute(f"SET search_path TO {schema}")
        await conn.execute(create_ddl)
        return json.dumps({"status": "ok", "ddl": create_ddl})


# ── Azure Storage Tools ──────────────────────────────────────────────


@mcp.tool()
async def storage_list_containers() -> str:
    """List all blob containers in the Azure Storage account."""
    client = await _get_blob_client()
    containers = []
    async for c in client.list_containers():
        containers.append({"name": c.name, "last_modified": str(c.last_modified)})
    return json.dumps(containers)


@mcp.tool()
async def storage_list_blobs(container: str, prefix: str = "") -> str:
    """List blobs in a container, optionally filtered by prefix."""
    client = await _get_blob_client()
    cc = client.get_container_client(container)
    blobs = []
    async for b in cc.list_blobs(name_starts_with=prefix or None):
        blobs.append(
            {"name": b.name, "size": b.size, "last_modified": str(b.last_modified)}
        )
    return json.dumps(blobs)


@mcp.tool()
async def storage_read_blob(container: str, blob_name: str, max_bytes: int = 1_000_000) -> str:
    """Read text content from a blob (up to max_bytes)."""
    client = await _get_blob_client()
    bc = client.get_blob_client(container, blob_name)
    data = await bc.download_blob(max_concurrency=1, length=max_bytes)
    content = await data.readall()
    return content.decode("utf-8", errors="replace")


@mcp.tool()
async def storage_upload_blob(container: str, blob_name: str, content: str) -> str:
    """Upload text content to a blob, creating the container if needed."""
    client = await _get_blob_client()
    cc = client.get_container_client(container)
    try:
        await cc.create_container()
    except Exception:
        pass  # already exists
    bc = cc.get_blob_client(blob_name)
    await bc.upload_blob(content.encode(), overwrite=True)
    return json.dumps({"status": "uploaded", "container": container, "blob": blob_name})


# ── MySQL / MariaDB Tools ────────────────────────────────────────────


@mcp.tool()
async def mysql_list_databases() -> str:
    """List all databases on the MySQL/MariaDB instance."""
    pool = await _get_mysql_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT SCHEMA_NAME, DEFAULT_CHARACTER_SET_NAME "
                "FROM information_schema.SCHEMATA "
                "WHERE SCHEMA_NAME NOT IN ('information_schema','mysql','performance_schema','sys') "
                "ORDER BY SCHEMA_NAME"
            )
            rows = await cur.fetchall()
            return json.dumps(
                [{"database": r[0], "charset": r[1]} for r in rows], default=str
            )


@mcp.tool()
async def mysql_list_tables(database: str) -> str:
    """List all tables in a MySQL database with row-count estimates."""
    pool = await _get_mysql_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT TABLE_NAME, TABLE_ROWS, ENGINE, TABLE_COLLATION "
                "FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE' "
                "ORDER BY TABLE_NAME",
                (database,),
            )
            rows = await cur.fetchall()
            return json.dumps(
                [{"table": r[0], "est_rows": r[1], "engine": r[2], "collation": r[3]} for r in rows],
                default=str,
            )


@mcp.tool()
async def mysql_get_table_schema(database: str, table: str) -> str:
    """Return column definitions for a MySQL table."""
    pool = await _get_mysql_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, "
                "IS_NULLABLE, COLUMN_DEFAULT, COLUMN_KEY "
                "FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s "
                "ORDER BY ORDINAL_POSITION",
                (database, table),
            )
            rows = await cur.fetchall()
            return json.dumps(
                [
                    {
                        "column_name": r[0], "data_type": r[1],
                        "character_maximum_length": r[2], "is_nullable": r[3],
                        "column_default": r[4], "column_key": r[5],
                    }
                    for r in rows
                ],
                default=str,
            )


@mcp.tool()
async def mysql_execute_query(database: str, query: str, max_rows: int = 100) -> str:
    """Execute a read-only SQL query on MySQL and return results as JSON."""
    if not query.strip().upper().startswith("SELECT"):
        return json.dumps({"error": "Only SELECT queries are permitted"})
    pool = await _get_mysql_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(f"USE `{database}`")
            await cur.execute(query)
            rows = await cur.fetchmany(max_rows)
            cols = [d[0] for d in cur.description] if cur.description else []
            return json.dumps(
                {"columns": cols, "rows": [dict(zip(cols, r)) for r in rows], "truncated": len(rows) == max_rows},
                default=str,
            )


@mcp.tool()
async def mysql_get_relationships(database: str) -> str:
    """Return foreign key relationships in a MySQL database."""
    pool = await _get_mysql_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT CONSTRAINT_NAME, TABLE_NAME, COLUMN_NAME, "
                "REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME "
                "FROM information_schema.KEY_COLUMN_USAGE "
                "WHERE TABLE_SCHEMA = %s AND REFERENCED_TABLE_NAME IS NOT NULL "
                "ORDER BY TABLE_NAME, CONSTRAINT_NAME",
                (database,),
            )
            rows = await cur.fetchall()
            return json.dumps(
                [
                    {
                        "fk_name": r[0], "table": r[1], "column": r[2],
                        "ref_table": r[3], "ref_column": r[4],
                    }
                    for r in rows
                ],
                default=str,
            )


# ── Oracle Database Tools ────────────────────────────────────────────


@mcp.tool()
async def oracle_list_schemas() -> str:
    """List all user schemas in the Oracle database."""
    loop = asyncio.get_running_loop()

    def _query():
        conn = _get_oracle_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT username, created FROM dba_users "
                    "WHERE oracle_maintained = 'N' ORDER BY username"
                )
                rows = cur.fetchall()
                cols = [d[0].lower() for d in cur.description]
                return [dict(zip(cols, r)) for r in rows]
        finally:
            conn.close()

    result = await loop.run_in_executor(None, _query)
    return json.dumps(result, default=str)


@mcp.tool()
async def oracle_list_tables(owner: str) -> str:
    """List all tables owned by a schema in Oracle."""
    loop = asyncio.get_running_loop()

    def _query():
        conn = _get_oracle_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT table_name, num_rows, tablespace_name "
                    "FROM all_tables WHERE owner = :owner ORDER BY table_name",
                    {"owner": owner.upper()},
                )
                rows = cur.fetchall()
                cols = [d[0].lower() for d in cur.description]
                return [dict(zip(cols, r)) for r in rows]
        finally:
            conn.close()

    result = await loop.run_in_executor(None, _query)
    return json.dumps(result, default=str)


@mcp.tool()
async def oracle_get_table_schema(owner: str, table: str) -> str:
    """Return column definitions for an Oracle table."""
    loop = asyncio.get_running_loop()

    def _query():
        conn = _get_oracle_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT column_name, data_type, data_length, data_precision, "
                    "data_scale, nullable, data_default "
                    "FROM all_tab_columns "
                    "WHERE owner = :owner AND table_name = :tbl "
                    "ORDER BY column_id",
                    {"owner": owner.upper(), "tbl": table.upper()},
                )
                rows = cur.fetchall()
                cols = [d[0].lower() for d in cur.description]
                return [dict(zip(cols, r)) for r in rows]
        finally:
            conn.close()

    result = await loop.run_in_executor(None, _query)
    return json.dumps(result, default=str)


@mcp.tool()
async def oracle_execute_query(query: str, max_rows: int = 100) -> str:
    """Execute a read-only SQL query on Oracle and return results as JSON."""
    if not query.strip().upper().startswith("SELECT"):
        return json.dumps({"error": "Only SELECT queries are permitted"})
    loop = asyncio.get_running_loop()

    def _query():
        conn = _get_oracle_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(query)
                rows = cur.fetchmany(max_rows)
                cols = [d[0].lower() for d in cur.description]
                return {
                    "columns": cols,
                    "rows": [dict(zip(cols, r)) for r in rows],
                    "truncated": len(rows) == max_rows,
                }
        finally:
            conn.close()

    result = await loop.run_in_executor(None, _query)
    return json.dumps(result, default=str)


@mcp.tool()
async def oracle_get_relationships(owner: str) -> str:
    """Return foreign key relationships in an Oracle schema."""
    loop = asyncio.get_running_loop()

    def _query():
        conn = _get_oracle_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT a.constraint_name, a.table_name, a.column_name,
                           c_pk.table_name AS ref_table, b.column_name AS ref_column
                    FROM all_cons_columns a
                    JOIN all_constraints c ON a.constraint_name = c.constraint_name AND a.owner = c.owner
                    JOIN all_constraints c_pk ON c.r_constraint_name = c_pk.constraint_name AND c.r_owner = c_pk.owner
                    JOIN all_cons_columns b ON c_pk.constraint_name = b.constraint_name AND c_pk.owner = b.owner
                    WHERE c.constraint_type = 'R' AND a.owner = :owner
                    ORDER BY a.table_name, a.constraint_name
                    """,
                    {"owner": owner.upper()},
                )
                rows = cur.fetchall()
                cols = [d[0].lower() for d in cur.description]
                return [dict(zip(cols, r)) for r in rows]
        finally:
            conn.close()

    result = await loop.run_in_executor(None, _query)
    return json.dumps(result, default=str)


# ── MongoDB Tools ────────────────────────────────────────────────────


@mcp.tool()
async def mongo_list_databases() -> str:
    """List all databases on the MongoDB instance."""
    client = await _get_mongo_client()
    db_list = await client.list_database_names()
    result = []
    for name in db_list:
        if name not in ("admin", "config", "local"):
            stats = await client[name].command("dbStats")
            result.append({
                "database": name,
                "collections": stats.get("collections", 0),
                "size_bytes": stats.get("dataSize", 0),
            })
    return json.dumps(result, default=str)


@mcp.tool()
async def mongo_list_collections(database: str) -> str:
    """List all collections in a MongoDB database with document counts."""
    client = await _get_mongo_client()
    db = client[database]
    collections = await db.list_collection_names()
    result = []
    for coll_name in sorted(collections):
        count = await db[coll_name].estimated_document_count()
        result.append({"collection": coll_name, "est_documents": count})
    return json.dumps(result, default=str)


@mcp.tool()
async def mongo_get_collection_schema(database: str, collection: str, sample_size: int = 100) -> str:
    """Infer schema of a MongoDB collection by sampling documents."""
    client = await _get_mongo_client()
    db = client[database]
    coll = db[collection]
    docs = await coll.find().limit(sample_size).to_list(length=sample_size)

    # Merge field info across sampled docs
    fields: dict[str, dict[str, Any]] = {}
    for doc in docs:
        for key, val in doc.items():
            if key not in fields:
                fields[key] = {"types": set(), "nullable": False, "sample": None}
            fields[key]["types"].add(type(val).__name__)
            if val is None:
                fields[key]["nullable"] = True
            elif fields[key]["sample"] is None:
                fields[key]["sample"] = str(val)[:200]

    schema = []
    for fname, info in fields.items():
        schema.append({
            "field": fname,
            "types": sorted(info["types"]),
            "nullable": info["nullable"],
            "sample": info["sample"],
        })
    return json.dumps({"collection": collection, "sampled_docs": len(docs), "fields": schema}, default=str)


@mcp.tool()
async def mongo_execute_query(database: str, collection: str, filter_json: str = "{}", max_docs: int = 100) -> str:
    """Execute a find query on a MongoDB collection. filter_json is a JSON query filter."""
    client = await _get_mongo_client()
    db = client[database]
    coll = db[collection]
    query_filter = json.loads(filter_json)
    docs = await coll.find(query_filter).limit(max_docs).to_list(length=max_docs)
    # Convert ObjectId etc. to string
    for doc in docs:
        for k, v in doc.items():
            if not isinstance(v, (str, int, float, bool, list, dict, type(None))):
                doc[k] = str(v)
    return json.dumps({"documents": docs, "count": len(docs), "truncated": len(docs) == max_docs}, default=str)


@mcp.tool()
async def mongo_get_indexes(database: str, collection: str) -> str:
    """List all indexes on a MongoDB collection."""
    client = await _get_mongo_client()
    db = client[database]
    coll = db[collection]
    indexes = []
    async for idx in coll.list_indexes():
        indexes.append({
            "name": idx.get("name"),
            "keys": {k: v for k, v in idx.get("key", {}).items()},
            "unique": idx.get("unique", False),
        })
    return json.dumps(indexes, default=str)


# ── Azure Cosmos DB (NoSQL API) Tools ────────────────────────────────


@mcp.tool()
async def cosmos_list_databases() -> str:
    """List all databases in the Cosmos DB account."""
    client = await _get_cosmos_client()
    databases = []
    async for db_props in client.list_databases():
        databases.append({"id": db_props["id"]})
    return json.dumps(databases, default=str)


@mcp.tool()
async def cosmos_list_containers(database: str) -> str:
    """List all containers in a Cosmos DB database."""
    client = await _get_cosmos_client()
    db = client.get_database_client(database)
    containers = []
    async for c in db.list_containers():
        containers.append({
            "id": c["id"],
            "partition_key": str(c.get("partitionKey", {}).get("paths", [])),
        })
    return json.dumps(containers, default=str)


@mcp.tool()
async def cosmos_query_items(database: str, container: str, query: str = "SELECT * FROM c", max_items: int = 100) -> str:
    """Execute a SQL query on a Cosmos DB container."""
    client = await _get_cosmos_client()
    db = client.get_database_client(database)
    cont = db.get_container_client(container)
    items = []
    async for item in cont.query_items(query=query, max_item_count=max_items):
        items.append(item)
        if len(items) >= max_items:
            break
    return json.dumps({"items": items, "count": len(items), "truncated": len(items) >= max_items}, default=str)


@mcp.tool()
async def cosmos_get_container_schema(database: str, container: str, sample_size: int = 50) -> str:
    """Infer schema of a Cosmos DB container by sampling items."""
    client = await _get_cosmos_client()
    db = client.get_database_client(database)
    cont = db.get_container_client(container)
    items = []
    async for item in cont.query_items(query="SELECT * FROM c", max_item_count=sample_size):
        items.append(item)
        if len(items) >= sample_size:
            break

    fields: dict[str, set] = {}
    for item in items:
        for key, val in item.items():
            if key.startswith("_"):
                continue
            if key not in fields:
                fields[key] = set()
            fields[key].add(type(val).__name__)

    schema = [{"field": k, "types": sorted(v)} for k, v in fields.items()]
    return json.dumps({"container": container, "sampled_items": len(items), "fields": schema}, default=str)


# ── Snowflake Tools ──────────────────────────────────────────────────


def _get_snowflake_connection():
    """Create a Snowflake connection (sync — wrapped in executor)."""
    import snowflake.connector  # type: ignore

    return snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT", ""),
        user=os.getenv("SNOWFLAKE_USER", ""),
        password=os.getenv("SNOWFLAKE_PASSWORD", ""),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
        database=os.getenv("SNOWFLAKE_DATABASE", ""),
        schema=os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC"),
        role=os.getenv("SNOWFLAKE_ROLE", ""),
    )


@mcp.tool()
async def snowflake_list_databases() -> str:
    """List all databases accessible in Snowflake."""
    loop = asyncio.get_running_loop()

    def _query():
        conn = _get_snowflake_connection()
        try:
            cur = conn.cursor()
            cur.execute("SHOW DATABASES")
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in rows]
        finally:
            conn.close()

    result = await loop.run_in_executor(None, _query)
    return json.dumps(result, default=str)


@mcp.tool()
async def snowflake_list_tables(database: str, schema: str = "PUBLIC") -> str:
    """List all tables in a Snowflake database/schema."""
    loop = asyncio.get_running_loop()

    def _query():
        conn = _get_snowflake_connection()
        try:
            cur = conn.cursor()
            cur.execute(f"SHOW TABLES IN {database}.{schema}")
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in rows]
        finally:
            conn.close()

    result = await loop.run_in_executor(None, _query)
    return json.dumps(result, default=str)


@mcp.tool()
async def snowflake_get_table_schema(database: str, schema: str, table: str) -> str:
    """Return column definitions for a Snowflake table."""
    loop = asyncio.get_running_loop()

    def _query():
        conn = _get_snowflake_connection()
        try:
            cur = conn.cursor()
            cur.execute(f"DESCRIBE TABLE {database}.{schema}.{table}")
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in rows]
        finally:
            conn.close()

    result = await loop.run_in_executor(None, _query)
    return json.dumps(result, default=str)


@mcp.tool()
async def snowflake_execute_query(query: str, max_rows: int = 100) -> str:
    """Execute a read-only SQL query on Snowflake and return results as JSON."""
    if not query.strip().upper().startswith("SELECT"):
        return json.dumps({"error": "Only SELECT queries are permitted"})
    loop = asyncio.get_running_loop()

    def _query():
        conn = _get_snowflake_connection()
        try:
            cur = conn.cursor()
            cur.execute(query)
            rows = cur.fetchmany(max_rows)
            cols = [d[0] for d in cur.description]
            return {
                "columns": cols,
                "rows": [dict(zip(cols, r)) for r in rows],
                "truncated": len(rows) == max_rows,
            }
        finally:
            conn.close()

    result = await loop.run_in_executor(None, _query)
    return json.dumps(result, default=str)


# ── Azure Data Lake Storage Gen2 Tools ───────────────────────────────


@mcp.tool()
async def adls_list_filesystems() -> str:
    """List all file systems (containers) in ADLS Gen2."""
    client = await _get_datalake_client()
    filesystems = []
    async for fs in client.list_file_systems():
        filesystems.append({"name": fs.name, "last_modified": str(fs.last_modified)})
    return json.dumps(filesystems, default=str)


@mcp.tool()
async def adls_list_paths(filesystem: str, path: str = "/", recursive: bool = False) -> str:
    """List files and directories in an ADLS Gen2 file system."""
    client = await _get_datalake_client()
    fs_client = client.get_file_system_client(filesystem)
    paths = []
    async for p in fs_client.get_paths(path=path, recursive=recursive):
        paths.append({
            "name": p.name,
            "is_directory": p.is_directory,
            "content_length": p.content_length,
            "last_modified": str(p.last_modified),
        })
    return json.dumps(paths, default=str)


@mcp.tool()
async def adls_read_file(filesystem: str, file_path: str, max_bytes: int = 1_000_000) -> str:
    """Read text content from a file in ADLS Gen2."""
    client = await _get_datalake_client()
    fs_client = client.get_file_system_client(filesystem)
    file_client = fs_client.get_file_client(file_path)
    download = await file_client.download_file(length=max_bytes)
    content = await download.readall()
    return content.decode("utf-8", errors="replace")


@mcp.tool()
async def adls_upload_file(filesystem: str, file_path: str, content: str) -> str:
    """Upload text content to a file in ADLS Gen2."""
    client = await _get_datalake_client()
    fs_client = client.get_file_system_client(filesystem)
    file_client = fs_client.get_file_client(file_path)
    await file_client.upload_data(content.encode(), overwrite=True)
    return json.dumps({"status": "uploaded", "filesystem": filesystem, "path": file_path})


# ── Databricks SQL Tools ─────────────────────────────────────────────


def _get_databricks_connection():
    """Create a Databricks SQL connection (sync — wrapped in executor)."""
    from databricks import sql as dbsql  # type: ignore

    return dbsql.connect(
        server_hostname=os.getenv("DATABRICKS_HOST", ""),
        http_path=os.getenv("DATABRICKS_HTTP_PATH", ""),
        access_token=os.getenv("DATABRICKS_TOKEN", ""),
    )


@mcp.tool()
async def databricks_list_schemas(catalog: str = "main") -> str:
    """List all schemas in a Databricks Unity Catalog."""
    loop = asyncio.get_running_loop()

    def _query():
        conn = _get_databricks_connection()
        try:
            cur = conn.cursor()
            cur.execute(f"SHOW SCHEMAS IN {catalog}")
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in rows]
        finally:
            conn.close()

    result = await loop.run_in_executor(None, _query)
    return json.dumps(result, default=str)


@mcp.tool()
async def databricks_list_tables(catalog: str, schema: str) -> str:
    """List all tables in a Databricks catalog.schema."""
    loop = asyncio.get_running_loop()

    def _query():
        conn = _get_databricks_connection()
        try:
            cur = conn.cursor()
            cur.execute(f"SHOW TABLES IN {catalog}.{schema}")
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in rows]
        finally:
            conn.close()

    result = await loop.run_in_executor(None, _query)
    return json.dumps(result, default=str)


@mcp.tool()
async def databricks_get_table_schema(catalog: str, schema: str, table: str) -> str:
    """Return column definitions for a Databricks table."""
    loop = asyncio.get_running_loop()

    def _query():
        conn = _get_databricks_connection()
        try:
            cur = conn.cursor()
            cur.execute(f"DESCRIBE TABLE {catalog}.{schema}.{table}")
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in rows]
        finally:
            conn.close()

    result = await loop.run_in_executor(None, _query)
    return json.dumps(result, default=str)


@mcp.tool()
async def databricks_execute_query(query: str, max_rows: int = 100) -> str:
    """Execute a read-only SQL query on Databricks and return results as JSON."""
    if not query.strip().upper().startswith("SELECT"):
        return json.dumps({"error": "Only SELECT queries are permitted"})
    loop = asyncio.get_running_loop()

    def _query_fn():
        conn = _get_databricks_connection()
        try:
            cur = conn.cursor()
            cur.execute(query)
            rows = cur.fetchmany(max_rows)
            cols = [d[0] for d in cur.description]
            return {
                "columns": cols,
                "rows": [dict(zip(cols, r)) for r in rows],
                "truncated": len(rows) == max_rows,
            }
        finally:
            conn.close()

    result = await loop.run_in_executor(None, _query_fn)
    return json.dumps(result, default=str)


# ── Google BigQuery Tools ────────────────────────────────────────────


def _get_bigquery_client():
    """Create a BigQuery client (sync — wrapped in executor)."""
    from google.cloud import bigquery  # type: ignore

    project = os.getenv("BIGQUERY_PROJECT", "")
    return bigquery.Client(project=project) if project else bigquery.Client()


@mcp.tool()
async def bigquery_list_datasets() -> str:
    """List all datasets in the BigQuery project."""
    loop = asyncio.get_running_loop()

    def _query():
        client = _get_bigquery_client()
        datasets = list(client.list_datasets())
        return [{"dataset_id": ds.dataset_id, "project": ds.project} for ds in datasets]

    result = await loop.run_in_executor(None, _query)
    return json.dumps(result, default=str)


@mcp.tool()
async def bigquery_list_tables(dataset: str) -> str:
    """List all tables in a BigQuery dataset."""
    loop = asyncio.get_running_loop()

    def _query():
        client = _get_bigquery_client()
        tables = list(client.list_tables(dataset))
        return [
            {"table_id": t.table_id, "table_type": t.table_type, "num_rows": t.num_rows}
            for t in tables
        ]

    result = await loop.run_in_executor(None, _query)
    return json.dumps(result, default=str)


@mcp.tool()
async def bigquery_get_table_schema(dataset: str, table: str) -> str:
    """Return column definitions for a BigQuery table."""
    loop = asyncio.get_running_loop()

    def _query():
        client = _get_bigquery_client()
        tbl = client.get_table(f"{dataset}.{table}")
        return [
            {
                "column_name": f.name, "data_type": f.field_type,
                "mode": f.mode, "description": f.description,
            }
            for f in tbl.schema
        ]

    result = await loop.run_in_executor(None, _query)
    return json.dumps(result, default=str)


@mcp.tool()
async def bigquery_execute_query(query: str, max_rows: int = 100) -> str:
    """Execute a read-only SQL query on BigQuery and return results as JSON."""
    if not query.strip().upper().startswith("SELECT"):
        return json.dumps({"error": "Only SELECT queries are permitted"})
    loop = asyncio.get_running_loop()

    def _query_fn():
        client = _get_bigquery_client()
        result = client.query(query).result()
        rows = []
        for row in result:
            if len(rows) >= max_rows:
                break
            rows.append(dict(row))
        return {
            "rows": rows,
            "total_rows": result.total_rows,
            "truncated": len(rows) >= max_rows,
        }

    result = await loop.run_in_executor(None, _query_fn)
    return json.dumps(result, default=str)


# ── File-Based Tools (CSV, Parquet, JSON) ────────────────────────────


@mcp.tool()
async def file_read_csv(container: str, blob_name: str, max_rows: int = 500) -> str:
    """Read a CSV file from Azure Blob Storage and return as JSON.

    Parses the CSV using pandas and returns column info + first N rows.
    """
    import pandas as pd  # type: ignore

    client = await _get_blob_client()
    bc = client.get_blob_client(container, blob_name)
    download = await bc.download_blob()
    content = await download.readall()
    df = pd.read_csv(io.BytesIO(content), nrows=max_rows)
    return json.dumps({
        "columns": [{"name": c, "dtype": str(df[c].dtype)} for c in df.columns],
        "row_count": len(df),
        "rows": df.head(max_rows).to_dict(orient="records"),
        "truncated": len(df) >= max_rows,
    }, default=str)


@mcp.tool()
async def file_read_parquet(container: str, blob_name: str, max_rows: int = 500) -> str:
    """Read a Parquet file from Azure Blob Storage and return as JSON.

    Uses pyarrow to read the Parquet schema + first N rows.
    """
    import pyarrow.parquet as pq  # type: ignore

    client = await _get_blob_client()
    bc = client.get_blob_client(container, blob_name)
    download = await bc.download_blob()
    content = await download.readall()
    table = pq.read_table(io.BytesIO(content))
    schema_info = [{"name": f.name, "type": str(f.type)} for f in table.schema]
    df = table.slice(0, max_rows).to_pandas()
    return json.dumps({
        "schema": schema_info,
        "total_rows": table.num_rows,
        "rows": df.to_dict(orient="records"),
        "truncated": table.num_rows > max_rows,
    }, default=str)


@mcp.tool()
async def file_read_json_blob(container: str, blob_name: str, max_items: int = 500) -> str:
    """Read a JSON or JSONL file from Azure Blob Storage and return as structured data.

    Handles both single JSON objects/arrays and newline-delimited JSON (JSONL).
    """
    client = await _get_blob_client()
    bc = client.get_blob_client(container, blob_name)
    download = await bc.download_blob()
    content = (await download.readall()).decode("utf-8", errors="replace")

    # Try as single JSON first
    try:
        data = json.loads(content)
        if isinstance(data, list):
            items = data[:max_items]
        else:
            items = [data]
        return json.dumps({
            "format": "json",
            "items": items,
            "count": len(items),
            "truncated": isinstance(data, list) and len(data) > max_items,
        }, default=str)
    except json.JSONDecodeError:
        pass

    # Try as JSONL
    items = []
    for line in content.strip().splitlines():
        if line.strip():
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        if len(items) >= max_items:
            break
    return json.dumps({
        "format": "jsonl",
        "items": items,
        "count": len(items),
        "truncated": len(items) >= max_items,
    }, default=str)


@mcp.tool()
async def file_infer_schema(container: str, blob_name: str) -> str:
    """Infer the schema of a CSV or Parquet file in Azure Blob Storage.

    Detects format by extension and returns column names, types, nullability.
    """
    client = await _get_blob_client()
    bc = client.get_blob_client(container, blob_name)
    download = await bc.download_blob()
    content = await download.readall()
    lower = blob_name.lower()

    if lower.endswith(".parquet"):
        import pyarrow.parquet as pq  # type: ignore

        table = pq.read_table(io.BytesIO(content))
        schema = [
            {"column": f.name, "type": str(f.type), "nullable": f.nullable}
            for f in table.schema
        ]
        return json.dumps({"format": "parquet", "columns": schema, "total_rows": table.num_rows}, default=str)
    else:
        import pandas as pd  # type: ignore

        df = pd.read_csv(io.BytesIO(content), nrows=1000)
        schema = [
            {"column": c, "type": str(df[c].dtype), "nulls": int(df[c].isnull().sum()), "sample": str(df[c].iloc[0]) if len(df) > 0 else None}
            for c in df.columns
        ]
        return json.dumps({"format": "csv", "columns": schema, "sampled_rows": len(df)}, default=str)


# ── Migration-specific Tools ─────────────────────────────────────────


@mcp.tool()
async def generate_type_mapping(source_type: str, target_type: str, columns_json: str) -> str:
    """
    Generate data-type mappings from source DB to target DB.
    columns_json should be a JSON array of {column_name, data_type, ...}.
    Supports mappings: SQL Server, MySQL, Oracle → PostgreSQL, Snowflake, BigQuery.
    """
    # ── Comprehensive type mapping dictionaries ──
    sql_to_pg: dict[str, str] = {
        "int": "integer", "bigint": "bigint", "smallint": "smallint",
        "tinyint": "smallint", "bit": "boolean",
        "decimal": "numeric", "numeric": "numeric",
        "money": "numeric(19,4)", "smallmoney": "numeric(10,4)",
        "float": "double precision", "real": "real",
        "datetime": "timestamp", "datetime2": "timestamp",
        "smalldatetime": "timestamp", "date": "date", "time": "time",
        "datetimeoffset": "timestamptz",
        "char": "char", "varchar": "varchar", "nchar": "char",
        "nvarchar": "varchar", "text": "text", "ntext": "text",
        "binary": "bytea", "varbinary": "bytea", "image": "bytea",
        "uniqueidentifier": "uuid", "xml": "xml", "sql_variant": "text",
    }

    mysql_to_pg: dict[str, str] = {
        "int": "integer", "bigint": "bigint", "smallint": "smallint",
        "tinyint": "smallint", "mediumint": "integer",
        "decimal": "numeric", "numeric": "numeric", "float": "real",
        "double": "double precision",
        "datetime": "timestamp", "timestamp": "timestamptz",
        "date": "date", "time": "time", "year": "smallint",
        "char": "char", "varchar": "varchar",
        "tinytext": "text", "text": "text", "mediumtext": "text", "longtext": "text",
        "tinyblob": "bytea", "blob": "bytea", "mediumblob": "bytea", "longblob": "bytea",
        "binary": "bytea", "varbinary": "bytea",
        "enum": "varchar(255)", "set": "varchar(255)",
        "json": "jsonb", "bit": "boolean",
    }

    oracle_to_pg: dict[str, str] = {
        "number": "numeric", "float": "double precision",
        "binary_float": "real", "binary_double": "double precision",
        "varchar2": "varchar", "nvarchar2": "varchar",
        "char": "char", "nchar": "char",
        "clob": "text", "nclob": "text", "blob": "bytea",
        "date": "timestamp", "timestamp": "timestamp",
        "timestamp with time zone": "timestamptz",
        "timestamp with local time zone": "timestamptz",
        "raw": "bytea", "long": "text", "long raw": "bytea",
        "xmltype": "xml", "rowid": "varchar(18)",
        "interval year to month": "interval", "interval day to second": "interval",
    }

    sql_to_snowflake: dict[str, str] = {
        "int": "NUMBER(38,0)", "bigint": "NUMBER(38,0)", "smallint": "NUMBER(38,0)",
        "tinyint": "NUMBER(38,0)", "bit": "BOOLEAN",
        "decimal": "NUMBER", "numeric": "NUMBER",
        "float": "FLOAT", "real": "FLOAT",
        "datetime": "TIMESTAMP_NTZ", "datetime2": "TIMESTAMP_NTZ",
        "date": "DATE", "time": "TIME",
        "datetimeoffset": "TIMESTAMP_TZ",
        "char": "VARCHAR", "varchar": "VARCHAR", "nvarchar": "VARCHAR",
        "text": "VARCHAR", "ntext": "VARCHAR",
        "binary": "BINARY", "varbinary": "BINARY",
        "uniqueidentifier": "VARCHAR(36)", "xml": "VARIANT",
    }

    sql_to_bigquery: dict[str, str] = {
        "int": "INT64", "bigint": "INT64", "smallint": "INT64",
        "tinyint": "INT64", "bit": "BOOL",
        "decimal": "NUMERIC", "numeric": "NUMERIC",
        "float": "FLOAT64", "real": "FLOAT64",
        "datetime": "DATETIME", "datetime2": "DATETIME",
        "date": "DATE", "time": "TIME",
        "datetimeoffset": "TIMESTAMP",
        "char": "STRING", "varchar": "STRING", "nvarchar": "STRING",
        "text": "STRING", "ntext": "STRING",
        "binary": "BYTES", "varbinary": "BYTES",
        "uniqueidentifier": "STRING", "xml": "STRING",
    }

    # Select appropriate mapping
    src = source_type.lower()
    tgt = target_type.lower()
    mapping_dict: dict[str, str] = sql_to_pg  # default

    if "mysql" in src and "pg" in tgt or "postgres" in tgt:
        mapping_dict = mysql_to_pg
    elif "oracle" in src and ("pg" in tgt or "postgres" in tgt):
        mapping_dict = oracle_to_pg
    elif "snowflake" in tgt:
        mapping_dict = sql_to_snowflake
    elif "bigquery" in tgt or "bq" in tgt:
        mapping_dict = sql_to_bigquery
    elif "mysql" in src:
        mapping_dict = mysql_to_pg
    elif "oracle" in src:
        mapping_dict = oracle_to_pg

    columns = json.loads(columns_json)
    mappings = []
    for col in columns:
        src_dt = col.get("data_type", "").lower()
        mapped_type = mapping_dict.get(src_dt, "text")
        max_len = col.get("character_maximum_length")
        if max_len and max_len > 0 and mapped_type in ("varchar", "char", "VARCHAR"):
            mapped_type = f"{mapped_type}({max_len})"
        mappings.append({
            "column_name": col.get("column_name"),
            "source_type": col.get("data_type"),
            "target_type": mapped_type,
        })
    return json.dumps(
        {"source": source_type, "target": target_type, "mappings": mappings}
    )


@mcp.tool()
async def validate_data_sample(
    source_json: str, target_json: str, key_columns: str
) -> str:
    """
    Compare source and target data samples (JSON arrays) by key columns.
    Returns mismatches found.
    """
    src = json.loads(source_json)
    tgt = json.loads(target_json)
    keys = [k.strip() for k in key_columns.split(",")]

    def make_key(row: dict[str, Any]) -> str:
        return "|".join(str(row.get(k, "")) for k in keys)

    src_map = {make_key(r): r for r in src}
    tgt_map = {make_key(r): r for r in tgt}

    missing_in_target = [k for k in src_map if k not in tgt_map]
    extra_in_target = [k for k in tgt_map if k not in src_map]
    mismatches = []
    for k in src_map:
        if k in tgt_map:
            for col in src_map[k]:
                if str(src_map[k][col]) != str(tgt_map[k].get(col, "")):
                    mismatches.append(
                        {"key": k, "column": col, "source": str(src_map[k][col]), "target": str(tgt_map[k].get(col, ""))}
                    )

    return json.dumps(
        {
            "source_count": len(src),
            "target_count": len(tgt),
            "missing_in_target": missing_in_target[:50],
            "extra_in_target": extra_in_target[:50],
            "value_mismatches": mismatches[:50],
        }
    )


# ══════════════════════════════════════════════════════════════════════
# ADF / Synapse Analytics / Fabric — Connection & Pipeline tools
# ══════════════════════════════════════════════════════════════════════

from linked_service_templates import (
    ADF_COPY_PIPELINE_TEMPLATE,
    ADF_DATASET_TEMPLATE,
    ADF_LINKED_SERVICE_TEMPLATES,
    FABRIC_CONNECTION_TEMPLATES,
    FABRIC_DATAFLOW_GEN2_TEMPLATE,
    SYNAPSE_LINKED_SERVICE_TEMPLATES,
    SYNAPSE_SPARK_POOL_NOTEBOOK_TEMPLATE,
    fill_template,
    get_supported_source_types,
    get_template,
)

# ── Lazy Azure SDK clients ────────────────────────────────────────────

_adf_client: Any = None
_synapse_client: Any = None


def _get_adf_client() -> Any:
    """Lazy-init Azure Data Factory management client (sync)."""
    global _adf_client
    if _adf_client is None:
        from azure.identity import DefaultAzureCredential as SyncCredential
        from azure.mgmt.datafactory import DataFactoryManagementClient

        sub_id = os.environ.get("AZURE_SUBSCRIPTION_ID", "")
        _adf_client = DataFactoryManagementClient(SyncCredential(), sub_id)
    return _adf_client


def _get_synapse_client() -> Any:
    """Lazy-init Synapse artifacts linked-service client (sync)."""
    global _synapse_client
    if _synapse_client is None:
        from azure.identity import DefaultAzureCredential as SyncCredential
        from azure.synapse.artifacts import ArtifactsClient

        endpoint = os.environ.get(
            "SYNAPSE_WORKSPACE_ENDPOINT",
            "https://placeholder.dev.azuresynapse.net",
        )
        _synapse_client = ArtifactsClient(SyncCredential(), endpoint)
    return _synapse_client


# ── Listing / discovery tools ─────────────────────────────────────────


@mcp.tool()
async def pipeline_list_supported_sources() -> str:
    """
    List all data-source types for which linked-service / connection
    templates are available, grouped by Azure service (ADF, Synapse, Fabric).
    """
    return json.dumps(
        {
            "adf": list(ADF_LINKED_SERVICE_TEMPLATES.keys()),
            "synapse": list(SYNAPSE_LINKED_SERVICE_TEMPLATES.keys()),
            "fabric": list(FABRIC_CONNECTION_TEMPLATES.keys()),
        }
    )


@mcp.tool()
async def pipeline_get_template(source_type: str, azure_service: str) -> str:
    """
    Return the raw linked-service / connection JSON template for a given
    source type and Azure service.  Placeholders are shown as {{TOKEN}}.

    Args:
        source_type: One of: sql_server, azure_sql, postgresql, mysql,
                     oracle, mongodb, cosmosdb, snowflake, adls_gen2,
                     azure_blob, databricks, bigquery
        azure_service: One of: adf, synapse, fabric
    """
    tpl = get_template(source_type, azure_service)
    if tpl is None:
        return json.dumps(
            {"error": f"No template for source_type={source_type!r}, azure_service={azure_service!r}"}
        )
    return json.dumps(tpl, indent=2)


# ── ADF tools ─────────────────────────────────────────────────────────


@mcp.tool()
async def adf_generate_linked_service(
    source_type: str, connection_params_json: str, connection_name: str = ""
) -> str:
    """
    Generate an ADF linked-service JSON definition for a given source type.
    Does NOT deploy — returns the JSON to be reviewed / deployed separately.

    Args:
        source_type: e.g. sql_server, postgresql, cosmosdb, snowflake …
        connection_params_json: JSON object with placeholder values, e.g.
            {"HOST":"myserver.database.windows.net","DATABASE":"mydb",
             "USERNAME":"admin","PASSWORD":"***"}
        connection_name: Optional friendly name.  Defaults to source_type + "_ls".
    """
    tpl = ADF_LINKED_SERVICE_TEMPLATES.get(source_type.lower())
    if tpl is None:
        return json.dumps({"error": f"Unknown source_type: {source_type}"})

    params: dict[str, str] = json.loads(connection_params_json)
    if not connection_name:
        connection_name = f"{source_type}_ls"
    params["CONNECTION_NAME"] = connection_name
    params.setdefault("IR_NAME", "AutoResolveIntegrationRuntime")

    return json.dumps(fill_template(tpl, params), indent=2)


@mcp.tool()
async def adf_generate_dataset(
    linked_service_name: str,
    dataset_type: str,
    schema_name: str,
    table_name: str,
    dataset_name: str = "",
) -> str:
    """
    Generate an ADF dataset JSON definition that references a linked service.

    Args:
        linked_service_name: The name of an existing linked service.
        dataset_type: ADF dataset type, e.g. SqlServerTable, AzureSqlTable,
                      AzurePostgreSqlTable, MongoDbV2Collection, CosmosDbSqlApiCollection,
                      SnowflakeTable, AzureBlobFSFile, ParquetDataset, etc.
        schema_name: Database schema (use "" for schemaless stores).
        table_name: Table / collection / file path.
        dataset_name: Optional friendly name.
    """
    if not dataset_name:
        dataset_name = f"ds_{table_name.replace('.', '_')}"
    params = {
        "DATASET_NAME": dataset_name,
        "DATASET_TYPE": dataset_type,
        "LINKED_SERVICE_NAME": linked_service_name,
        "SCHEMA": schema_name,
        "TABLE": table_name,
    }
    return json.dumps(fill_template(ADF_DATASET_TEMPLATE, params), indent=2)


@mcp.tool()
async def adf_generate_copy_pipeline(
    pipeline_name: str,
    source_dataset: str,
    target_dataset: str,
    source_table: str,
    target_table: str,
    source_type: str = "SqlServer",
    sink_type: str = "AzureSqlDatabase",
) -> str:
    """
    Generate an ADF copy-activity pipeline JSON that moves data from
    source dataset to target dataset.

    Args:
        pipeline_name: Friendly pipeline name.
        source_dataset: Name of source ADF dataset.
        target_dataset: Name of target ADF dataset.
        source_table: Source table name (for activity naming).
        target_table: Target table name (for activity naming).
        source_type: ADF source type (SqlServer, AzurePostgreSql, MongoDbV2 …).
        sink_type: ADF sink type (AzureSqlDatabase, AzureBlobFS …).
    """
    params = {
        "PIPELINE_NAME": pipeline_name,
        "SOURCE_DATASET": source_dataset,
        "TARGET_DATASET": target_dataset,
        "SOURCE_TABLE": source_table,
        "TARGET_TABLE": target_table,
        "SOURCE_TYPE": source_type,
        "SINK_TYPE": sink_type,
    }
    return json.dumps(fill_template(ADF_COPY_PIPELINE_TEMPLATE, params), indent=2)


@mcp.tool()
async def adf_deploy_linked_service(
    resource_group: str, factory_name: str, linked_service_json: str
) -> str:
    """
    Deploy a linked service to Azure Data Factory.

    Args:
        resource_group: Azure resource group containing the ADF instance.
        factory_name: Name of the Data Factory.
        linked_service_json: Full linked-service JSON (from adf_generate_linked_service).
    """
    try:
        client = _get_adf_client()
        ls_def = json.loads(linked_service_json)
        ls_name = ls_def.get("name", "unknown_ls")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: client.linked_services.create_or_update(
                resource_group, factory_name, ls_name, ls_def.get("properties", ls_def)
            ),
        )
        return json.dumps(
            {"status": "deployed", "name": ls_name, "factory": factory_name, "id": getattr(result, "id", "")}
        )
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@mcp.tool()
async def adf_deploy_pipeline(
    resource_group: str, factory_name: str, pipeline_json: str
) -> str:
    """
    Deploy a pipeline to Azure Data Factory.

    Args:
        resource_group: Azure resource group containing the ADF instance.
        factory_name: Name of the Data Factory.
        pipeline_json: Full pipeline JSON (from adf_generate_copy_pipeline).
    """
    try:
        client = _get_adf_client()
        pipe_def = json.loads(pipeline_json)
        pipe_name = pipe_def.get("name", "unknown_pipeline")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: client.pipelines.create_or_update(
                resource_group, factory_name, pipe_name, pipe_def.get("properties", pipe_def)
            ),
        )
        return json.dumps(
            {"status": "deployed", "name": pipe_name, "factory": factory_name, "id": getattr(result, "id", "")}
        )
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@mcp.tool()
async def adf_test_connection(
    resource_group: str, factory_name: str, linked_service_name: str
) -> str:
    """
    Verify an existing ADF linked-service connection by retrieving its metadata.

    Args:
        resource_group: Azure resource group.
        factory_name: Data Factory name.
        linked_service_name: Name of the linked service to test.
    """
    try:
        client = _get_adf_client()
        loop = asyncio.get_event_loop()
        ls = await loop.run_in_executor(
            None,
            lambda: client.linked_services.get(resource_group, factory_name, linked_service_name),
        )
        return json.dumps(
            {
                "status": "ok",
                "name": ls.name,
                "type": ls.properties.type if hasattr(ls, "properties") else "unknown",
                "provisioning_state": getattr(ls.properties, "provisioning_state", None),
            }
        )
    except Exception as exc:
        return json.dumps({"status": "error", "error": str(exc)})


# ── Synapse Analytics tools ───────────────────────────────────────────


@mcp.tool()
async def synapse_generate_linked_service(
    source_type: str, connection_params_json: str, connection_name: str = ""
) -> str:
    """
    Generate a Synapse Analytics linked-service JSON definition.

    Args:
        source_type: e.g. sql_server, postgresql, cosmosdb, snowflake …
        connection_params_json: JSON object with placeholder values.
        connection_name: Optional friendly name.
    """
    tpl = SYNAPSE_LINKED_SERVICE_TEMPLATES.get(source_type.lower())
    if tpl is None:
        return json.dumps({"error": f"Unknown source_type: {source_type}"})

    params: dict[str, str] = json.loads(connection_params_json)
    if not connection_name:
        connection_name = f"{source_type}_synapse_ls"
    params["CONNECTION_NAME"] = connection_name
    params.setdefault("IR_NAME", "AutoResolveIntegrationRuntime")

    return json.dumps(fill_template(tpl, params), indent=2)


@mcp.tool()
async def synapse_generate_notebook(
    notebook_name: str,
    source_format: str,
    source_url: str,
    source_table: str,
    target_format: str,
    target_url: str,
    target_table: str,
) -> str:
    """
    Generate a Synapse Spark notebook JSON for data migration.

    Args:
        notebook_name: Notebook display name.
        source_format: Spark read format (jdbc, parquet, csv, json, cosmos.oltp …).
        source_url: JDBC URL or storage path for source.
        source_table: Source table / path.
        target_format: Spark write format.
        target_url: JDBC URL or storage path for target.
        target_table: Target table / path.
    """
    params = {
        "NOTEBOOK_NAME": notebook_name,
        "SOURCE_FORMAT": source_format,
        "SOURCE_URL": source_url,
        "SOURCE_TABLE": source_table,
        "TARGET_FORMAT": target_format,
        "TARGET_URL": target_url,
        "TARGET_TABLE": target_table,
    }
    return json.dumps(fill_template(SYNAPSE_SPARK_POOL_NOTEBOOK_TEMPLATE, params), indent=2)


@mcp.tool()
async def synapse_deploy_linked_service(
    linked_service_json: str,
) -> str:
    """
    Deploy a linked service to Synapse Analytics workspace.
    Uses the SYNAPSE_WORKSPACE_ENDPOINT env var for targeting.

    Args:
        linked_service_json: Full linked-service JSON (from synapse_generate_linked_service).
    """
    try:
        client = _get_synapse_client()
        ls_def = json.loads(linked_service_json)
        ls_name = ls_def.get("name", "unknown_ls")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: client.linked_service.create_or_update_linked_service(
                ls_name, ls_def.get("properties", ls_def)
            ),
        )
        return json.dumps(
            {"status": "deployed", "name": ls_name, "id": getattr(result, "id", "")}
        )
    except Exception as exc:
        return json.dumps({"error": str(exc)})


# ── Fabric tools ──────────────────────────────────────────────────────


@mcp.tool()
async def fabric_generate_connection(
    source_type: str, connection_params_json: str, connection_name: str = ""
) -> str:
    """
    Generate a Microsoft Fabric connection JSON definition.

    Args:
        source_type: e.g. sql_server, postgresql, cosmosdb, snowflake …
        connection_params_json: JSON object with placeholder values.
        connection_name: Optional friendly name.
    """
    tpl = FABRIC_CONNECTION_TEMPLATES.get(source_type.lower())
    if tpl is None:
        return json.dumps({"error": f"Unknown source_type: {source_type}"})

    params: dict[str, str] = json.loads(connection_params_json)
    if not connection_name:
        connection_name = f"{source_type}_fabric_conn"
    params["CONNECTION_NAME"] = connection_name

    return json.dumps(fill_template(tpl, params), indent=2)


@mcp.tool()
async def fabric_generate_dataflow(
    dataflow_name: str,
    source_connector: str,
    source_params: str,
    schema_name: str,
    table_name: str,
    lakehouse_id: str,
    target_table: str,
    query_name: str = "",
) -> str:
    """
    Generate a Fabric Dataflow Gen2 definition for migrating a single table.

    Args:
        dataflow_name: Display name for the dataflow.
        source_connector: Power Query M connector function, e.g.
            Sql.Database, PostgreSQL.Database, Oracle.Database,
            MongoDB.Database, Snowflake.Databases, GoogleBigQuery.Database
        source_params: Connector-specific M parameters, e.g.
            '"myserver.database.windows.net", "mydb"'
        schema_name: Source schema/namespace.
        table_name: Source table/collection name.
        lakehouse_id: Target Fabric Lakehouse GUID.
        target_table: Target table name in Lakehouse.
        query_name: Optional query name (defaults to table_name).
    """
    if not query_name:
        query_name = table_name.replace(" ", "_").replace(".", "_")
    params = {
        "DATAFLOW_NAME": dataflow_name,
        "QUERY_NAME": query_name,
        "SOURCE_CONNECTOR": source_connector,
        "SOURCE_PARAMS": source_params,
        "SCHEMA": schema_name,
        "TABLE": table_name,
        "LAKEHOUSE_ID": lakehouse_id,
        "TARGET_TABLE": target_table,
    }
    return json.dumps(fill_template(FABRIC_DATAFLOW_GEN2_TEMPLATE, params), indent=2)


# ══════════════════════════════════════════════════════════════════════
# Azure Resource Management tools — provision real Azure resources
# ══════════════════════════════════════════════════════════════════════

_resource_client: Any = None
_storage_mgmt_client: Any = None
_keyvault_mgmt_client: Any = None
_policy_client: Any = None


def _get_azure_subscription_id() -> str:
    """Return the configured Azure subscription ID."""
    sub_id = os.environ.get("AZURE_SUBSCRIPTION_ID", "")
    if not sub_id:
        raise ValueError("AZURE_SUBSCRIPTION_ID is not set")
    return sub_id


def _get_resource_client():
    """Lazy-init Azure Resource Management client (sync)."""
    global _resource_client
    if _resource_client is None:
        from azure.identity import DefaultAzureCredential as SyncCredential
        from azure.mgmt.resource import ResourceManagementClient

        _resource_client = ResourceManagementClient(
            SyncCredential(), _get_azure_subscription_id()
        )
    return _resource_client


def _get_storage_mgmt_client():
    """Lazy-init Azure Storage Management client (sync)."""
    global _storage_mgmt_client
    if _storage_mgmt_client is None:
        from azure.identity import DefaultAzureCredential as SyncCredential
        from azure.mgmt.storage import StorageManagementClient

        _storage_mgmt_client = StorageManagementClient(
            SyncCredential(), _get_azure_subscription_id()
        )
    return _storage_mgmt_client


def _get_keyvault_mgmt_client():
    """Lazy-init Azure Key Vault Management client (sync)."""
    global _keyvault_mgmt_client
    if _keyvault_mgmt_client is None:
        from azure.identity import DefaultAzureCredential as SyncCredential
        from azure.mgmt.keyvault import KeyVaultManagementClient

        _keyvault_mgmt_client = KeyVaultManagementClient(
            SyncCredential(), _get_azure_subscription_id()
        )
    return _keyvault_mgmt_client


def _get_policy_client():
    """Lazy-init Azure Policy Insights client (sync)."""
    global _policy_client
    if _policy_client is None:
        from azure.identity import DefaultAzureCredential as SyncCredential
        from azure.mgmt.policyinsights import PolicyInsightsClient

        _policy_client = PolicyInsightsClient(
            SyncCredential(), _get_azure_subscription_id()
        )
    return _policy_client


# ── Azure Paired Region Mapping & Fallback Helper ─────────────────────

# Official Azure paired regions (bidirectional).
# See: https://learn.microsoft.com/en-us/azure/reliability/cross-region-replication-azure
_AZURE_PAIRED_REGIONS: dict[str, str] = {
    "eastus": "westus",
    "westus": "eastus",
    "eastus2": "centralus",
    "centralus": "eastus2",
    "westus2": "westcentralus",
    "westcentralus": "westus2",
    "westus3": "eastus",
    "northcentralus": "southcentralus",
    "southcentralus": "northcentralus",
    "canadacentral": "canadaeast",
    "canadaeast": "canadacentral",
    "brazilsouth": "southcentralus",
    "northeurope": "westeurope",
    "westeurope": "northeurope",
    "uksouth": "ukwest",
    "ukwest": "uksouth",
    "francecentral": "francesouth",
    "francesouth": "francecentral",
    "germanywestcentral": "germanynorth",
    "germanynorth": "germanywestcentral",
    "switzerlandnorth": "switzerlandwest",
    "switzerlandwest": "switzerlandnorth",
    "norwayeast": "norwaywest",
    "norwaywest": "norwayeast",
    "swedencentral": "swedensouth",
    "swedensouth": "swedencentral",
    "australiaeast": "australiasoutheast",
    "australiasoutheast": "australiaeast",
    "australiacentral": "australiacentral2",
    "australiacentral2": "australiacentral",
    "eastasia": "southeastasia",
    "southeastasia": "eastasia",
    "japaneast": "japanwest",
    "japanwest": "japaneast",
    "koreacentral": "koreasouth",
    "koreasouth": "koreacentral",
    "centralindia": "southindia",
    "southindia": "centralindia",
    "westindia": "southindia",
    "uaenorth": "uaecentral",
    "uaecentral": "uaenorth",
    "southafricanorth": "southafricawest",
    "southafricawest": "southafricanorth",
    "qatarcentral": "uaenorth",
}


def _get_paired_region(location: str) -> str | None:
    """Return the Azure paired region for a given location, or None."""
    return _AZURE_PAIRED_REGIONS.get(location.lower().replace(" ", ""))


def _provision_with_region_fallback(
    create_fn,
    location: str,
    resource_label: str,
) -> dict:
    """Run *create_fn(location)* and, on failure, retry in the paired region.

    Both SDK exceptions and returned-error dicts are handled: if create_fn
    raises an exception OR returns a dict whose ``status`` is not a success
    value, the paired region is attempted.

    Args:
        create_fn: A callable(location) -> dict that provisions a resource.
                   Must return a dict with a "status" key ("success"/"created"/
                   "created_or_updated" for success, anything else for failure).
        location: Primary Azure region.
        resource_label: Human-readable label for log messages.

    Returns:
        The result dict from whichever attempt succeeded, or a failure dict
        augmented with ``primary_region``, ``fallback_region``, and
        ``primary_error`` keys.
    """
    import logging
    _log = logging.getLogger("mcp_server.region_fallback")

    _success_values = {"success", "created", "created_or_updated", "Succeeded"}

    # ── helper: call create_fn safely ────────────────────────────────
    def _safe_call(loc: str):
        """Return (result_dict, error_string | None)."""
        try:
            result = create_fn(loc)
            if result.get("status") in _success_values:
                return result, None
            return result, result.get("error", "Unknown error")
        except Exception as exc:
            _log.exception(
                "Region fallback: %s raised in %s", resource_label, loc,
            )
            return {"status": "failed", "error": str(exc)}, str(exc)

    # ── Primary attempt ──────────────────────────────────────────────
    result, primary_error = _safe_call(location)
    if primary_error is None:
        return result

    _log.warning(
        "Region fallback: %s failed in %s — %s",
        resource_label, location, primary_error,
    )

    # ── Paired-region attempt ────────────────────────────────────────
    paired = _get_paired_region(location)
    if not paired:
        _log.warning(
            "No paired region found for %s — cannot retry", location,
        )
        result["fallback_attempted"] = False
        result["note"] = f"No paired region for '{location}'"
        return result

    _log.info(
        "Region fallback: retrying %s in paired region %s",
        resource_label, paired,
    )
    fallback_result, fallback_error = _safe_call(paired)
    if fallback_error is None:
        fallback_result["fallback_used"] = True
        fallback_result["primary_region"] = location
        fallback_result["primary_error"] = primary_error
        fallback_result["fallback_region"] = paired
        _log.info(
            "Region fallback: %s succeeded in %s", resource_label, paired,
        )
        return fallback_result

    # Both failed
    _log.error(
        "Region fallback: %s also failed in %s — %s",
        resource_label, paired, fallback_error,
    )
    fallback_result["fallback_used"] = True
    fallback_result["primary_region"] = location
    fallback_result["primary_error"] = primary_error
    fallback_result["fallback_region"] = paired
    return fallback_result


# ── Resource Group tools ──────────────────────────────────────────────


@mcp.tool()
async def azure_list_resource_groups() -> str:
    """List all resource groups in the Azure subscription."""
    loop = asyncio.get_running_loop()

    def _query():
        client = _get_resource_client()
        groups = list(client.resource_groups.list())
        return [
            {
                "name": rg.name,
                "location": rg.location,
                "provisioning_state": rg.properties.provisioning_state if rg.properties else None,
                "tags": dict(rg.tags) if rg.tags else {},
            }
            for rg in groups
        ]

    result = await loop.run_in_executor(None, _query)
    return json.dumps(result, default=str)


@mcp.tool()
async def azure_create_resource_group(
    name: str, location: str, tags_json: str = "{}"
) -> str:
    """
    Create or update an Azure resource group.

    Args:
        name: Resource group name (e.g. 'rg-migration-dev').
        location: Azure region (e.g. 'eastus', 'westeurope').
        tags_json: Optional JSON object of tags, e.g. '{"project":"migration"}'.
    """
    loop = asyncio.get_running_loop()
    tags = json.loads(tags_json) if tags_json else {}

    def _create_in_region(loc: str):
        client = _get_resource_client()
        result = client.resource_groups.create_or_update(
            name, {"location": loc, "tags": tags}
        )
        return {
            "name": result.name,
            "location": result.location,
            "provisioning_state": result.properties.provisioning_state if result.properties else None,
            "status": "created_or_updated",
        }

    def _with_fallback():
        return _provision_with_region_fallback(
            _create_in_region, location, f"Resource Group {name}",
        )

    result = await loop.run_in_executor(None, _with_fallback)
    return json.dumps(result, default=str)


@mcp.tool()
async def azure_check_resource_group_exists(name: str) -> str:
    """Check if a resource group exists in the subscription."""
    loop = asyncio.get_running_loop()

    def _check():
        client = _get_resource_client()
        exists = client.resource_groups.check_existence(name)
        return {"name": name, "exists": exists}

    result = await loop.run_in_executor(None, _check)
    return json.dumps(result, default=str)


# ── Resource listing tools ────────────────────────────────────────────


@mcp.tool()
async def azure_list_resources(
    resource_group: str = "", resource_type: str = ""
) -> str:
    """
    List Azure resources. Optionally filter by resource group and/or resource type.

    Args:
        resource_group: Optional resource group name to scope the query.
        resource_type: Optional resource type filter (e.g. 'Microsoft.Sql/servers',
                       'Microsoft.Storage/storageAccounts',
                       'Microsoft.DataFactory/factories').
    """
    loop = asyncio.get_running_loop()

    def _query():
        client = _get_resource_client()
        filter_expr = f"resourceType eq '{resource_type}'" if resource_type else None

        if resource_group:
            resources = list(
                client.resources.list_by_resource_group(
                    resource_group, filter=filter_expr
                )
            )
        else:
            resources = list(client.resources.list(filter=filter_expr))

        return [
            {
                "name": r.name,
                "type": r.type,
                "location": r.location,
                "resource_group": r.id.split("/")[4] if r.id and len(r.id.split("/")) > 4 else "",
                "provisioning_state": getattr(r, "provisioning_state", None),
                "tags": dict(r.tags) if r.tags else {},
            }
            for r in resources[:200]  # cap at 200 to avoid huge payloads
        ]

    result = await loop.run_in_executor(None, _query)
    return json.dumps(result, default=str)


@mcp.tool()
async def azure_get_resource(
    resource_group: str,
    provider_namespace: str,
    resource_type: str,
    resource_name: str,
    api_version: str = "2023-07-01",
) -> str:
    """
    Get details of a specific Azure resource by its path components.

    Args:
        resource_group: Resource group name.
        provider_namespace: e.g. 'Microsoft.Sql', 'Microsoft.Storage'.
        resource_type: e.g. 'servers', 'storageAccounts'.
        resource_name: Name of the resource.
        api_version: ARM API version (default '2023-07-01').
    """
    loop = asyncio.get_running_loop()

    def _query():
        client = _get_resource_client()
        resource = client.resources.get(
            resource_group,
            provider_namespace,
            "",  # parent resource path
            resource_type,
            resource_name,
            api_version,
        )
        return {
            "name": resource.name,
            "type": resource.type,
            "location": resource.location,
            "properties": resource.properties if hasattr(resource, "properties") else {},
            "tags": dict(resource.tags) if resource.tags else {},
        }

    result = await loop.run_in_executor(None, _query)
    return json.dumps(result, default=str)


@mcp.tool()
async def azure_check_resource_exists(
    resource_group: str,
    provider_namespace: str,
    resource_type: str,
    resource_name: str,
    api_version: str = "2023-07-01",
) -> str:
    """
    Check if a specific Azure resource exists.

    Args:
        resource_group: Resource group name.
        provider_namespace: e.g. 'Microsoft.Sql', 'Microsoft.Storage'.
        resource_type: e.g. 'servers', 'storageAccounts'.
        resource_name: Name of the resource.
        api_version: ARM API version.
    """
    loop = asyncio.get_running_loop()

    def _check():
        client = _get_resource_client()
        exists = client.resources.check_existence(
            resource_group,
            provider_namespace,
            "",  # parent resource path
            resource_type,
            resource_name,
            api_version,
        )
        return {"resource_name": resource_name, "resource_type": f"{provider_namespace}/{resource_type}", "exists": exists}

    result = await loop.run_in_executor(None, _check)
    return json.dumps(result, default=str)


# ── Storage Account tools ─────────────────────────────────────────────


@mcp.tool()
async def azure_create_storage_account(
    resource_group: str,
    account_name: str,
    location: str,
    sku: str = "Standard_LRS",
    kind: str = "StorageV2",
    enable_hns: bool = False,
    tags_json: str = "{}",
) -> str:
    """
    Create an Azure Storage account (also supports ADLS Gen2 via enable_hns).

    Args:
        resource_group: Resource group name.
        account_name: Storage account name (3-24 chars, lowercase alphanumeric).
        location: Azure region (e.g. 'eastus').
        sku: SKU name — Standard_LRS, Standard_GRS, Standard_RAGRS, Premium_LRS, etc.
        kind: Account kind — StorageV2 (recommended), BlobStorage, BlockBlobStorage.
        enable_hns: Set True for ADLS Gen2 (hierarchical namespace).
        tags_json: Optional JSON tags.
    """
    loop = asyncio.get_running_loop()
    tags = json.loads(tags_json) if tags_json else {}

    def _create_in_region(loc: str):
        client = _get_storage_mgmt_client()
        params = {
            "sku": {"name": sku},
            "kind": kind,
            "location": loc,
            "tags": tags,
            "is_hns_enabled": enable_hns,
        }
        poller = client.storage_accounts.begin_create(
            resource_group, account_name, params
        )
        result = poller.result()
        ep = result.primary_endpoints
        return {
            "status": "created",
            "name": result.name,
            "location": result.location,
            "sku": result.sku.name if result.sku else sku,
            "kind": getattr(result, "kind", kind),
            "hns_enabled": getattr(result, "is_hns_enabled", enable_hns),
            "primary_endpoints": {
                "blob": getattr(ep, "blob", None),
                "dfs": getattr(ep, "dfs", None),
            } if ep else None,
        }

    def _with_fallback():
        return _provision_with_region_fallback(
            _create_in_region, location, f"storage account '{account_name}'"
        )

    result = await loop.run_in_executor(None, _with_fallback)
    return json.dumps(result, default=str)


@mcp.tool()
async def azure_list_storage_accounts(resource_group: str = "") -> str:
    """
    List Azure Storage accounts, optionally scoped to a resource group.

    Args:
        resource_group: Optional resource group name. If empty, lists all in subscription.
    """
    loop = asyncio.get_running_loop()

    def _query():
        client = _get_storage_mgmt_client()
        if resource_group:
            accounts = list(client.storage_accounts.list_by_resource_group(resource_group))
        else:
            accounts = list(client.storage_accounts.list())
        return [
            {
                "name": a.name,
                "location": a.location,
                "sku": a.sku.name if a.sku else None,
                "kind": a.kind,
                "hns_enabled": a.is_hns_enabled,
                "provisioning_state": a.provisioning_state,
                "primary_endpoints": {
                    "blob": a.primary_endpoints.blob if a.primary_endpoints else None,
                    "dfs": a.primary_endpoints.dfs if a.primary_endpoints else None,
                },
            }
            for a in accounts
        ]

    result = await loop.run_in_executor(None, _query)
    return json.dumps(result, default=str)


@mcp.tool()
async def azure_get_storage_account_keys(
    resource_group: str, account_name: str
) -> str:
    """
    Retrieve access keys for an Azure Storage account.

    Args:
        resource_group: Resource group name.
        account_name: Storage account name.
    """
    loop = asyncio.get_running_loop()

    def _query():
        client = _get_storage_mgmt_client()
        keys = client.storage_accounts.list_keys(resource_group, account_name)
        return [
            {"key_name": k.key_name, "value": k.value[:8] + "...", "permissions": k.permissions}
            for k in keys.keys
        ]

    result = await loop.run_in_executor(None, _query)
    return json.dumps(result, default=str)


# ── SQL Server / Database tools ───────────────────────────────────────


@mcp.tool()
async def azure_create_sql_server(
    resource_group: str,
    server_name: str,
    location: str,
    admin_login: str,
    admin_password: str,
    tags_json: str = "{}",
) -> str:
    """
    Create an Azure SQL Server (logical server).

    Args:
        resource_group: Resource group name.
        server_name: SQL server name (globally unique, lowercase).
        location: Azure region (e.g. 'eastus').
        admin_login: Administrator login name.
        admin_password: Administrator password.
        tags_json: Optional JSON tags.
    """
    loop = asyncio.get_running_loop()
    tags = json.loads(tags_json) if tags_json else {}

    def _create_in_region(loc: str):
        from azure.identity import DefaultAzureCredential as SyncCredential
        from azure.mgmt.sql import SqlManagementClient
        from azure.mgmt.sql.models import Server

        client = SqlManagementClient(SyncCredential(), _get_azure_subscription_id())
        server_params = Server(
            location=loc,
            administrator_login=admin_login,
            administrator_login_password=admin_password,
            version="12.0",
            minimal_tls_version="1.2",
            public_network_access="Enabled",
            tags=tags,
        )
        poller = client.servers.begin_create_or_update(
            resource_group,
            server_name,
            server_params,
        )
        result = poller.result()
        return {
            "status": "created",
            "name": result.name,
            "fqdn": getattr(result, "fully_qualified_domain_name", None),
            "location": result.location,
            "state": getattr(result, "state", None),
            "version": getattr(result, "version", None),
            "minimal_tls_version": getattr(result, "minimal_tls_version", None),
        }

    def _with_fallback():
        return _provision_with_region_fallback(
            _create_in_region, location, f"SQL Server {server_name}",
        )

    result = await loop.run_in_executor(None, _with_fallback)
    return json.dumps(result, default=str)


@mcp.tool()
async def azure_create_sql_database(
    resource_group: str,
    server_name: str,
    database_name: str,
    sku_name: str = "Basic",
    max_size_gb: int = 2,
    tags_json: str = "{}",
) -> str:
    """
    Create an Azure SQL Database on an existing logical server.

    Args:
        resource_group: Resource group name.
        server_name: Azure SQL Server name.
        database_name: Database name.
        sku_name: SKU — Basic, S0, S1, S2, S3, P1, P2, GP_Gen5_2, BC_Gen5_2, etc.
        max_size_gb: Maximum database size in GB.
        tags_json: Optional JSON tags.
    """
    loop = asyncio.get_running_loop()
    tags = json.loads(tags_json) if tags_json else {}

    def _create():
        from azure.identity import DefaultAzureCredential as SyncCredential
        from azure.mgmt.sql import SqlManagementClient

        client = SqlManagementClient(SyncCredential(), _get_azure_subscription_id())
        poller = client.databases.begin_create_or_update(
            resource_group,
            server_name,
            database_name,
            {
                "location": client.servers.get(resource_group, server_name).location,
                "sku": {"name": sku_name},
                "properties": {
                    "max_size_bytes": max_size_gb * 1024 * 1024 * 1024,
                },
                "tags": tags,
            },
        )
        result = poller.result()
        return {
            "status": "created",
            "name": result.name,
            "server": server_name,
            "sku": result.sku.name if result.sku else sku_name,
            "max_size_bytes": result.max_size_bytes,
            "state": result.status,
        }

    result = await loop.run_in_executor(None, _create)
    return json.dumps(result, default=str)


@mcp.tool()
async def azure_list_sql_servers(resource_group: str = "") -> str:
    """
    List Azure SQL Servers, optionally scoped to a resource group.

    Args:
        resource_group: Optional resource group name.
    """
    loop = asyncio.get_running_loop()

    def _query():
        from azure.identity import DefaultAzureCredential as SyncCredential
        from azure.mgmt.sql import SqlManagementClient

        client = SqlManagementClient(SyncCredential(), _get_azure_subscription_id())
        if resource_group:
            servers = list(client.servers.list_by_resource_group(resource_group))
        else:
            servers = list(client.servers.list())
        return [
            {
                "name": s.name,
                "fqdn": s.fully_qualified_domain_name,
                "location": s.location,
                "state": s.state,
                "admin_login": s.administrator_login,
            }
            for s in servers
        ]

    result = await loop.run_in_executor(None, _query)
    return json.dumps(result, default=str)


@mcp.tool()
async def azure_list_sql_databases(resource_group: str, server_name: str) -> str:
    """
    List all databases on an Azure SQL Server.

    Args:
        resource_group: Resource group name.
        server_name: Azure SQL Server name.
    """
    loop = asyncio.get_running_loop()

    def _query():
        from azure.identity import DefaultAzureCredential as SyncCredential
        from azure.mgmt.sql import SqlManagementClient

        client = SqlManagementClient(SyncCredential(), _get_azure_subscription_id())
        databases = list(client.databases.list_by_server(resource_group, server_name))
        return [
            {
                "name": db.name,
                "status": db.status,
                "sku": db.sku.name if db.sku else None,
                "max_size_bytes": db.max_size_bytes,
                "creation_date": str(db.creation_date) if db.creation_date else None,
            }
            for db in databases
        ]

    result = await loop.run_in_executor(None, _query)
    return json.dumps(result, default=str)


# ── Azure Data Factory provisioning tools ─────────────────────────────


@mcp.tool()
async def azure_create_data_factory(
    resource_group: str,
    factory_name: str,
    location: str,
    tags_json: str = "{}",
) -> str:
    """
    Create an Azure Data Factory instance.

    Args:
        resource_group: Resource group name.
        factory_name: Data Factory name (globally unique).
        location: Azure region (e.g. 'eastus').
        tags_json: Optional JSON tags.
    """
    loop = asyncio.get_running_loop()
    tags = json.loads(tags_json) if tags_json else {}

    def _create_in_region(loc: str):
        client_obj = _get_adf_client()
        try:
            result = client_obj.factories.create_or_update(
                resource_group,
                factory_name,
                {
                    "location": loc,
                    "tags": tags,
                    "identity": {"type": "SystemAssigned"},
                },
            )
            return {
                "status": "created",
                "name": result.name,
                "location": result.location,
                "provisioning_state": result.provisioning_state,
                "id": result.id,
            }
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
                "factory_name": factory_name,
            }

    def _with_fallback():
        return _provision_with_region_fallback(
            _create_in_region, location, f"Data Factory {factory_name}",
        )

    result = await loop.run_in_executor(None, _with_fallback)
    return json.dumps(result, default=str)


@mcp.tool()
async def azure_list_data_factories(resource_group: str = "") -> str:
    """
    List Azure Data Factory instances, optionally scoped to a resource group.

    Args:
        resource_group: Optional resource group name.
    """
    loop = asyncio.get_running_loop()

    def _query():
        client_obj = _get_adf_client()
        try:
            if resource_group:
                factories = list(client_obj.factories.list_by_resource_group(resource_group))
            else:
                factories = list(client_obj.factories.list())
            return [
                {
                    "name": f.name,
                    "location": f.location,
                    "provisioning_state": f.provisioning_state,
                    "id": f.id,
                }
                for f in factories
            ]
        except Exception as e:
            return {"status": "error", "error": str(e)}

    result = await loop.run_in_executor(None, _query)
    return json.dumps(result, default=str)


# ── SQL Server firewall rules ─────────────────────────────────────────


@mcp.tool()
async def azure_create_sql_firewall_rule(
    resource_group: str,
    server_name: str,
    rule_name: str,
    start_ip: str,
    end_ip: str,
) -> str:
    """
    Create a firewall rule on an Azure SQL Server.

    Args:
        resource_group: Resource group name.
        server_name: Azure SQL Server name.
        rule_name: Firewall rule name.
        start_ip: Start IP address (use '0.0.0.0' for Azure services).
        end_ip: End IP address (use '0.0.0.0' for Azure services).
    """
    loop = asyncio.get_running_loop()

    def _create():
        from azure.identity import DefaultAzureCredential as SyncCredential
        from azure.mgmt.sql import SqlManagementClient

        client = SqlManagementClient(SyncCredential(), _get_azure_subscription_id())
        result = client.firewall_rules.create_or_update(
            resource_group,
            server_name,
            rule_name,
            {"start_ip_address": start_ip, "end_ip_address": end_ip},
        )
        return {
            "status": "created",
            "name": result.name,
            "start_ip": result.start_ip_address,
            "end_ip": result.end_ip_address,
        }

    result = await loop.run_in_executor(None, _create)
    return json.dumps(result, default=str)


# ── Generic ARM deployment tool ───────────────────────────────────────


@mcp.tool()
async def azure_deploy_arm_template(
    resource_group: str,
    deployment_name: str,
    template_json: str,
    parameters_json: str = "{}",
) -> str:
    """
    Deploy an ARM template to a resource group (for advanced provisioning).

    Args:
        resource_group: Target resource group.
        deployment_name: Unique deployment name.
        template_json: Full ARM template as JSON string.
        parameters_json: ARM template parameters as JSON string.
    """
    loop = asyncio.get_running_loop()

    def _deploy():
        client = _get_resource_client()
        template = json.loads(template_json)
        parameters = json.loads(parameters_json) if parameters_json else {}

        # Wrap parameter values if not already wrapped
        wrapped_params = {}
        for k, v in parameters.items():
            if isinstance(v, dict) and "value" in v:
                wrapped_params[k] = v
            else:
                wrapped_params[k] = {"value": v}

        deployment_properties = {
            "mode": "Incremental",
            "template": template,
            "parameters": wrapped_params,
        }
        poller = client.deployments.begin_create_or_update(
            resource_group,
            deployment_name,
            {"properties": deployment_properties},
        )
        result = poller.result()
        return {
            "status": "succeeded" if result.properties and result.properties.provisioning_state == "Succeeded" else "completed",
            "deployment_name": deployment_name,
            "provisioning_state": result.properties.provisioning_state if result.properties else None,
            "outputs": result.properties.outputs if result.properties else None,
        }

    result = await loop.run_in_executor(None, _deploy)
    return json.dumps(result, default=str)


# ── Infrastructure Provisioning Tools ────────────────────────────────


@mcp.tool()
async def azure_provision_storage_account(
    resource_group: str,
    account_name: str,
    location: str,
    sku: str = "Standard_LRS",
    kind: str = "StorageV2",
    access_tier: str = "Hot",
    minimum_tls_version: str = "TLS1_2",
    supports_https_only: bool = True,
    allow_blob_public_access: bool = False,
    allow_shared_key_access: bool = True,
    is_hns_enabled: bool = True,
    tags_json: str = "{}",
) -> str:
    """
    Provision an Azure Storage Account with security and compliance settings.

    Args:
        resource_group: Resource group name.
        account_name: Storage account name (3-24 lowercase alphanumeric, globally unique).
        location: Azure region (e.g. 'eastus2').
        sku: Storage SKU (Standard_LRS, Standard_ZRS, Premium_LRS, etc.).
        kind: Storage kind (StorageV2, BlobStorage, etc.).
        access_tier: Access tier (Hot, Cool).
        minimum_tls_version: Minimum TLS version (TLS1_0, TLS1_1, TLS1_2).
        supports_https_only: Require HTTPS traffic only.
        allow_blob_public_access: Allow public blob access.
        allow_shared_key_access: Allow shared key access.
        is_hns_enabled: Enable hierarchical namespace (ADLS Gen2).
        tags_json: Optional JSON tags.
    """
    loop = asyncio.get_running_loop()
    tags = json.loads(tags_json) if tags_json else {}

    def _create_in_region(loc: str):
        from azure.identity import DefaultAzureCredential as SyncCredential
        from azure.mgmt.storage import StorageManagementClient
        from azure.mgmt.storage.models import (
            StorageAccountCreateParameters,
            Sku as StorageSku,
            Encryption,
            EncryptionServices,
            EncryptionService,
        )

        client = StorageManagementClient(SyncCredential(), _get_azure_subscription_id())

        params = StorageAccountCreateParameters(
            sku=StorageSku(name=sku),
            kind=kind,
            location=loc,
            tags=tags,
            access_tier=access_tier,
            enable_https_traffic_only=supports_https_only,
            minimum_tls_version=minimum_tls_version,
            allow_blob_public_access=allow_blob_public_access,
            allow_shared_key_access=allow_shared_key_access,
            is_hns_enabled=is_hns_enabled,
            encryption=Encryption(
                services=EncryptionServices(
                    blob=EncryptionService(enabled=True, key_type="Account"),
                    file=EncryptionService(enabled=True, key_type="Account"),
                    queue=EncryptionService(enabled=True, key_type="Account"),
                    table=EncryptionService(enabled=True, key_type="Account"),
                ),
                key_source="Microsoft.Storage",
            ),
        )

        try:
            result = client.storage_accounts.begin_create(
                resource_group, account_name, params
            ).result()

            if getattr(result, "provisioning_state", None) == "Succeeded":
                ep = result.primary_endpoints
                return {
                    "status": "success",
                    "account_name": result.name,
                    "location": result.location,
                    "sku": result.sku.name if result.sku else sku,
                    "kind": getattr(result, "kind", kind),
                    "minimum_tls_version": getattr(result, "minimum_tls_version", minimum_tls_version),
                    "supports_https_only": getattr(result, "enable_https_traffic_only", supports_https_only),
                    "primary_endpoints": {
                        "blob": getattr(ep, "blob", None),
                        "dfs": getattr(ep, "dfs", None),
                        "queue": getattr(ep, "queue", None),
                        "table": getattr(ep, "table", None),
                    } if ep else None,
                    "provisioning_state": result.provisioning_state,
                }
            else:
                return {
                    "status": "failed",
                    "error": f"Provisioning failed with state: {result.provisioning_state}",
                    "account_name": account_name,
                }

        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
                "account_name": account_name,
            }

    def _with_fallback():
        return _provision_with_region_fallback(
            _create_in_region, location,
            f"Storage Account {account_name}",
        )

    result = await loop.run_in_executor(None, _with_fallback)
    return json.dumps(result, default=str)


@mcp.tool()
async def azure_provision_data_factory(
    resource_group: str,
    factory_name: str,
    location: str,
    tags_json: str = "{}",
) -> str:
    """
    Provision an Azure Data Factory instance.

    Args:
        resource_group: Resource group name.
        factory_name: Data Factory name (globally unique).
        location: Azure region (e.g. 'eastus2').
        tags_json: Optional JSON tags.
    """
    loop = asyncio.get_running_loop()
    tags = json.loads(tags_json) if tags_json else {}

    def _create_in_region(loc: str):
        client = _get_adf_client()

        properties = {
            "location": loc,
            "tags": tags,
            "identity": {"type": "SystemAssigned"},
        }

        try:
            result = client.factories.create_or_update(
                resource_group, factory_name, properties
            )

            return {
                "status": "success",
                "factory_name": result.name,
                "location": result.location,
                "provisioning_state": result.provisioning_state,
                "id": result.id,
            }

        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
                "factory_name": factory_name,
            }

    def _with_fallback():
        return _provision_with_region_fallback(
            _create_in_region, location,
            f"Data Factory {factory_name}",
        )

    result = await loop.run_in_executor(None, _with_fallback)
    return json.dumps(result, default=str)


@mcp.tool()
async def azure_provision_key_vault(
    resource_group: str,
    vault_name: str,
    location: str,
    sku: str = "standard",
    enabled_for_deployment: bool = True,
    enabled_for_template_deployment: bool = True,
    enabled_for_disk_encryption: bool = True,
    soft_delete_retention_days: int = 90,
    tags_json: str = "{}",
) -> str:
    """
    Provision an Azure Key Vault.

    Args:
        resource_group: Resource group name.
        vault_name: Key Vault name (globally unique).
        location: Azure region (e.g. 'eastus2').
        sku: Key Vault SKU (standard, premium).
        enabled_for_deployment: Enable for VM deployment.
        enabled_for_template_deployment: Enable for ARM template deployment.
        enabled_for_disk_encryption: Enable for disk encryption.
        soft_delete_retention_days: Soft delete retention in days.
        tags_json: Optional JSON tags.
    """
    loop = asyncio.get_running_loop()
    tags = json.loads(tags_json) if tags_json else {}

    def _create_in_region(loc: str):
        client = _get_keyvault_mgmt_client()

        # Get tenant ID from environment variable (set by docker-compose)
        tenant_id = os.environ.get("AZURE_TENANT_ID", "")
        if not tenant_id:
            return {
                "status": "failed",
                "error": "AZURE_TENANT_ID environment variable is not set",
                "vault_name": vault_name,
            }

        from azure.mgmt.keyvault.models import (
            VaultCreateOrUpdateParameters,
            VaultProperties,
            Sku,
            SkuName,
            SkuFamily,
        )

        sku_name = SkuName.STANDARD if sku.lower() == "standard" else SkuName.PREMIUM

        params = VaultCreateOrUpdateParameters(
            location=loc,
            tags=tags,
            properties=VaultProperties(
                tenant_id=tenant_id,
                sku=Sku(family=SkuFamily.A, name=sku_name),
                enabled_for_deployment=enabled_for_deployment,
                enabled_for_template_deployment=enabled_for_template_deployment,
                enabled_for_disk_encryption=enabled_for_disk_encryption,
                soft_delete_retention_in_days=soft_delete_retention_days,
                enable_rbac_authorization=True,
                enable_soft_delete=True,
                enable_purge_protection=True,
                access_policies=[],
            ),
        )

        try:
            poller = client.vaults.begin_create_or_update(
                resource_group, vault_name, params
            )
            result = poller.result()

            return {
                "status": "success",
                "vault_name": result.name,
                "location": result.location,
                "vault_uri": result.properties.vault_uri,
                "provisioning_state": result.properties.provisioning_state,
            }

        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
                "vault_name": vault_name,
            }

    def _with_fallback():
        return _provision_with_region_fallback(
            _create_in_region, location, f"Key Vault {vault_name}",
        )

    result = await loop.run_in_executor(None, _with_fallback)
    return json.dumps(result, default=str)


@mcp.tool()
async def azure_check_policy_compliance(
    resource_group: str,
    resource_type: str,
    resource_name: str,
) -> str:
    """
    Check if an Azure resource complies with organizational policies.

    Args:
        resource_group: Resource group name.
        resource_type: Resource type (e.g. 'Microsoft.Storage/storageAccounts').
        resource_name: Resource name.
    """
    loop = asyncio.get_running_loop()

    def _check():
        resource_client = _get_resource_client()
        
        try:
            # Build the resource ID
            sub_id = _get_azure_subscription_id()
            resource_id = (
                f"/subscriptions/{sub_id}/resourceGroups/{resource_group}"
                f"/providers/{resource_type}/{resource_name}"
            )
            
            # Try to get the resource to verify it exists
            parts = resource_type.split('/')
            provider = parts[0]
            res_type = '/'.join(parts[1:])
            resource = resource_client.resources.get_by_id(resource_id, '2021-04-01')
            
            # Check policy compliance via policy insights
            policy_client = _get_policy_client()
            query_results = policy_client.policy_states.list_query_results_for_resource(
                "latest", resource_id
            )
            
            states = list(query_results)
            non_compliant = [
                {
                    "policy_name": s.policy_definition_name,
                    "compliance_state": s.compliance_state,
                }
                for s in states if s.compliance_state and s.compliance_state != "Compliant"
            ]
            
            return {
                "status": "checked",
                "resource_name": resource_name,
                "resource_type": resource_type,
                "policy_compliant": len(non_compliant) == 0,
                "total_policies_evaluated": len(states),
                "non_compliant_policies": non_compliant,
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "resource_name": resource_name,
            }

    result = await loop.run_in_executor(None, _check)
    return json.dumps(result, default=str)


@mcp.tool()
async def azure_get_resource_status(
    resource_group: str,
    resource_type: str,
    resource_name: str,
) -> str:
    """
    Get the provisioning status of an Azure resource.

    Args:
        resource_group: Resource group name.
        resource_type: Resource type (e.g. 'Microsoft.Storage/storageAccounts').
        resource_name: Resource name.
    """
    loop = asyncio.get_running_loop()

    def _get_status():
        client = _get_resource_client()
        
        try:
            resource = client.resources.get(
                resource_group, resource_type.split('/')[0],
                '', resource_type.split('/')[1], resource_name, '2021-04-01'
            )
            
            return {
                "status": "found",
                "resource_name": resource.name,
                "resource_type": resource.type,
                "location": resource.location,
                "provisioning_state": resource.properties.get('provisioningState') if resource.properties else None,
                "tags": resource.tags,
            }
            
        except Exception as e:
            return {
                "status": "not_found",
                "error": str(e),
                "resource_name": resource_name,
            }

    result = await loop.run_in_executor(None, _get_status)
    return json.dumps(result, default=str)


# ── Entry point ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    # Host/port configured via FastMCP constructor above
    mcp.run(transport="sse")
