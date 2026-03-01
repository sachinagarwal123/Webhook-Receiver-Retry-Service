# Webhook Receiver + Retry Service

Production-grade Python backend service for receiving webhook events with idempotency, persistence, and retry capabilities.

## Features

- ✅ Webhook event reception with idempotency
- ✅ SQLite database persistence
- ✅ Automatic event processing with retry logic
- ✅ Status filtering and pagination
- ✅ Comprehensive test coverage
- ✅ RESTful API design

## Tech Stack

- **FastAPI** - Modern web framework
- **SQLAlchemy** - ORM for database operations
- **Pydantic** - Data validation
- **Pytest** - Testing framework
- **SQLite** - Database

## Setup

1. **Create virtual environment:**
```bash
python -m venv webhook_env
source webhook_env/bin/activate  # On Windows: webhook_env\Scripts\activate
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Run the service:**
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

4. **Run tests:**
```bash
pytest test_main.py -v
```

## API Endpoints

### 1. POST /webhooks
Receive webhook events with idempotency check.

**Request:**
```json
{
  "event_id": "evt_123",
  "event_type": "user.created",
  "payload": {"user_id": 1, "name": "John"}
}
```

**Response:**
- If new: `{"message": "Event received and processed", "event_id": "evt_123", "status": "processed"}`
- If duplicate: `{"message": "Duplicate ignored", "event_id": "evt_123"}`

### 2. GET /webhooks
List events with pagination and optional status filter.

**Query Parameters:**
- `status` (optional): Filter by status (received/processed/failed)
- `limit` (default: 10, max: 100): Number of results
- `offset` (default: 0): Pagination offset

**Example:**
```bash
curl "http://localhost:8000/webhooks?status=failed&limit=10&offset=0"
```

### 3. POST /webhooks/{event_id}/retry
Retry a failed webhook event.

**Response:**
- 404 if not found
- "Event already processed" if already successful
- Processes event again if failed

**Example:**
```bash
curl -X POST "http://localhost:8000/webhooks/evt_123/retry"
```

## Processing Rules

1. **Attempts Counter**: Increments on each processing attempt
2. **Failure Logic**: Events with "fail" in event_type are marked as failed
3. **Success Logic**: All other events are marked as processed
4. **Force Success**: Set `payload.force_success = true` to force success on retry

## Database Schema

**WebhookEvent Model:**
- `event_id` (String, Primary Key) - Unique event identifier
- `event_type` (String) - Type of webhook event
- `payload` (Text/JSON) - Event payload data
- `status` (String) - received/processed/failed
- `attempts` (Integer) - Number of processing attempts
- `last_error` (Text) - Last error message if failed
- `created_at` (DateTime) - Creation timestamp
- `updated_at` (DateTime) - Last update timestamp

## Test Coverage

All required tests are implemented:
- ✅ Idempotency (no duplicates)
- ✅ Success processing
- ✅ Fail processing
- ✅ Retry success using force_success
- ✅ Additional edge cases

Run tests with coverage:
```bash
pytest test_main.py -v --cov=. --cov-report=html
```

## Project Structure

```
Webhook-Receiver-Retry-Service/
├── main.py           # FastAPI application and endpoints
├── models.py         # SQLAlchemy database models
├── schemas.py        # Pydantic schemas
├── service.py        # Business logic
├── test_main.py      # Pytest test suite
├── requirements.txt  # Python dependencies
├── .env             # Environment configuration
├── .gitignore       # Git ignore rules
└── README.md        # Documentation
```


