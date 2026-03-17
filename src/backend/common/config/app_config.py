"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from functools import lru_cache

from pydantic_settings import BaseSettings


class AzureOpenAIConfig(BaseSettings):
    """Azure OpenAI service configuration."""

    endpoint: str = ""
    api_key: str = ""
    api_version: str = "2024-12-01-preview"
    chat_deployment: str = "gpt-4o"
    embedding_deployment: str = "text-embedding-3-small"
    reasoning_deployment: str = "o3-mini"

    model_config = {"env_prefix": "AZURE_OPENAI_"}


class AzureAIFoundryConfig(BaseSettings):
    """Azure AI Foundry (Projects) configuration."""

    project_connection_string: str = ""
    model_deployment_name: str = "gpt-4o"

    model_config = {"env_prefix": "AZURE_AI_FOUNDRY_"}


class CosmosDBConfig(BaseSettings):
    """Cosmos DB configuration."""

    endpoint: str = "https://localhost:8081"
    key: str = ""
    database_name: str = "damacae"
    container_name: str = "data"

    model_config = {"env_prefix": "COSMOS_"}


class AzureSearchConfig(BaseSettings):
    """Azure AI Search configuration."""

    endpoint: str = ""
    api_key: str = ""
    index_name: str = "migration-knowledge"

    model_config = {"env_prefix": "AZURE_SEARCH_"}


class AzureStorageConfig(BaseSettings):
    """Azure Blob Storage configuration."""

    connection_string: str = ""
    container_name: str = "migration-artifacts"

    model_config = {"env_prefix": "AZURE_STORAGE_"}


class AnthropicConfig(BaseSettings):
    """Anthropic (Claude) configuration."""

    api_key: str = ""
    model: str = "claude-opus-4-20250514"

    model_config = {"env_prefix": "ANTHROPIC_"}


class MCPConfig(BaseSettings):
    """MCP Server configuration."""

    server_url: str = "http://localhost:8001"
    enabled: bool = True

    model_config = {"env_prefix": "MCP_"}


class AuthConfig(BaseSettings):
    """Authentication configuration."""

    enabled: bool = False
    tenant_id: str = ""
    client_id: str = ""

    model_config = {"env_prefix": "AUTH_"}


class AppConfig(BaseSettings):
    """Top-level application configuration."""

    app_name: str = "DA-MACAÉ"
    environment: str = "development"
    log_level: str = "INFO"
    backend_port: int = 8000
    frontend_port: int = 3001
    cors_origins: str = "http://localhost:3001"
    rai_enabled: bool = True
    database_backend: str = "in_memory"  # "cosmosdb" | "in_memory"

    # Sub-configurations
    azure_openai: AzureOpenAIConfig = AzureOpenAIConfig()
    azure_ai_foundry: AzureAIFoundryConfig = AzureAIFoundryConfig()
    cosmos_db: CosmosDBConfig = CosmosDBConfig()
    azure_search: AzureSearchConfig = AzureSearchConfig()
    azure_storage: AzureStorageConfig = AzureStorageConfig()
    anthropic: AnthropicConfig = AnthropicConfig()
    mcp: MCPConfig = MCPConfig()
    auth: AuthConfig = AuthConfig()

    model_config = {"env_prefix": ""}

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_config() -> AppConfig:
    """Return cached application configuration singleton."""
    return AppConfig()
