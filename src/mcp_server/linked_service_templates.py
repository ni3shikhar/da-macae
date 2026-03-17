"""
Linked Service / Connection Templates for Azure Data Factory, Synapse Analytics, and Fabric.

Provides canonical JSON-ARM templates for every supported source type so that
MCP tools can generate valid linked-service definitions with minimal user input.
"""

from __future__ import annotations

from typing import Any

# ── ADF / Synapse Linked Service Templates ─────────────────────────────
# Each template follows the ARM resource schema for
# Microsoft.DataFactory/factories/linkedservices
# (also valid for Synapse workspaces with minor wrapper changes).
#
# Placeholder tokens use the form {{PLACEHOLDER}} and must be replaced
# at tool invocation time.

ADF_LINKED_SERVICE_TEMPLATES: dict[str, dict[str, Any]] = {
    # ── SQL Server (on-prem / Azure SQL / VM) ─────────────────────────
    "sql_server": {
        "name": "{{CONNECTION_NAME}}",
        "properties": {
            "type": "SqlServer",
            "typeProperties": {
                "connectionString": (
                    "Server={{HOST}};Database={{DATABASE}};"
                    "User ID={{USERNAME}};Password={{PASSWORD}};"
                    "Encrypt=true;TrustServerCertificate=false;"
                ),
            },
            "connectVia": {"referenceName": "{{IR_NAME}}", "type": "IntegrationRuntimeReference"},
        },
    },
    # ── Azure SQL Database ────────────────────────────────────────────
    "azure_sql": {
        "name": "{{CONNECTION_NAME}}",
        "properties": {
            "type": "AzureSqlDatabase",
            "typeProperties": {
                "connectionString": (
                    "Server=tcp:{{HOST}},1433;Database={{DATABASE}};"
                    "Authentication=Active Directory Default;"
                ),
            },
        },
    },
    # ── PostgreSQL ────────────────────────────────────────────────────
    "postgresql": {
        "name": "{{CONNECTION_NAME}}",
        "properties": {
            "type": "AzurePostgreSql",
            "typeProperties": {
                "connectionString": (
                    "Server={{HOST}};Database={{DATABASE}};"
                    "Port={{PORT}};UID={{USERNAME}};Password={{PASSWORD}};"
                    "SSL Mode=Require;"
                ),
            },
        },
    },
    # ── MySQL / MariaDB ───────────────────────────────────────────────
    "mysql": {
        "name": "{{CONNECTION_NAME}}",
        "properties": {
            "type": "AzureMySql",
            "typeProperties": {
                "connectionString": (
                    "Server={{HOST}};Database={{DATABASE}};"
                    "Port={{PORT}};UID={{USERNAME}};Password={{PASSWORD}};"
                    "SslMode=Required;"
                ),
            },
        },
    },
    # ── Oracle Database ───────────────────────────────────────────────
    "oracle": {
        "name": "{{CONNECTION_NAME}}",
        "properties": {
            "type": "Oracle",
            "typeProperties": {
                "connectionString": (
                    "Host={{HOST}};Port={{PORT}};SID={{SID}};"
                    "User Id={{USERNAME}};Password={{PASSWORD}};"
                ),
            },
            "connectVia": {"referenceName": "{{IR_NAME}}", "type": "IntegrationRuntimeReference"},
        },
    },
    # ── MongoDB / MongoDB Atlas ───────────────────────────────────────
    "mongodb": {
        "name": "{{CONNECTION_NAME}}",
        "properties": {
            "type": "MongoDbV2",
            "typeProperties": {
                "connectionString": "mongodb://{{USERNAME}}:{{PASSWORD}}@{{HOST}}:{{PORT}}",
                "database": "{{DATABASE}}",
            },
            "connectVia": {"referenceName": "{{IR_NAME}}", "type": "IntegrationRuntimeReference"},
        },
    },
    # ── Azure Cosmos DB (NoSQL API) ───────────────────────────────────
    "cosmosdb": {
        "name": "{{CONNECTION_NAME}}",
        "properties": {
            "type": "CosmosDb",
            "typeProperties": {
                "connectionString": "AccountEndpoint={{ENDPOINT}};AccountKey={{ACCOUNT_KEY}};Database={{DATABASE}}",
            },
        },
    },
    # ── Snowflake ─────────────────────────────────────────────────────
    "snowflake": {
        "name": "{{CONNECTION_NAME}}",
        "properties": {
            "type": "Snowflake",
            "typeProperties": {
                "connectionString": (
                    "jdbc:snowflake://{{ACCOUNT}}.snowflakecomputing.com/?"
                    "db={{DATABASE}}&warehouse={{WAREHOUSE}}&role={{ROLE}}"
                ),
                "password": {"type": "SecureString", "value": "{{PASSWORD}}"},
            },
        },
    },
    # ── Azure Data Lake Storage Gen2 ──────────────────────────────────
    "adls_gen2": {
        "name": "{{CONNECTION_NAME}}",
        "properties": {
            "type": "AzureBlobFS",
            "typeProperties": {
                "url": "https://{{STORAGE_ACCOUNT}}.dfs.core.windows.net",
            },
            # Uses Managed Identity by default
        },
    },
    # ── Azure Blob Storage ────────────────────────────────────────────
    "azure_blob": {
        "name": "{{CONNECTION_NAME}}",
        "properties": {
            "type": "AzureBlobStorage",
            "typeProperties": {
                "connectionString": (
                    "DefaultEndpointsProtocol=https;"
                    "AccountName={{STORAGE_ACCOUNT}};"
                    "AccountKey={{ACCOUNT_KEY}};"
                    "EndpointSuffix=core.windows.net"
                ),
            },
        },
    },
    # ── Databricks ────────────────────────────────────────────────────
    "databricks": {
        "name": "{{CONNECTION_NAME}}",
        "properties": {
            "type": "AzureDatabricks",
            "typeProperties": {
                "domain": "https://{{WORKSPACE_URL}}",
                "accessToken": {"type": "SecureString", "value": "{{ACCESS_TOKEN}}"},
                "existingClusterId": "{{CLUSTER_ID}}",
            },
        },
    },
    # ── Google BigQuery ───────────────────────────────────────────────
    "bigquery": {
        "name": "{{CONNECTION_NAME}}",
        "properties": {
            "type": "GoogleBigQuery",
            "typeProperties": {
                "project": "{{PROJECT_ID}}",
                "authenticationType": "ServiceAuthentication",
                "email": "{{SERVICE_ACCOUNT_EMAIL}}",
                "keyFileContent": {"type": "SecureString", "value": "{{KEY_FILE_CONTENT}}"},
            },
        },
    },
}


