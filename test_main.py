import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import json

from main import app
from models import Base, get_db

TEST_DATABASE_URL = "sqlite:///./test_webhooks.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="function")
def client():
    Base.metadata.create_all(bind=engine)
    yield TestClient(app)
    Base.metadata.drop_all(bind=engine)

def test_idempotency_no_duplicates(client):
    """Test that duplicate event_id is ignored"""
    payload = {
        "event_id": "evt_123",
        "event_type": "user.created",
        "payload": {"user_id": 1, "name": "John"}
    }
    
    response1 = client.post("/webhooks", json=payload)
    assert response1.status_code == 200
    assert "Event received and processed" in response1.json()["message"]
    
    response2 = client.post("/webhooks", json=payload)
    assert response2.status_code == 200
    assert response2.json()["message"] == "Duplicate ignored"
    
    events = client.get("/webhooks").json()
    assert len(events) == 1

def test_success_processing(client):
    """Test successful event processing"""
    payload = {
        "event_id": "evt_success_1",
        "event_type": "order.completed",
        "payload": {"order_id": 100}
    }
    
    response = client.post("/webhooks", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "processed"
    
    events = client.get("/webhooks?status=processed").json()
    assert len(events) == 1
    assert events[0]["event_id"] == "evt_success_1"
    assert events[0]["status"] == "processed"
    assert events[0]["attempts"] == 1
    assert events[0]["last_error"] is None

def test_fail_processing(client):
    """Test failed event processing when event_type contains 'fail'"""
    payload = {
        "event_id": "evt_fail_1",
        "event_type": "payment.failed",
        "payload": {"payment_id": 200}
    }
    
    response = client.post("/webhooks", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    
    events = client.get("/webhooks?status=failed").json()
    assert len(events) == 1
    assert events[0]["event_id"] == "evt_fail_1"
    assert events[0]["status"] == "failed"
    assert events[0]["attempts"] == 1
    assert events[0]["last_error"] is not None
    assert "fail" in events[0]["last_error"].lower()

def test_retry_success_using_force_success(client):
    """Test retry with force_success flag"""
    payload = {
        "event_id": "evt_retry_1",
        "event_type": "transaction.failed",
        "payload": {"transaction_id": 300}
    }
    
    response = client.post("/webhooks", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    
    events = client.get("/webhooks?status=failed").json()
    assert len(events) == 1
    assert events[0]["attempts"] == 1
    
    retry_response = client.post("/webhooks/evt_retry_1/retry")
    assert retry_response.status_code == 200
    assert retry_response.json()["status"] == "failed"
    
    events_after_retry = client.get("/webhooks").json()
    assert events_after_retry[0]["attempts"] == 2
    
    db = next(override_get_db())
    from models import WebhookEvent
    event = db.query(WebhookEvent).filter(WebhookEvent.event_id == "evt_retry_1").first()
    event.payload = json.dumps({"transaction_id": 300, "force_success": True})
    db.commit()
    
    retry_response2 = client.post("/webhooks/evt_retry_1/retry")
    assert retry_response2.status_code == 200
    assert retry_response2.json()["status"] == "processed"
    
    final_events = client.get("/webhooks?status=processed").json()
    assert len(final_events) == 1
    assert final_events[0]["attempts"] == 3
    assert final_events[0]["status"] == "processed"

def test_retry_already_processed(client):
    """Test retry on already processed event"""
    payload = {
        "event_id": "evt_processed",
        "event_type": "user.updated",
        "payload": {"user_id": 400}
    }
    
    response = client.post("/webhooks", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "processed"
    
    retry_response = client.post("/webhooks/evt_processed/retry")
    assert retry_response.status_code == 200
    assert retry_response.json()["message"] == "Event already processed"

def test_retry_not_found(client):
    """Test retry on non-existent event"""
    retry_response = client.post("/webhooks/non_existent/retry")
    assert retry_response.status_code == 404
    assert retry_response.json()["detail"] == "Event not found"

def test_list_webhooks_pagination(client):
    """Test pagination in list webhooks"""
    for i in range(15):
        client.post("/webhooks", json={
            "event_id": f"evt_{i}",
            "event_type": "test.event",
            "payload": {"index": i}
        })
    
    response1 = client.get("/webhooks?limit=10&offset=0")
    assert len(response1.json()) == 10
    
    response2 = client.get("/webhooks?limit=10&offset=10")
    assert len(response2.json()) == 5

def test_list_webhooks_status_filter(client):
    """Test status filtering in list webhooks"""
    client.post("/webhooks", json={
        "event_id": "evt_success",
        "event_type": "order.created",
        "payload": {}
    })
    
    client.post("/webhooks", json={
        "event_id": "evt_fail",
        "event_type": "order.failed",
        "payload": {}
    })
    
    processed = client.get("/webhooks?status=processed").json()
    failed = client.get("/webhooks?status=failed").json()
    
    assert len(processed) == 1
    assert len(failed) == 1
    assert processed[0]["status"] == "processed"
    assert failed[0]["status"] == "failed"
