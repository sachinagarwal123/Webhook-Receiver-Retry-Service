import json
from datetime import datetime
from sqlalchemy.orm import Session
from models import WebhookEvent

def process_event(event: WebhookEvent, db: Session) -> None:
    """Process webhook event based on business rules"""
    event.attempts += 1
    event.updated_at = datetime.utcnow()
    
    payload = json.loads(event.payload)
    
    if payload.get("force_success"):
        event.status = "processed"
        event.last_error = None
    elif "fail" in event.event_type.lower():
        event.status = "failed"
        event.last_error = f"Event type '{event.event_type}' contains 'fail'"
    else:
        event.status = "processed"
        event.last_error = None
    
    db.commit()
    db.refresh(event)
