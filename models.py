# filepath: /home/kasper/randomrepos/intercept_calls/models.py
from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID # Use PostgreSQL UUID type
from sqlalchemy.sql import func
import uuid
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey
from sqlalchemy import Text
# UUID
from sqlalchemy.dialects.postgresql import UUID

from database import Base

class RequestsLog(Base):
    __tablename__ = "requests_log"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4) # Store as UUI
    log_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    intercept_key = Column(PG_UUID(as_uuid=True), index=True) # Store as UUID
    request_method = Column(String)
    request_url = Column(String)
    request_headers = Column(JSON) # Store headers as JSON
    request_body = Column(JSON, nullable=True) # Store body as JSON, allow null
    response_status_code = Column(Integer, nullable=True)
    response_headers = Column(JSON, nullable=True)
    response_body = Column(JSON, nullable=True)

    completion = relationship("CompletionResponse", back_populates="request_log", uselist=False)
    completion_request = relationship("CompletionsRequest", back_populates="request_log", uselist=False)

class CompletionsRequest(Base):
    __tablename__ = "completions_requests"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4) # Store as UUID
    request_log_id = Column(PG_UUID(as_uuid=True), ForeignKey("requests_log.id"))
    messages = Column(JSON) # Store messages as JSON
    messages_hash = Column(String)
    model = Column(String) # e.g., "gpt-3.5-turbo"
    response_format = Column(JSON) # e.g., "text", "json"
    response_format_hash = Column(String)

    request_log = relationship("RequestsLog", back_populates="completion_request", uselist=False)

class CompletionsRaterNotification(Base):
    __tablename__ = "completions_rater_notifications"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4) # Store as UUID
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    rater_id = Column(String)
    content = Column(Text)  # The content of the message
    intercept_key = Column(PG_UUID(as_uuid=True))
    completion_response_id = Column(String, ForeignKey("completion_responses.id"))

class CompletionResponse(Base):
    __tablename__ = "completion_responses"
    
    id = Column(String, primary_key=True)  # The OpenAI/OpenRouter response ID
    request_log_id = Column(UUID, ForeignKey("requests_log.id"))
    provider = Column(String)
    model = Column(String)
    created = Column(Integer)
    
    # Relationship to the original request log
    request_log = relationship("RequestsLog", back_populates="completion")
    
    # Relationship to message choices
    choices = relationship("CompletionChoice", back_populates="completion")
    
    # Usage statistics
    prompt_tokens = Column(Integer)
    completion_tokens = Column(Integer)
    total_tokens = Column(Integer)

class CompletionChoice(Base):
    __tablename__ = "completion_choices"
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    completion_id = Column(String, ForeignKey("completion_responses.id"))
    index = Column(Integer)
    finish_reason = Column(String)
    role = Column(String)  # From message.role
    content = Column(Text)  # From message.content
    
    # Relationship to parent completion
    completion = relationship("CompletionResponse", back_populates="choices")