# ── ADF Pipeline Templates ────────────────────────────────────────────

ADF_COPY_PIPELINE_TEMPLATE: dict[str, Any] = {
    "name": "{{PIPELINE_NAME}}",
    "properties": {
        "activities": [
            {
                "name": "Copy_{{SOURCE_TABLE}}_to_{{TARGET_TABLE}}",
                "type": "Copy",
                "inputs": [
                    {
                        "referenceName": "{{SOURCE_DATASET}}",
                        "type": "DatasetReference",
                    }
                ],
                "outputs": [
                    {
                        "referenceName": "{{TARGET_DATASET}}",
                        "type": "DatasetReference",
                    }
                ],
                "typeProperties": {
                    "source": {"type": "{{SOURCE_TYPE}}Source"},
                    "sink": {"type": "{{SINK_TYPE}}Sink", "writeBehavior": "insert"},
                    "enableStaging": False,
                },
            }
        ],
    },
}

ADF_DATASET_TEMPLATE: dict[str, Any] = {
    "name": "{{DATASET_NAME}}",
    "properties": {
        "type": "{{DATASET_TYPE}}",
        "linkedServiceName": {
            "referenceName": "{{LINKED_SERVICE_NAME}}",
            "type": "LinkedServiceReference",
        },
        "typeProperties": {
            "schema": "{{SCHEMA}}",
            "table": "{{TABLE}}",
        },
    },
}


# ── Synapse-specific wrappers ─────────────────────────────────────────
# Synapse linked services use the same inner structure but are deployed
# as workspace resources rather than ARM factory resources.

SYNAPSE_LINKED_SERVICE_TEMPLATES = ADF_LINKED_SERVICE_TEMPLATES  # Same payload

SYNAPSE_SPARK_POOL_NOTEBOOK_TEMPLATE: dict[str, Any] = {
    "name": "{{NOTEBOOK_NAME}}",
    "properties": {
        "nbformat": 4,
        "nbformat_minor": 2,
        "cells": [
            {
                "cell_type": "code",
                "source": [
                    "# Auto-generated by DA-MACAÉ Pipeline Agent\n",
                    "from pyspark.sql import SparkSession\n",
                    "\n",
                    "spark = SparkSession.builder.getOrCreate()\n",
                    "\n",
                    "# Read from source\n",
                    'source_df = spark.read.format("{{SOURCE_FORMAT}}") \\\n',
                    '    .option("url", "{{SOURCE_URL}}") \\\n',
                    '    .option("dbtable", "{{SOURCE_TABLE}}") \\\n',
                    "    .load()\n",
                    "\n",
                    "# Write to target\n",
                    'source_df.write.format("{{TARGET_FORMAT}}") \\\n',
                    '    .option("url", "{{TARGET_URL}}") \\\n',
                    '    .option("dbtable", "{{TARGET_TABLE}}") \\\n',
                    '    .mode("append") \\\n',
                    "    .save()\n",
                ],
                "metadata": {},
                "outputs": [],
            }
        ],
        "metadata": {
            "language_info": {"name": "python"},
            "a]]_name": "synapse_pyspark",
        },
    },
}


