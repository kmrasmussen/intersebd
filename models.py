from sqlalchemy import Column, Integer, String, DateTime, JSON, Float, Boolean, ForeignKey
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

    user_id = Column(String, index=True) # Store as String
    intercept_key = Column(String(200), nullable=False, unique=True, primary_key=True) # Changed type
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_valid = Column(Boolean, default=True, nullable=False)
    user_is_guest = Column(Boolean, default=False, nullable=True)

class RequestsLog(Base):
    __tablename__ = "requests_log"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    log_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    intercept_key = Column(String(200), ForeignKey("intercept_keys.intercept_key"), index=True) # Changed type
    request_method = Column(String)
    request_url = Column(String)
    request_headers = Column(JSON)
    request_body = Column(JSON, nullable=True)
    response_status_code = Column(Integer, nullable=True)
    response_headers = Column(JSON, nullable=True)
    response_body = Column(JSON, nullable=True)

    completion_request = relationship("CompletionsRequest", back_populates="request_log", uselist=False)
    key_info = relationship("InterceptKey")
class CompletionsRequest(Base):
    __tablename__ = "completions_requests"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4) # Store as UUID
    request_log_id = Column(PG_UUID(as_uuid=True), ForeignKey("requests_log.id"))
    intercept_key = Column(String(200), ForeignKey("intercept_keys.intercept_key"), index=True) # Changed type
    messages = Column(JSON) # Store messages as JSON
    messages_hash = Column(String)
    model = Column(String) # e.g., "gpt-3.5-turbo"
    response_format = Column(JSON) # e.g., "text", "json"
    response_format_hash = Column(String)

    request_log = relationship("RequestsLog", back_populates="completion_request", uselist=False)

    completion_response = relationship("CompletionResponse", back_populates="completion_request", uselist=False)
    key_info = relationship("InterceptKey")

class CompletionsRaterNotification(Base):
    __tablename__ = "completions_rater_notifications"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4) # Store as UUID
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    rater_id = Column(String)
    content = Column(Text)  # The content of the message
    intercept_key = Column(String(200), ForeignKey("intercept_keys.intercept_key")) # Changed type
    completion_response_id = Column(String, ForeignKey("completion_responses.id"))

class CompletionResponse(Base):
    __tablename__ = "completion_responses"
    
    id = Column(String, primary_key=True)  # The OpenAI/OpenRouter response ID
    completion_request_id = Column(PG_UUID(as_uuid=True), ForeignKey("completions_requests.id"))
    provider = Column(String)
    model = Column(String)
    created = Column(Integer)
    
    completion_request = relationship("CompletionsRequest", back_populates="completion_response", uselist=False)

    annotations = relationship("CompletionAnnotation", back_populates="completion_response")
    
    # Usage statistics
    prompt_tokens = Column(Integer)
    completion_tokens = Column(Integer)
    total_tokens = Column(Integer)

    # completion choice
    choice_finish_reason = Column(String)
    choice_role = Column(String)  # From message.role
    choice_content = Column(Text)  # From message.content
    
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
