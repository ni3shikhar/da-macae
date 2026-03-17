"""Quick test of Azure credentials from MCP container."""
import os
import json

sub_id = os.environ.get("AZURE_SUBSCRIPTION_ID", "")
tenant_id = os.environ.get("AZURE_TENANT_ID", "")
client_id = os.environ.get("AZURE_CLIENT_ID", "")
has_secret = bool(os.environ.get("AZURE_CLIENT_SECRET", ""))

print(f"Subscription ID: {sub_id}")
print(f"Tenant ID: {tenant_id}")
print(f"Client ID: {client_id}")
print(f"Has Client Secret: {has_secret}")
print()

# Test 1: Authenticate
try:
    from azure.identity import DefaultAzureCredential
    cred = DefaultAzureCredential()
    token = cred.get_token("https://management.azure.com/.default")
    print("AUTH: SUCCESS - got token")
except Exception as e:
    print(f"AUTH: FAILED - {e}")
    exit(1)

# Test 2: List resource groups
try:
    from azure.mgmt.resource import ResourceManagementClient
    client = ResourceManagementClient(cred, sub_id)
    groups = list(client.resource_groups.list())
    print(f"RESOURCE GROUPS: Found {len(groups)}")
    for rg in groups[:10]:
        print(f"  - {rg.name} ({rg.location})")
except Exception as e:
    print(f"RESOURCE GROUPS: FAILED - {e}")

# Test 3: Try creating a resource group
print()
print("Test 3: Create resource group (dry-run check)...")
try:
    exists = client.resource_groups.check_existence("rg-test-damacae-check")
    print(f"  check_existence works: rg-test-damacae-check exists={exists}")
except Exception as e:
    print(f"  check_existence FAILED: {e}")

# Test 4: Check ADF client
print()
print("Test 4: ADF management client...")
try:
    from azure.mgmt.datafactory import DataFactoryManagementClient
    adf_client = DataFactoryManagementClient(cred, sub_id)
    # Just list - don't create
    factories = list(adf_client.factories.list())
    print(f"  ADF LIST: Found {len(factories)} factories")
    for f in factories[:5]:
        print(f"    - {f.name} ({f.location})")
except Exception as e:
    print(f"  ADF: FAILED - {e}")

# Test 5: Check SQL client
print()
print("Test 5: SQL management client...")
try:
    from azure.mgmt.sql import SqlManagementClient
    sql_client = SqlManagementClient(cred, sub_id)
    servers = list(sql_client.servers.list())
    print(f"  SQL LIST: Found {len(servers)} servers")
    for s in servers[:5]:
        print(f"    - {s.name} ({s.location})")
except Exception as e:
    print(f"  SQL: FAILED - {e}")

# Test 6: Check Storage client
print()
print("Test 6: Storage management client...")
try:
    from azure.mgmt.storage import StorageManagementClient
    storage_client = StorageManagementClient(cred, sub_id)
    accounts = list(storage_client.storage_accounts.list())
    print(f"  STORAGE LIST: Found {len(accounts)} accounts")
    for a in accounts[:5]:
        print(f"    - {a.name} ({a.location})")
except Exception as e:
    print(f"  STORAGE: FAILED - {e}")
