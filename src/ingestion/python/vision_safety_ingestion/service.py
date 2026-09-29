from __future__ import annotations

import hashlib
from typing import Protocol
from uuid import uuid4

from vision_safety_contracts import ContractRegistry, InspectionRequested

from .store import Database, Inspection, OutboxMessage


class IngestionError(ValueError): pass
class ObjectStorage(Protocol):
    def put(self, *, tenant_id: str, filename: str, content: bytes, content_type: str) -> str: ...
class InMemoryObjectStorage:
    def __init__(self) -> None: self.objects: dict[str, bytes]={}
    def put(self, *, tenant_id: str, filename: str, content: bytes, content_type: str) -> str:
        digest=hashlib.sha256(content).hexdigest(); uri=f"memory://{tenant_id}/{digest}/{filename}"; self.objects[uri]=content; return uri

class IngestionService:
    allowed_types={"image/jpeg":b"\xff\xd8\xff", "image/png":b"\x89PNG\r\n\x1a\n", "image/webp":b"RIFF"}
    def __init__(self, database: Database, storage: ObjectStorage, contracts: ContractRegistry, max_bytes: int=10_000_000) -> None: self.database, self.storage, self.contracts, self.max_bytes=database, storage, contracts, max_bytes
    def create_inspection(self, *, tenant_id: str, trace_id: str, filename: str, content_type: str, content: bytes) -> str:
        self._validate(content_type, content); inspection_id=str(uuid4()); uri=self.storage.put(tenant_id=tenant_id, filename=filename, content=content, content_type=content_type); event=InspectionRequested.create(trace_id=trace_id, tenant_id=tenant_id, inspection_id=inspection_id, media_uri=uri); self.contracts.validate("inspection.requested.v1", event.payload())
        with self.database.sessions.begin() as session:
            session.add(Inspection(id=inspection_id, tenant_id=tenant_id, filename=filename, media_uri=uri)); session.add(OutboxMessage(id=event.event_id, topic="inspection.requested.v1", payload=event.payload()))
        return inspection_id
    def _validate(self, content_type: str, content: bytes) -> None:
        if content_type not in self.allowed_types: raise IngestionError("Unsupported content type")
        if not content or len(content)>self.max_bytes: raise IngestionError("Invalid media size")
        if not content.startswith(self.allowed_types[content_type]): raise IngestionError("Media signature does not match content type")
