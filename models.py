from sqlalchemy import Column, Integer, String, DateTime, JSON, Float, Boolean, ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID as PG_UUID # Use PostgreSQL UUID type
from sqlalchemy.sql import func
import uuid
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey
from sqlalchemy import Text
# UUID
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import UniqueConstraint
from database import Base

annotation_target_annotation_link = Table(
    "annotation_target_annotation_link",
    Base.metadata,
    Column("annotation_target_id", PG_UUID(as_uuid=True), ForeignKey("annotation_targets.id"), primary_key=True),
    Column("completion_annotation_id", PG_UUID(as_uuid=True), ForeignKey("completion_annotations.id"), primary_key=True),
)

class AnnotationTarget(Base):
    """
    An intermediate table representing something that can be annotated.
    Both CompletionResponse and CompletionAlternative will have a one-to-one
    relationship with an entry in this table.
    """
    __tablename__ = "annotation_targets"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Relationships back to the specific types (optional but useful for querying)
    completion_response = relationship(
        "CompletionResponse",
        back_populates="annotation_target",
        uselist=False,
        cascade="all, delete-orphan"
    )
    completion_alternative = relationship(
        "CompletionAlternative",
        back_populates="annotation_target",
        uselist=False,
        cascade="all, delete-orphan"
    )

    annotations = relationship(
        "CompletionAnnotation",
        secondary=annotation_target_annotation_link, # Use the association table
        back_populates="annotation_targets" # Matches relationship name in CompletionAnnotation
        # cascade options on the relationship itself might not be needed here,
        # rely on database FK constraints or handle deletes in application logic
    )

class InterceptKey(Base):
    __tablename__ = "intercept_keys"

    user_id = Column(String, index=True) 
    intercept_key = Column(String(200), nullable=False, unique=True, primary_key=True) 
    viewing_id = Column(String, unique=True, index=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_valid = Column(Boolean, default=True, nullable=False)
    user_is_guest = Column(Boolean, default=False, nullable=True)

class RequestsLog(Base):
    __tablename__ = "requests_log"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    log_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    intercept_key = Column(String(200), ForeignKey("intercept_keys.intercept_key"), index=True) 
    request_method = Column(String)
    request_url = Column(String)
    request_headers = Column(JSON)
    request_body = Column(JSON, nullable=True)
    response_status_code = Column(Integer, nullable=True)
    response_headers = Column(JSON, nullable=True)
    response_body = Column(JSON, nullable=True)

    completion_request = relationship("CompletionsRequest", back_populates="request_log", uselist=False)
    key_info = relationship("InterceptKey")

class CompletionAlternative(Base):
    __tablename__ = "completion_alternatives"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    original_completion_request_id = Column(PG_UUID(as_uuid=True), ForeignKey("completions_requests.id"))
    intercept_key = Column(String(200), ForeignKey("intercept_keys.intercept_key"), index=True)
    alternative_content = Column(Text, nullable=False)
    rater_id = Column(String, nullable=True, index=True) 
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    annotation_target_id = Column(PG_UUID(as_uuid=True), ForeignKey("annotation_targets.id"), unique=True, nullable=False)
    annotation_target = relationship("AnnotationTarget", back_populates="completion_alternative")

    original_completion_request = relationship("CompletionsRequest", back_populates="alternatives", uselist=False)
    submitted_via_intercept_key = relationship("InterceptKey")

    __table_args__ = (UniqueConstraint("original_completion_request_id", "alternative_content", name='uq_alternative_content_per_request'),)

class CompletionsRequest(Base):
    __tablename__ = "completions_requests"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_log_id = Column(PG_UUID(as_uuid=True), ForeignKey("requests_log.id"))
    intercept_key = Column(String(200), ForeignKey("intercept_keys.intercept_key"), index=True)
    messages = Column(JSON)
    messages_hash = Column(String)
    model = Column(String)
    response_format = Column(JSON)
    response_format_hash = Column(String)

    request_log = relationship("RequestsLog", back_populates="completion_request", uselist=False)

    alternatives = relationship(
        "CompletionAlternative",
        back_populates="original_completion_request",
        cascade="all, delete-orphan"
    )

    completion_response = relationship("CompletionResponse", back_populates="completion_request", uselist=False)
    key_info = relationship("InterceptKey")

class CompletionsRaterNotification(Base):
    __tablename__ = "completions_rater_notifications"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4) 
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    rater_id = Column(String)
    content = Column(Text) 
    intercept_key = Column(String(200), ForeignKey("intercept_keys.intercept_key")) 
    completion_response_id = Column(String, ForeignKey("completion_responses.id"))

class CompletionResponse(Base):
    __tablename__ = "completion_responses"
    
    id = Column(String, primary_key=True)
    completion_request_id = Column(PG_UUID(as_uuid=True), ForeignKey("completions_requests.id"), unique=True)
    provider = Column(String)
    model = Column(String)
    created = Column(Integer)
    
    annotation_target_id = Column(PG_UUID(as_uuid=True), ForeignKey("annotation_targets.id"), unique=True, nullable=False)
    annotation_target = relationship("AnnotationTarget", back_populates="completion_response")

    completion_request = relationship("CompletionsRequest", back_populates="completion_response", uselist=False)

    # Usage statistics
    prompt_tokens = Column(Integer)
    completion_tokens = Column(Integer)
    total_tokens = Column(Integer)

    # completion choice
    choice_finish_reason = Column(String)
    choice_role = Column(String) 
    choice_content = Column(Text)
    
class CompletionAnnotation(Base):
    __tablename__ = "completion_annotations"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    rater_id = Column(String)
    reward = Column(Float) 
    annotation_metadata = Column(JSON)

    annotation_targets = relationship(
        "AnnotationTarget",
        secondary=annotation_target_annotation_link, # Use the association table
        back_populates="annotations" # Matches relationship name in AnnotationTarget
    )
    

class OpenRouterGuestKey(Base):
    __tablename__ = "openrouter_guest_keys"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    or_key_hash = Column(String, unique=True, index=True, nullable=False)
    or_name = Column(String, nullable=False)
    or_label = Column(String, nullable=False)
    or_disabled = Column(Boolean, default=False)
    or_limit = Column(Integer, default=5)
    or_created_at = Column(DateTime(timezone=True), server_default=func.now())
    or_updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    or_key = Column(String, nullable=False)
    or_usage = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    user_id = Column(String, nullable=True)

class AgentWidget(Base):
    __tablename__ = "agent_widgets"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cors_origin = Column(String, nullable=False)
    tools = Column(JSON, nullable=False)
    user_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    n_calls = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)