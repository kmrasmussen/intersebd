from sqlalchemy import Column, Integer, String, DateTime, JSON, Float, Boolean, ForeignKey, Table, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID # Use PostgreSQL UUID type
from sqlalchemy.sql import func
import uuid
from sqlalchemy.orm import relationship
from sqlalchemy import UniqueConstraint
from database import Base

annotation_target_annotation_link = Table(
    "annotation_target_annotation_link",
    Base.metadata,
    Column("annotation_target_id", PG_UUID(as_uuid=True), ForeignKey("annotation_targets.id"), primary_key=True),
    Column("completion_annotation_id", PG_UUID(as_uuid=True), ForeignKey("completion_annotations.id"), primary_key=True),
)

class User(Base):
    __tablename__ = "users"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=True) # Nullable for guests
    google_id = Column(String, unique=True, index=True, nullable=True) # Nullable until Google login
    auth_provider = Column(String, nullable=True, index=True) # e.g., 'google' or None for guests
    name = Column(String, nullable=True) # Nullable for guests
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship to projects created by this user
    created_projects = relationship("CompletionProject", back_populates="creator")

    project_memberships = relationship("ProjectMembership", back_populates="user")
    projects = relationship(
        "CompletionProject",
        secondary="project_memberships",
        back_populates="members",
        viewonly=True
    )

class CompletionProject(Base):
    __tablename__ = "completion_projects"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String) # Consider uniqueness constraint if needed
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)

    creator_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    creator = relationship("User", back_populates="created_projects")

    project_memberships = relationship("ProjectMembership", back_populates="project", cascade="all, delete-orphan")
    members = relationship(
        "User",
        secondary="project_memberships",
        back_populates="projects",
        viewonly=True
    )

    completion_requests = relationship("CompletionsRequest", back_populates="project")

    call_keys = relationship("CompletionProjectCallKeys", back_populates="project", cascade="all, delete-orphan")

class ProjectMembership(Base):
    __tablename__ = 'project_memberships'
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True)
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey('completion_projects.id'), primary_key=True)
    role = Column(String, nullable=False, default='viewer', server_default='viewer')
    added_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="project_memberships")
    project = relationship("CompletionProject", back_populates="project_memberships")

class CompletionProjectCallKeys(Base):
    __tablename__ = "completion_project_call_keys"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)

    project_id = Column(PG_UUID(as_uuid=True), ForeignKey("completion_projects.id"), nullable=False, index=True)

    project = relationship("CompletionProject", back_populates="call_keys")

    # Add relationship to OpenRouterGuestKey (one-to-one)
    openrouter_guest_key = relationship(
        "OpenRouterGuestKey",
        back_populates="completion_project_call_key",
        uselist=False, # Indicates a one-to-one relationship from this side
        cascade="all, delete-orphan" # Optional: Delete linked OR key if this key is deleted
    )

class AnnotationTarget(Base):
    """
    An intermediate table representing something that can be annotated.
    Both CompletionResponse and CompletionAlternative will have a one-to-one
    relationship with an entry in this table.
    """
    __tablename__ = "annotation_targets"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

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
        secondary=annotation_target_annotation_link,
        back_populates="annotation_targets"
    )

class CompletionAlternative(Base):
    __tablename__ = "completion_alternatives"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    original_completion_request_id = Column(PG_UUID(as_uuid=True), ForeignKey("completions_requests.id"))
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey("completion_projects.id"), index=True, nullable=False)
    alternative_content = Column(Text, nullable=False)
    rater_id = Column(String, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    annotation_target_id = Column(PG_UUID(as_uuid=True), ForeignKey("annotation_targets.id"), unique=True, nullable=False)
    annotation_target = relationship("AnnotationTarget", back_populates="completion_alternative")

    original_completion_request = relationship("CompletionsRequest", back_populates="alternatives")
    project = relationship("CompletionProject")
    
    __table_args__ = (UniqueConstraint("original_completion_request_id", "alternative_content", name='uq_alternative_content_per_request'),)

class CompletionsRequest(Base):
    __tablename__ = "completions_requests"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey("completion_projects.id"), index=True, nullable=False)
    messages = Column(JSON)
    messages_hash = Column(String)
    model = Column(String)
    response_format = Column(JSON)
    response_format_hash = Column(String)

    project = relationship("CompletionProject", back_populates="completion_requests")

    alternatives = relationship(
        "CompletionAlternative",
        back_populates="original_completion_request",
        cascade="all, delete-orphan"
    )

    completion_response = relationship(
        "CompletionResponse",
        back_populates="completion_request",
        uselist=False,
        cascade="all, delete-orphan"
    )

class CompletionsRaterNotification(Base):
    __tablename__ = "completions_rater_notifications"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4) 
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    rater_id = Column(String)
    content = Column(Text) 
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

    prompt_tokens = Column(Integer)
    completion_tokens = Column(Integer)
    total_tokens = Column(Integer)

    choice_finish_reason = Column(String)
    choice_role = Column(String) 
    choice_content = Column(Text)
    
class CompletionAnnotation(Base):
    __tablename__ = "completion_annotations"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey('users.id', ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    reward = Column(Float)
    annotation_metadata = Column(JSON)

    user = relationship("User")

    annotation_targets = relationship(
        "AnnotationTarget",
        secondary=annotation_target_annotation_link,
        back_populates="annotations"
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

    # Foreign key to link to a specific project call key
    completion_project_call_key_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("completion_project_call_keys.id", ondelete="SET NULL"), # Optional: Set FK to NULL if call key is deleted
        nullable=True,
        unique=True # Enforce one-to-one at DB level
    )
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey('users.id', ondelete="SET NULL"), nullable=True)

    user = relationship("User") # Relationship to User

    # Add relationship back to CompletionProjectCallKeys
    completion_project_call_key = relationship(
        "CompletionProjectCallKeys",
        back_populates="openrouter_guest_key"
    )

class AgentWidget(Base):
    __tablename__ = "agent_widgets"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cors_origin = Column(String, nullable=False)
    tools = Column(JSON, nullable=False)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey('users.id', ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    n_calls = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    user = relationship("User")