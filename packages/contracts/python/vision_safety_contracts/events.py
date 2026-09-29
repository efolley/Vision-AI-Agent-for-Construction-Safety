from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from jsonschema import Draft202012Validator


class ContractError(ValueError): pass


@dataclass(frozen=True, slots=True)
class InspectionRequested:
    event_id: str
    trace_id: str
    tenant_id: str
    inspection_id: str
    schema_version: str
    occurred_at: str
    media_uri: str

    @classmethod
    def create(cls, *, trace_id: str, tenant_id: str, inspection_id: str, media_uri: str) -> InspectionRequested:
        return cls(str(uuid4()), trace_id, tenant_id, inspection_id, "v1", datetime.now(UTC).isoformat(), media_uri)

    def payload(self) -> dict[str, str]: return asdict(self)


class ContractRegistry:
    def __init__(self) -> None:
        path = Path(__file__).parents[2] / "schemas" / "inspection.requested.v1.json"
        self._inspection = Draft202012Validator(json.loads(path.read_text()))

    def validate(self, topic: str, payload: Mapping[str, Any]) -> None:
        if topic != "inspection.requested.v1": raise ContractError(f"Unsupported topic: {topic}")
        errors = sorted(self._inspection.iter_errors(dict(payload)), key=lambda error: error.path)
        if errors: raise ContractError(errors[0].message)
