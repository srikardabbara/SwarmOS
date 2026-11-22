"""SQLAlchemy database models."""

import json
from datetime import datetime
from typing import Generator

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, relationship, sessionmaker

Base = declarative_base()

# Database URL (SQLite for MVP)
DATABASE_URL = "sqlite:///./swarmos.db"

# Create engine
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class TraceDB(Base):
    """Trace database model."""

    __tablename__ = "traces"

    id = Column(String, primary_key=True, index=True)
    test_id = Column(String, nullable=True, index=True)
    workflow_id = Column(String, nullable=False, index=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String, nullable=False, default="running")
    input_data = Column(Text, nullable=False)  # JSON string
    output_data = Column(Text, nullable=True)  # JSON string
    metadata = Column(Text, nullable=False, default="{}")  # JSON string

    # Relationships
    events = relationship("EventDB", back_populates="trace", cascade="all, delete-orphan")
    validation_results = relationship(
        "ValidationResultDB", back_populates="trace", cascade="all, delete-orphan"
    )


class EventDB(Base):
    """Event database model."""

    __tablename__ = "events"

    id = Column(String, primary_key=True, index=True)
    trace_id = Column(String, ForeignKey("traces.id"), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    event_type = Column(String, nullable=False, index=True)
    agent = Column(String, nullable=True, index=True)
    data = Column(Text, nullable=False, default="{}")  # JSON string
    parent_event_id = Column(String, nullable=True)

    # Relationship
    trace = relationship("TraceDB", back_populates="events")


class ValidationResultDB(Base):
    """Validation result database model."""

    __tablename__ = "validation_results"

    id = Column(String, primary_key=True, index=True)
    trace_id = Column(String, ForeignKey("traces.id"), nullable=False, index=True)
    validation_type = Column(String, nullable=False, index=True)
    passed = Column(Integer, nullable=False)  # 0 or 1 (boolean)
    message = Column(Text, nullable=False)
    details = Column(Text, nullable=False, default="{}")  # JSON string
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    trace = relationship("TraceDB", back_populates="validation_results")


def init_db() -> None:
    """Initialize the database (create tables)."""
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully")


def get_db() -> Generator[Session, None, None]:
    """Get database session (for FastAPI dependency injection)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