# ── Fabric Templates ──────────────────────────────────────────────────
# Fabric uses Connections (not linked services) and Dataflow Gen2.

FABRIC_CONNECTION_TEMPLATES: dict[str, dict[str, Any]] = {
    "sql_server": {
        "connectionName": "{{CONNECTION_NAME}}",
        "connectivityType": "OnPremisesDataGateway",
        "connectionDetails": {
            "type": "SQL",
            "parameters": {
                "server": "{{HOST}}",
                "database": "{{DATABASE}}",
            },
        },
        "credentialDetails": {
            "credentialType": "Basic",
            "credentials": {
                "username": "{{USERNAME}}",
                "password": "{{PASSWORD}}",
            },
        },
        "privacyLevel": "Organizational",
    },
    "azure_sql": {
        "connectionName": "{{CONNECTION_NAME}}",
        "connectivityType": "Cloud",
        "connectionDetails": {
            "type": "SQL",
            "parameters": {
                "server": "{{HOST}}",
                "database": "{{DATABASE}}",
            },
        },
        "credentialDetails": {
            "credentialType": "OAuth2",
        },
        "privacyLevel": "Organizational",
    },
    "postgresql": {
        "connectionName": "{{CONNECTION_NAME}}",
        "connectivityType": "Cloud",
        "connectionDetails": {
            "type": "PostgreSQL",
            "parameters": {
                "server": "{{HOST}}",
                "database": "{{DATABASE}}",
                "port": "{{PORT}}",
            },
        },
        "credentialDetails": {
            "credentialType": "Basic",
            "credentials": {
                "username": "{{USERNAME}}",
                "password": "{{PASSWORD}}",
            },
        },
        "privacyLevel": "Organizational",
    },
    "mysql": {
        "connectionName": "{{CONNECTION_NAME}}",
        "connectivityType": "Cloud",
        "connectionDetails": {
            "type": "MySQL",
            "parameters": {
                "server": "{{HOST}}",
                "database": "{{DATABASE}}",
                "port": "{{PORT}}",
            },
        },
        "credentialDetails": {
            "credentialType": "Basic",
            "credentials": {
                "username": "{{USERNAME}}",
                "password": "{{PASSWORD}}",
            },
        },
        "privacyLevel": "Organizational",
    },
    "oracle": {
        "connectionName": "{{CONNECTION_NAME}}",
        "connectivityType": "OnPremisesDataGateway",
        "connectionDetails": {
            "type": "Oracle",
            "parameters": {
                "server": "{{HOST}}:{{PORT}}/{{SID}}",
            },
        },
        "credentialDetails": {
            "credentialType": "Basic",
            "credentials": {
                "username": "{{USERNAME}}",
                "password": "{{PASSWORD}}",
            },
        },
        "privacyLevel": "Organizational",
    },
    "mongodb": {
        "connectionName": "{{CONNECTION_NAME}}",
        "connectivityType": "Cloud",
        "connectionDetails": {
            "type": "MongoDB",
            "parameters": {
                "connectionString": "mongodb://{{HOST}}:{{PORT}}",
                "database": "{{DATABASE}}",
            },
        },
        "credentialDetails": {
            "credentialType": "Basic",
            "credentials": {
                "username": "{{USERNAME}}",
                "password": "{{PASSWORD}}",
            },
        },
        "privacyLevel": "Organizational",
    },
    "cosmosdb": {
        "connectionName": "{{CONNECTION_NAME}}",
        "connectivityType": "Cloud",
        "connectionDetails": {
            "type": "CosmosDb",
            "parameters": {
                "endpoint": "{{ENDPOINT}}",
                "database": "{{DATABASE}}",
            },
        },
        "credentialDetails": {
            "credentialType": "Key",
            "credentials": {
                "accountKey": "{{ACCOUNT_KEY}}",
            },
        },
        "privacyLevel": "Organizational",
    },
    "snowflake": {
        "connectionName": "{{CONNECTION_NAME}}",
        "connectivityType": "Cloud",
        "connectionDetails": {
            "type": "Snowflake",
            "parameters": {
                "server": "{{ACCOUNT}}.snowflakecomputing.com",
                "database": "{{DATABASE}}",
                "warehouse": "{{WAREHOUSE}}",
            },
        },
        "credentialDetails": {
            "credentialType": "Basic",
            "credentials": {
                "username": "{{USERNAME}}",
                "password": "{{PASSWORD}}",
            },
        },
        "privacyLevel": "Organizational",
    },
    "adls_gen2": {
        "connectionName": "{{CONNECTION_NAME}}",
        "connectivityType": "Cloud",
        "connectionDetails": {
            "type": "AzureDataLakeStorage",
            "parameters": {
                "url": "https://{{STORAGE_ACCOUNT}}.dfs.core.windows.net",
            },
        },
        "credentialDetails": {
            "credentialType": "OAuth2",
        },
        "privacyLevel": "Organizational",
    },
    "azure_blob": {
        "connectionName": "{{CONNECTION_NAME}}",
        "connectivityType": "Cloud",
        "connectionDetails": {
            "type": "AzureBlobStorage",
            "parameters": {
                "accountName": "{{STORAGE_ACCOUNT}}",
            },
        },
        "credentialDetails": {
            "credentialType": "Key",
            "credentials": {
                "accountKey": "{{ACCOUNT_KEY}}",
            },
        },
        "privacyLevel": "Organizational",
    },
    "databricks": {
        "connectionName": "{{CONNECTION_NAME}}",
        "connectivityType": "Cloud",
        "connectionDetails": {
            "type": "Databricks",
            "parameters": {
                "workspaceUrl": "https://{{WORKSPACE_URL}}",
                "clusterId": "{{CLUSTER_ID}}",
            },
        },
        "credentialDetails": {
            "credentialType": "Token",
            "credentials": {
                "token": "{{ACCESS_TOKEN}}",
            },
        },
        "privacyLevel": "Organizational",
    },
    "bigquery": {
        "connectionName": "{{CONNECTION_NAME}}",
        "connectivityType": "Cloud",
        "connectionDetails": {
            "type": "GoogleBigQuery",
            "parameters": {
                "project": "{{PROJECT_ID}}",
            },
        },
        "credentialDetails": {
            "credentialType": "ServiceAccount",
            "credentials": {
                "email": "{{SERVICE_ACCOUNT_EMAIL}}",
                "keyFileContent": "{{KEY_FILE_CONTENT}}",
            },
        },
        "privacyLevel": "Organizational",
    },
}


