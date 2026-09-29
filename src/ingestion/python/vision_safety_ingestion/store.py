from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase): pass
class Inspection(Base):
    __tablename__="inspections"; id: Mapped[str]=mapped_column(String, primary_key=True); tenant_id: Mapped[str]=mapped_column(String, index=True); filename: Mapped[str]=mapped_column(String); media_uri: Mapped[str]=mapped_column(String); status: Mapped[str]=mapped_column(String, default="queued")
class OutboxMessage(Base):
    __tablename__="outbox_messages"; id: Mapped[str]=mapped_column(String, primary_key=True); topic: Mapped[str]=mapped_column(String); payload: Mapped[dict[str, Any]]=mapped_column(JSON); attempts: Mapped[int]=mapped_column(Integer, default=0); published: Mapped[bool]=mapped_column(Boolean, default=False); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
class ProcessedEvent(Base):
    __tablename__="processed_events"; event_id: Mapped[str]=mapped_column(String, primary_key=True); processed_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class Database:
    def __init__(self, url: str) -> None:
        options: dict[str, Any] = {}
        if url == "sqlite+pysqlite:///:memory:":
            options = {"connect_args": {"check_same_thread": False}, "poolclass": StaticPool}
        self.engine = create_engine(url, **options)
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(self.engine, expire_on_commit=False)

class KafkaProducer(Protocol):
    def publish(self, topic: str, payload: dict[str, Any]) -> None: ...
class MemoryProducer:
    def __init__(self) -> None: self.messages: list[tuple[str, dict[str, Any]]]=[]
    def publish(self, topic: str, payload: dict[str, Any]) -> None: self.messages.append((topic, payload))

@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_attempts: int = 3
    def next_delay_seconds(self, attempts: int) -> int: return 2 ** max(attempts - 1, 0)

class OutboxPublisher:
    def __init__(self, database: Database, producer: KafkaProducer, policy: RetryPolicy = RetryPolicy()) -> None: self.database, self.producer, self.policy=database, producer, policy
    def publish_pending(self) -> int:
        sent=0
        with self.database.sessions.begin() as session:
            for message in session.scalars(select(OutboxMessage).where(OutboxMessage.published.is_(False))).all():
                try: self.producer.publish(message.topic, message.payload); message.published=True; sent+=1
                except Exception:
                    message.attempts += 1
                    if message.attempts >= self.policy.max_attempts:
                        self.producer.publish(f"{message.topic}.dlq.v1", {"original": message.payload, "attempts": message.attempts}); message.published=True
        return sent

class IdempotentConsumer:
    def __init__(self, database: Database) -> None: self.database=database
    def process(self, event_id: str, handler: Callable[[Session], None]) -> bool:
        with self.database.sessions.begin() as session:
            if session.get(ProcessedEvent, event_id): return False
            handler(session); session.add(ProcessedEvent(event_id=event_id)); return True
