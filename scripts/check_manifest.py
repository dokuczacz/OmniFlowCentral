import json
import sys
from pathlib import Path

from azure.storage.blob import ContainerClient

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
APP_ROOT = REPO_ROOT / "OmniFlowCentral"
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from OmniFlowCentral.shared.config import AzureConfig


def main():
    client = ContainerClient.from_connection_string(
        AzureConfig.CONNECTION_STRING, AzureConfig.CONTAINER_NAME
    )
    blobs = list(client.list_blobs(name_starts_with="manifests/"))
    print("Found manifest blobs:", len(blobs))
    total_entries = 0
    for blob in blobs:
        print(" -", blob.name)
        if not blob.name.endswith("manifest.json"):
            continue
        raw = client.get_blob_client(blob.name).download_blob().readall().decode(
            "utf-8"
        )
        manifest = json.loads(raw)
        entries = manifest.get("entries", [])
        print(f"   entries: {len(entries)} (version {manifest.get('manifest_version')} updated at {manifest.get('updated_at')})")
        total_entries += len(entries)
    print("Total entries across manifests:", total_entries)


if __name__ == "__main__":
    main()
