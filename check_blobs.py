from azure.storage.blob import BlobServiceClient
import os

conn = os.environ.get("AZURE_STORAGE_CONNECTION_STRING", 
    "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://azurite:10000/devstoreaccount1")
client = BlobServiceClient.from_connection_string(conn)
containers = list(client.list_containers())
if not containers:
    print("No containers found - storage is empty")
else:
    for c in containers:
        print(f"Container: {c.name}")
        blobs = list(client.get_container_client(c.name).list_blobs())
        if not blobs:
            print("  (empty)")
        for b in blobs:
            print(f"  - {b.name} ({b.size} bytes)")
