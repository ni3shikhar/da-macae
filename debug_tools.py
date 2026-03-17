"""Debug script to test Claude API with actual MCP tools."""
import asyncio
import json
import os
import anthropic
from mcp import ClientSession
from mcp.client.sse import sse_client


# DiscoveryAgent tools from migration_team.json
DISCOVERY_TOOLS = [
    "pg_list_databases", "pg_list_schemas", "pg_list_tables", "pg_get_table_schema",
    "pg_run_query", "pg_get_foreign_keys",
    "mysql_list_databases", "mysql_list_tables", "mysql_get_table_schema", "mysql_run_query",
    "sql_list_databases", "sql_list_tables", "sql_get_table_schema", "sql_run_query",
    "mongo_list_databases", "mongo_list_collections", "mongo_get_collection_schema", "mongo_run_query",
    "cosmos_list_databases", "cosmos_list_containers", "cosmos_get_container_schema", "cosmos_run_query",
    "storage_list_containers", "storage_list_blobs", "storage_get_blob_content",
    "adf_list_pipelines", "adf_get_pipeline", "adf_list_datasets", "adf_get_dataset",
    "adf_list_linked_services", "adf_get_linked_service",
    "adf_list_dataflows", "adf_get_dataflow",
    "adf_list_triggers", "adf_get_trigger",
    "adf_list_integration_runtimes", "adf_get_integration_runtime",
    "keyvault_list_secrets", "keyvault_get_secret",
    "appconfig_list_settings", "appconfig_get_setting",
    "servicebus_list_queues", "servicebus_get_queue",
    "servicebus_list_topics", "servicebus_get_topic",
    "eventhub_list_hubs", "eventhub_get_hub",
    "apim_list_apis", "apim_get_api",
]


def mcp_tools_to_claude(tools, requested_names):
    claude_tools = []
    for tool in tools:
        name = tool.name
        if requested_names and name not in requested_names:
            continue
        description = (tool.description or "MCP tool: " + name)[:1024]
        input_schema = tool.inputSchema or {"type": "object", "properties": {}}
        claude_tools.append({
            "name": name,
            "description": description,
            "input_schema": input_schema,
        })
    return claude_tools


async def main():
    sse_url = "http://mcp-server:8001/sse"
    requested = set(DISCOVERY_TOOLS)

    print("Connecting to MCP server...")
    async with sse_client(sse_url, timeout=30, sse_read_timeout=300) as (rs, ws):
        async with ClientSession(rs, ws) as session:
            await session.initialize()
            tools_result = await session.list_tools()
            claude_tools = mcp_tools_to_claude(tools_result.tools, requested)
            
            print(f"Total MCP tools: {len(tools_result.tools)}")
            print(f"Agent tools: {len(claude_tools)}")
            
            # Print each tool's schema size
            total_schema_size = 0
            for ct in claude_tools:
                schema_str = json.dumps(ct)
                total_schema_size += len(schema_str)
                print(f"  {ct['name']}: {len(schema_str)} bytes")
            
            print(f"\nTotal tools JSON size: {total_schema_size} bytes")
            
            # Build the exact same kwargs as claude_mcp_runner
            system_prompt = "You are a DiscoveryAgent. Connect to PostgreSQL."
            task = "Connect to PostgreSQL database and list all tables."
            
            kwargs = {
                "model": "claude-opus-4-20250514",
                "system": system_prompt,
                "messages": [{"role": "user", "content": task}],
                "temperature": 0.3,
                "max_tokens": 16384,
            }
            if claude_tools:
                kwargs["tools"] = claude_tools
            
            print(f"\nFull request size: {len(json.dumps(kwargs))} bytes")
            print("\nCalling Claude API with streaming...")
            
            client = anthropic.AsyncAnthropic()
            try:
                async with client.messages.stream(**kwargs) as stream:
                    response = await stream.get_final_message()
                print(f"SUCCESS! stop_reason={response.stop_reason}")
                for block in response.content:
                    if block.type == "text":
                        print(f"  Text: {block.text[:200]}")
                    elif block.type == "tool_use":
                        print(f"  Tool call: {block.name}({json.dumps(block.input)[:100]})")
            except Exception as e:
                print(f"ERROR TYPE: {type(e).__name__}")
                print(f"ERROR: {e}")
                import traceback
                traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
