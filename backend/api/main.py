"""Main FastAPI application."""

import hashlib
import json
import os
import secrets
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session

from swarmos.langsmith.import_trace import LangSmithImportError, import_langsmith_trace

from backend.models.database import (
    EventDB,
    ProjectDB,
    TraceDB,
    ValidationResultDB,
    get_db,
    init_db,
)

# Create FastAPI app
app = FastAPI(
    title="SwarmOS API",
    description="Backend API for SwarmOS - Testing and reliability for LangGraph multi-agent systems",
    version="0.1.0",
)

def _dashboard_origins() -> List[str]:
    configured = os.environ.get("SWARMOS_DASHBOARD_ORIGIN", "http://localhost:3000")
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


# The dashboard origin is the only browser allowed to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=_dashboard_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

_bearer = HTTPBearer(auto_error=False)


def hash_key(api_key: str) -> str:
    """Hash a project ingest key. The plaintext is shown once at creation."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def require_project(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> ProjectDB:
    """Resolve the project for this request, or reject it."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Missing project key")
    project = (
        db.query(ProjectDB).filter(ProjectDB.key_hash == hash_key(credentials.credentials)).first()
    )
    if project is None:
        raise HTTPException(status_code=401, detail="Invalid project key")
    return project


# Pydantic models for API requests/responses
class EventCreate(BaseModel):
    """Event creation model."""

    id: str
    trace_id: str
    timestamp: datetime
    event_type: str
    agent: Optional[str] = None
    data: dict
    parent_event_id: Optional[str] = None


class EventResponse(BaseModel):
    """Event response model."""

    id: str
    trace_id: str
    timestamp: datetime
    event_type: str
    agent: Optional[str]
    data: dict
    parent_event_id: Optional[str]

    class Config:
        from_attributes = True


class ValidationResultCreate(BaseModel):
    """Validation result creation model."""

    id: str
    trace_id: str
    validation_type: str
    passed: bool
    message: str
    details: dict
    timestamp: datetime


class ValidationResultResponse(BaseModel):
    """Validation result response model."""

    id: str
    trace_id: str
    validation_type: str
    passed: bool
    message: str
    details: dict
    timestamp: datetime

    class Config:
        from_attributes = True


class TraceCreate(BaseModel):
    """Trace creation model."""

    id: str
    test_id: Optional[str] = None
    workflow_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str
    input_data: dict
    output_data: Optional[dict] = None
    metadata: dict
    events: List[EventCreate] = []
    validation_results: List[ValidationResultCreate] = []


class TraceResponse(BaseModel):
    """Trace response model."""

    id: str
    test_id: Optional[str]
    workflow_id: str
    started_at: datetime
    completed_at: Optional[datetime]
    status: str
    input_data: dict
    output_data: Optional[dict]
    metadata: dict

    class Config:
        from_attributes = True


class TraceWithDetails(TraceResponse):
    """Trace response with events and validations."""

    events: List[EventResponse]
    validation_results: List[ValidationResultResponse]


# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    init_db()


# Health check endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "SwarmOS API",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


class ProjectCreate(BaseModel):
    """Name for a new project."""

    name: str


class ProjectCreated(BaseModel):
    """Project plus the ingest key. The key is not stored in plaintext."""

    id: str
    name: str
    api_key: str


class ProjectResponse(BaseModel):
    """Project identity returned when a key is presented."""

    id: str
    name: str


@app.post("/projects", response_model=ProjectCreated, status_code=201)
async def create_project(body: ProjectCreate, db: Session = Depends(get_db)):
    """Create a project and return its ingest key once."""
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Project name is required")

    api_key = f"swarmos_{secrets.token_urlsafe(32)}"
    project = ProjectDB(id=str(uuid4()), name=name, key_hash=hash_key(api_key))
    db.add(project)
    db.commit()
    return ProjectCreated(id=project.id, name=project.name, api_key=api_key)


@app.get("/projects/current", response_model=ProjectResponse)
async def current_project(project: ProjectDB = Depends(require_project)):
    """Confirm a project key and return the project it unlocks."""
    return ProjectResponse(id=project.id, name=project.name)


# Trace endpoints
class LangSmithImportRequest(BaseModel):
    """A LangSmith trace address and the key used once to read it."""

    api_key: str
    url: str


def _persist_trace(trace: TraceCreate, project: ProjectDB, db: Session) -> TraceDB:
    """Store a trace for one project. Rejects an id that is already stored."""
    existing = db.query(TraceDB).filter(TraceDB.id == trace.id).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Trace {trace.id} already exists")

    db_trace = TraceDB(
        id=trace.id,
        project_id=project.id,
        test_id=trace.test_id,
        workflow_id=trace.workflow_id,
        started_at=trace.started_at,
        completed_at=trace.completed_at,
        status=trace.status,
        input_data=json.dumps(trace.input_data),
        output_data=json.dumps(trace.output_data) if trace.output_data else None,
        metadata=json.dumps(trace.metadata),
    )
    db.add(db_trace)

    # Create events
    for event in trace.events:
        db_event = EventDB(
            id=event.id,
            trace_id=event.trace_id,
            timestamp=event.timestamp,
            event_type=event.event_type,
            agent=event.agent,
            data=json.dumps(event.data),
            parent_event_id=event.parent_event_id,
        )
        db.add(db_event)

    # Create validation results
    for validation in trace.validation_results:
        db_validation = ValidationResultDB(
            id=validation.id,
            trace_id=validation.trace_id,
            validation_type=validation.validation_type,
            passed=1 if validation.passed else 0,
            message=validation.message,
            details=json.dumps(validation.details),
            timestamp=validation.timestamp,
        )
        db.add(db_validation)

    db.commit()
    db.refresh(db_trace)
    return db_trace


