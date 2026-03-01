from sqlalchemy import Column, String, Integer, DateTime, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    
    event_id = Column(String(255), primary_key=True, index=True)
    event_type = Column(String(100), nullable=False)
    payload = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="received")
    attempts = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

DATABASE_URL = "sqlite:///./webhooks.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
