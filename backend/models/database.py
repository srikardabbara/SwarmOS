"""SQLAlchemy database models."""

import os
from datetime import datetime
from typing import Generator

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, create_engine, inspect, text
from sqlalchemy.orm import Session, declarative_base, relationship, sessionmaker

Base = declarative_base()


def normalize_database_url(url: str) -> str:
    """Use the psycopg driver when the host gives a plain Postgres URL."""
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


# SQLite remains the local default. Set DATABASE_URL to host on Postgres.
DATABASE_URL = normalize_database_url(os.environ.get("DATABASE_URL", "sqlite:///./swarmos.db"))

_sqlite = DATABASE_URL.startswith("sqlite")
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if _sqlite else {},
    pool_pre_ping=not _sqlite,
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class ProjectDB(Base):
    """A customer project. The ingest key is stored only as a hash."""

    __tablename__ = "projects"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    key_hash = Column(String, nullable=False, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    traces = relationship("TraceDB", back_populates="project")


class TraceDB(Base):
    """Trace database model."""

    __tablename__ = "traces"

    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=True, index=True)
    test_id = Column(String, nullable=True, index=True)
    workflow_id = Column(String, nullable=False, index=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String, nullable=False, default="running")
    input_data = Column(Text, nullable=False)  # JSON string
    output_data = Column(Text, nullable=True)  # JSON string
    metadata = Column(Text, nullable=False, default="{}")  # JSON string

    # Relationships
    project = relationship("ProjectDB", back_populates="traces")
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
    _ensure_project_column()
    print("Database initialized successfully")


def _ensure_project_column() -> None:
    """Add project scoping to a database created before projects existed."""
    columns = {column["name"] for column in inspect(engine).get_columns("traces")}
    if "project_id" in columns:
        return
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE traces ADD COLUMN project_id VARCHAR"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_traces_project_id ON traces (project_id)"))


def get_db() -> Generator[Session, None, None]:
    """Get database session (for FastAPI dependency injection)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
