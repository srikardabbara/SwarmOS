"""Main FastAPI application."""

import json
from datetime import datetime
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.models.database import (
    EventDB,
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

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


# Trace endpoints
@app.post("/traces", response_model=TraceResponse, status_code=201)
async def create_trace(trace: TraceCreate, db: Session = Depends(get_db)):
    """Create a new trace."""
    # Check if trace already exists
    existing = db.query(TraceDB).filter(TraceDB.id == trace.id).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Trace {trace.id} already exists")

    # Create trace
    db_trace = TraceDB(
        id=trace.id,
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


@app.get("/traces", response_model=List[TraceResponse])
async def list_traces(
    workflow_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List traces with optional filtering."""
    query = db.query(TraceDB)

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
async def get_trace(trace_id: str, db: Session = Depends(get_db)):
    """Get a specific trace with all details."""
    trace = db.query(TraceDB).filter(TraceDB.id == trace_id).first()

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
async def delete_trace(trace_id: str, db: Session = Depends(get_db)):
    """Delete a trace."""
    trace = db.query(TraceDB).filter(TraceDB.id == trace_id).first()

    if not trace:
        raise HTTPException(status_code=404, detail=f"Trace {trace_id} not found")

    db.delete(trace)
    db.commit()

    return None


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
