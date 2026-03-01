from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import json
from datetime import datetime

from models import WebhookEvent, get_db, init_db
from schemas import WebhookEventCreate, WebhookEventResponse
from service import process_event

app = FastAPI(title="Webhook Receiver & Retry Service")

@app.on_event("startup")
def startup_event():
    init_db()

@app.post("/webhooks", response_model=dict, status_code=200)
def receive_webhook(webhook: WebhookEventCreate, db: Session = Depends(get_db)):
    """Receive webhook event with idempotency check"""
    existing = db.query(WebhookEvent).filter(WebhookEvent.event_id == webhook.event_id).first()
    
    if existing:
        return {"message": "Duplicate ignored", "event_id": webhook.event_id}
    
    event = WebhookEvent(
        event_id=webhook.event_id,
        event_type=webhook.event_type,
        payload=json.dumps(webhook.payload),
        status="received",
        attempts=0
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    
    process_event(event, db)
    
    return {"message": "Event received and processed", "event_id": event.event_id, "status": event.status}

@app.get("/webhooks", response_model=List[WebhookEventResponse])
def list_webhooks(
    status: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """List webhook events with pagination and optional status filter"""
    query = db.query(WebhookEvent)
    
    if status:
        query = query.filter(WebhookEvent.status == status)
    
    events = query.offset(offset).limit(limit).all()
    
    return [
        WebhookEventResponse(
            event_id=e.event_id,
            event_type=e.event_type,
            payload=json.loads(e.payload),
            status=e.status,
            attempts=e.attempts,
            last_error=e.last_error,
            created_at=e.created_at,
            updated_at=e.updated_at
        )
        for e in events
    ]

@app.post("/webhooks/{event_id}/retry", response_model=dict)
def retry_webhook(event_id: str, db: Session = Depends(get_db)):
    """Retry failed webhook event"""
    event = db.query(WebhookEvent).filter(WebhookEvent.event_id == event_id).first()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    if event.status == "processed":
        return {"message": "Event already processed", "event_id": event_id}
    
    if event.status == "failed":
        process_event(event, db)
        return {"message": "Event retried", "event_id": event_id, "status": event.status}
    
    return {"message": "Event cannot be retried", "event_id": event_id, "status": event.status}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
