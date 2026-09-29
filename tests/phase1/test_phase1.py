from __future__ import annotations

import base64
import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
for path in (
    ROOT / "packages/contracts/python",
    ROOT / "packages/shared/python",
    ROOT / "src/ingestion/python",
    ROOT / "src/api-gateway/python",
):
    sys.path.insert(0, str(path))
from vision_safety_gateway import create_app
from vision_safety_ingestion import (
    Database,
    IdempotentConsumer,
    IngestionError,
    IngestionService,
    InMemoryObjectStorage,
    OutboxPublisher,
    RetryPolicy,
)
from vision_safety_ingestion.store import Inspection, MemoryProducer, OutboxMessage

from vision_safety_contracts import ContractError, ContractRegistry, InspectionRequested
from vision_safety_core.gateway import (
    IdempotencyService,
    InMemoryRedis,
    JwtVerifier,
    Principal,
    RateLimiter,
)

PNG = b"\x89PNG\r\n\x1a\nphase-one"


class PhaseOneTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = Database("sqlite+pysqlite:///:memory:")
        self.storage = InMemoryObjectStorage()
        self.registry = ContractRegistry()
        self.ingestion = IngestionService(self.db, self.storage, self.registry)
        self.redis = InMemoryRedis()
        self.verifier = JwtVerifier("secret", "issuer", "audience")

    def tearDown(self) -> None:
        self.db.engine.dispose()

    def headers(self, tenant: str = "tenant-a", key: str = "key-1") -> dict[str, str]:
        token = self.verifier.issue_for_test(Principal("user", tenant, "safety_manager"))
        return {"Authorization": f"Bearer {token}", "Idempotency-Key": key, "X-Trace-Id": "trace-1"}

    def app(self, limit: int = 3) -> TestClient:
        return TestClient(
            create_app(
                verifier=self.verifier,
                limiter=RateLimiter(self.redis, limit, 60),
                idempotency=IdempotencyService(self.redis),
                ingestion=self.ingestion,
            )
        )

    def body(self) -> dict[str, str]:
        return {
            "filename": "site.png",
            "content_type": "image/png",
            "content_base64": base64.b64encode(PNG).decode(),
        }

    def test_gateway_accepts_authenticated_submission(self) -> None:
        response = self.app().post(
            "/v1/tenants/tenant-a/inspections", json=self.body(), headers=self.headers()
        )
        self.assertEqual(response.status_code, 200)

    def test_gateway_rejects_missing_token(self) -> None:
        self.assertEqual(
            self.app().post("/v1/tenants/tenant-a/inspections", json=self.body()).status_code, 401
        )

    def test_gateway_rejects_cross_tenant_access(self) -> None:
        self.assertEqual(
            self.app()
            .post("/v1/tenants/tenant-b/inspections", json=self.body(), headers=self.headers())
            .status_code,
            403,
        )

    def test_gateway_rejects_duplicate_idempotency_key(self) -> None:
        client = self.app()
        self.assertEqual(
            client.post(
                "/v1/tenants/tenant-a/inspections", json=self.body(), headers=self.headers()
            ).status_code,
            200,
        )
        self.assertEqual(
            client.post(
                "/v1/tenants/tenant-a/inspections", json=self.body(), headers=self.headers()
            ).status_code,
            409,
        )

    def test_gateway_rate_limits_tenant(self) -> None:
        client = self.app(limit=1)
        self.assertEqual(
            client.post(
                "/v1/tenants/tenant-a/inspections", json=self.body(), headers=self.headers()
            ).status_code,
            200,
        )
        self.assertEqual(
            client.post(
                "/v1/tenants/tenant-a/inspections",
                json=self.body(),
                headers=self.headers(key="other"),
            ).status_code,
            429,
        )

    def test_ingestion_rejects_bad_signature(self) -> None:
        with self.assertRaises(IngestionError):
            self.ingestion.create_inspection(
                tenant_id="t",
                trace_id="x",
                filename="x.png",
                content_type="image/png",
                content=b"bad",
            )

    def test_ingestion_rejects_unknown_type(self) -> None:
        with self.assertRaises(IngestionError):
            self.ingestion.create_inspection(
                tenant_id="t", trace_id="x", filename="x.gif", content_type="image/gif", content=PNG
            )

    def test_ingestion_persists_record_and_outbox_atomically(self) -> None:
        inspection = self.ingestion.create_inspection(
            tenant_id="t", trace_id="x", filename="x.png", content_type="image/png", content=PNG
        )
        with self.db.sessions() as session:
            self.assertIsNotNone(session.get(Inspection, inspection))
            self.assertEqual(len(session.query(OutboxMessage).all()), 1)

    def test_contract_accepts_valid_event(self) -> None:
        event = InspectionRequested.create(
            trace_id="x", tenant_id="t", inspection_id="i", media_uri="memory://x"
        )
        self.registry.validate("inspection.requested.v1", event.payload())

    def test_contract_rejects_wrong_version(self) -> None:
        event = InspectionRequested.create(
            trace_id="x", tenant_id="t", inspection_id="i", media_uri="memory://x"
        ).payload()
        event["schema_version"] = "v2"
        with self.assertRaises(ContractError):
            self.registry.validate("inspection.requested.v1", event)

    def test_contract_rejects_unknown_topic(self) -> None:
        with self.assertRaises(ContractError):
            self.registry.validate("unknown.v1", {})

    def test_outbox_publishes_event(self) -> None:
        self.ingestion.create_inspection(
            tenant_id="t", trace_id="x", filename="x.png", content_type="image/png", content=PNG
        )
        producer = MemoryProducer()
        self.assertEqual(OutboxPublisher(self.db, producer).publish_pending(), 1)
        self.assertEqual(producer.messages[0][0], "inspection.requested.v1")

    def test_outbox_does_not_republish(self) -> None:
        self.ingestion.create_inspection(
            tenant_id="t", trace_id="x", filename="x.png", content_type="image/png", content=PNG
        )
        producer = MemoryProducer()
        publisher = OutboxPublisher(self.db, producer)
        publisher.publish_pending()
        self.assertEqual(publisher.publish_pending(), 0)

    def test_outbox_sends_dlq_after_retries(self) -> None:
        class Broken:
            def __init__(self) -> None:
                self.messages = []

            def publish(self, topic: str, payload: dict[str, object]) -> None:
                if ".dlq" not in topic:
                    raise RuntimeError("down")
                self.messages.append((topic, payload))

        self.ingestion.create_inspection(
            tenant_id="t", trace_id="x", filename="x.png", content_type="image/png", content=PNG
        )
        producer = Broken()
        publisher = OutboxPublisher(self.db, producer, RetryPolicy(2))
        publisher.publish_pending()
        publisher.publish_pending()
        self.assertEqual(producer.messages[0][0], "inspection.requested.v1.dlq.v1")

    def test_idempotent_consumer_processes_once(self) -> None:
        calls = []
        consumer = IdempotentConsumer(self.db)
        self.assertTrue(consumer.process("event", lambda session: calls.append("done")))
        self.assertFalse(consumer.process("event", lambda session: calls.append("again")))
        self.assertEqual(calls, ["done"])

    def test_full_workflow_persists_and_publishes(self) -> None:
        response = self.app().post(
            "/v1/tenants/tenant-a/inspections", json=self.body(), headers=self.headers()
        )
        producer = MemoryProducer()
        OutboxPublisher(self.db, producer).publish_pending()
        self.assertEqual(response.json()["status"], "queued")
        self.assertEqual(len(producer.messages), 1)
