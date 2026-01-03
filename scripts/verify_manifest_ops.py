import json
from datetime import datetime
from azure.core.exceptions import ResourceNotFoundError

from OmniFlowCentral.shared.manifest_helper import (
    build_manifest_entry,
    load_manifest,
    remove_manifest_entry,
    rename_manifest_entry,
    write_manifest,
)

class FakeDownloader:
    def __init__(self, data):
        self._data = data
    def readall(self):
        return self._data

class FakeBlobClient:
    def __init__(self, container, name):
        self.container = container
        self.name = name
    def download_blob(self):
        payload = self.container.blobs.get(self.name)
        if payload is None:
            raise ResourceNotFoundError('Blob not found')
        return FakeDownloader(payload)
    def upload_blob(self, payload, overwrite=False):
        self.container.blobs[self.name] = payload

class FakeContainerClient:
    def __init__(self):
        self.blobs = {}
    def get_blob_client(self, name):
        return FakeBlobClient(self, name)

container = FakeContainerClient()
entries = []
for idx, blob in enumerate(['users/alice/notes.json', 'users/alice/log.json']):
    entry = build_manifest_entry(
        namespaced=blob,
        target_blob_name=blob.split('/')[-1],
        payload={'display_name': blob.split('/')[-1], 'category': 'dataset', 'tags': ['test'], 'version': f'v{idx+1}'},
        content_type='application/json',
        size=123 + idx,
    )
    entries.append(entry)
manifest = {
    'manifest_version': 1,
    'updated_at': datetime.utcnow().isoformat() + 'Z',
    'entries': entries,
}
write_manifest(container, 'alice', manifest)
print('initial entries:', [e['blob_name'] for e in load_manifest(container, 'alice')['entries']])
removed = remove_manifest_entry(container, 'alice', 'users/alice/notes.json')
print('remove_manifest_entry returned', removed)
after_remove = load_manifest(container, 'alice')['entries']
print('entries after removal:', [e['blob_name'] for e in after_remove])
renamed = rename_manifest_entry(container, 'alice', 'users/alice/log.json', 'users/alice/log_latest.json', 'log_latest.json')
print('rename_manifest_entry returned', renamed)
after_rename = load_manifest(container, 'alice')['entries']
print('entries after rename:', [e['blob_name'] for e in after_rename])
print('manifest updated_at values:', [entry['updated_at'] for entry in after_rename])
