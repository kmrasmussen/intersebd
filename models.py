# filepath: /home/kasper/randomrepos/intercept_calls/models.py
from sqlalchemy import Column, Integer, String, DateTime, JSON, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID as PG_UUID # Use PostgreSQL UUID type
from sqlalchemy.sql import func
import uuid
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey
from sqlalchemy import Text
# UUID
from sqlalchemy.dialects.postgresql import UUID

from database import Base

class InterceptKey(Base):
    __tablename__ = "intercept_keys"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, index=True) # Store as String
    intercept_key = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_valid = Column(Boolean, default=True, nullable=False)
    user_is_guest = Column(Boolean, default=False, nullable=True)

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

    annotations = relationship("CompletionAnnotation", back_populates="completion_response")
    
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

class CompletionAnnotation(Base):
    __tablename__ = "completion_annotations"
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    completion_id = Column(String, ForeignKey("completion_responses.id"))
    rater_id = Column(String)
    reward = Column(Float)  # Rating given by the rater
    annotation_metadata = Column(JSON)  # Feedback provided by the rater
    
    # Relationship to parent completion
    completion_response = relationship("CompletionResponse", back_populates="annotations")

class OpenRouterGuestKey(Base):
    __tablename__ = "openrouter_guest_keys"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    or_key_hash = Column(String, unique=True, index=True, nullable=False)
    or_name = Column(String, nullable=False)
    or_label = Column(String, nullable=False)
    or_disabled = Column(Boolean, default=False)
    or_limit = Column(Integer, default=5)
    or_created_at = Column(DateTime(timezone=True), server_default=func.now())
    or_created_at = Column(DateTime(timezone=True), server_default=func.now())
    or_updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    or_key = Column(String, nullable=False)
    or_usage = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    user_id = Column(String, nullable=True)  # Optional user ID
