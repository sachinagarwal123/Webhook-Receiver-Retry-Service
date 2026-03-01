from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class WebhookEventCreate(BaseModel):
    event_id: str
    event_type: str
    payload: Dict[str, Any] = Field(default_factory=dict)

class WebhookEventResponse(BaseModel):
    event_id: str
    event_type: str
    payload: Dict[str, Any]
    status: str
    attempts: int
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