# ── Fabric Dataflow Gen2 Template ─────────────────────────────────────

FABRIC_DATAFLOW_GEN2_TEMPLATE: dict[str, Any] = {
    "name": "{{DATAFLOW_NAME}}",
    "description": "Auto-generated by DA-MACAÉ Pipeline Agent",
    "mashup": {
        "document": "section Section1;\nshared {{QUERY_NAME}} = let\n"
        "    Source = {{SOURCE_CONNECTOR}}({{SOURCE_PARAMS}}),\n"
        '    Data = Source{[Schema="{{SCHEMA}}",Item="{{TABLE}}"]}[Data]\n'
        "in\n    Data;",
        "queryGroups": [],
    },
    "destinationSettings": {
        "loadToLakehouse": {
            "lakehouseId": "{{LAKEHOUSE_ID}}",
            "tableName": "{{TARGET_TABLE}}",
            "loadType": "Append",
        }
    },
}


# ── Helper Functions ──────────────────────────────────────────────────


def get_supported_source_types() -> list[str]:
    """Return the list of supported data source types."""
    return list(ADF_LINKED_SERVICE_TEMPLATES.keys())


def get_template(
    source_type: str,
    azure_service: str,  # "adf", "synapse", "fabric"
) -> dict[str, Any] | None:
    """Return the appropriate linked service / connection template."""
    source_type = source_type.lower().replace(" ", "_").replace("-", "_")
    azure_service = azure_service.lower().strip()

    if azure_service in ("adf", "data_factory", "datafactory"):
        return ADF_LINKED_SERVICE_TEMPLATES.get(source_type)
    elif azure_service in ("synapse", "synapse_analytics"):
        return SYNAPSE_LINKED_SERVICE_TEMPLATES.get(source_type)
    elif azure_service in ("fabric", "microsoft_fabric"):
        return FABRIC_CONNECTION_TEMPLATES.get(source_type)
    return None


def fill_template(template: dict[str, Any], params: dict[str, str]) -> dict[str, Any]:
    """Deep-replace {{PLACEHOLDER}} tokens in a template dict."""
    import copy

    def _replace(obj: Any) -> Any:
        if isinstance(obj, str):
            for key, value in params.items():
                obj = obj.replace(f"{{{{{key}}}}}", value)
            return obj
        if isinstance(obj, dict):
            return {k: _replace(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_replace(item) for item in obj]
        return obj

    return _replace(copy.deepcopy(template))