def _trace_response(db_trace: TraceDB) -> TraceResponse:
    return TraceResponse(
        id=db_trace.id,
        test_id=db_trace.test_id,
        workflow_id=db_trace.workflow_id,
        started_at=db_trace.started_at,
        completed_at=db_trace.completed_at,
        status=db_trace.status,
        input_data=json.loads(db_trace.input_data),
        output_data=json.loads(db_trace.output_data) if db_trace.output_data else None,
        metadata=json.loads(db_trace.metadata),
    )


@app.post("/traces", response_model=TraceResponse, status_code=201)
async def create_trace(
    trace: TraceCreate,
    project: ProjectDB = Depends(require_project),
    db: Session = Depends(get_db),
):
    """Create a new trace."""
    return _trace_response(_persist_trace(trace, project, db))


@app.post("/langsmith/import", response_model=TraceResponse, status_code=201)
async def import_langsmith(
    body: LangSmithImportRequest,
    project: ProjectDB = Depends(require_project),
    db: Session = Depends(get_db),
):
    """Read one LangSmith trace and store the handoff review. The LangSmith key is not saved."""
    try:
        trace = import_langsmith_trace(body.api_key, body.url)
    except LangSmithImportError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    created = TraceCreate.model_validate(trace.model_dump(mode="json"))
    return _trace_response(_persist_trace(created, project, db))


@app.get("/traces", response_model=List[TraceResponse])
async def list_traces(
    workflow_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    project: ProjectDB = Depends(require_project),
    db: Session = Depends(get_db),
):
    """List traces with optional filtering."""
    query = db.query(TraceDB).filter(TraceDB.project_id == project.id)

    if workflow_id:
        query = query.filter(TraceDB.workflow_id == workflow_id)
    if status:
        query = query.filter(TraceDB.status == status)

    query = query.order_by(TraceDB.started_at.desc())
    traces = query.offset(offset).limit(limit).all()

    return [
        TraceResponse(
            id=t.id,
            test_id=t.test_id,
            workflow_id=t.workflow_id,
            started_at=t.started_at,
            completed_at=t.completed_at,
            status=t.status,
            input_data=json.loads(t.input_data),
            output_data=json.loads(t.output_data) if t.output_data else None,
            metadata=json.loads(t.metadata),
        )
        for t in traces
    ]


@app.get("/traces/{trace_id}", response_model=TraceWithDetails)
async def get_trace(
    trace_id: str,
    project: ProjectDB = Depends(require_project),
    db: Session = Depends(get_db),
):
    """Get a specific trace with all details."""
    trace = (
        db.query(TraceDB)
        .filter(TraceDB.id == trace_id, TraceDB.project_id == project.id)
        .first()
    )

    if not trace:
        raise HTTPException(status_code=404, detail=f"Trace {trace_id} not found")

    # Get events
    events = db.query(EventDB).filter(EventDB.trace_id == trace_id).all()
    event_responses = [
        EventResponse(
            id=e.id,
            trace_id=e.trace_id,
            timestamp=e.timestamp,
            event_type=e.event_type,
            agent=e.agent,
            data=json.loads(e.data),
            parent_event_id=e.parent_event_id,
        )
        for e in events
    ]

    # Get validation results
    validations = (
        db.query(ValidationResultDB).filter(ValidationResultDB.trace_id == trace_id).all()
    )
    validation_responses = [
        ValidationResultResponse(
            id=v.id,
            trace_id=v.trace_id,
            validation_type=v.validation_type,
            passed=bool(v.passed),
            message=v.message,
            details=json.loads(v.details),
            timestamp=v.timestamp,
        )
        for v in validations
    ]

    return TraceWithDetails(
        id=trace.id,
        test_id=trace.test_id,
        workflow_id=trace.workflow_id,
        started_at=trace.started_at,
        completed_at=trace.completed_at,
        status=trace.status,
        input_data=json.loads(trace.input_data),
        output_data=json.loads(trace.output_data) if trace.output_data else None,
        metadata=json.loads(trace.metadata),
        events=event_responses,
        validation_results=validation_responses,
    )


@app.delete("/traces/{trace_id}", status_code=204)
async def delete_trace(
    trace_id: str,
    project: ProjectDB = Depends(require_project),
    db: Session = Depends(get_db),
):
    """Delete a trace."""
    trace = (
        db.query(TraceDB)
        .filter(TraceDB.id == trace_id, TraceDB.project_id == project.id)
        .first()
    )

    if not trace:
        raise HTTPException(status_code=404, detail=f"Trace {trace_id} not found")

    db.delete(trace)
    db.commit()

    return None


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
