from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum, Index, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel, Field
from enum import Enum
import uuid


Base = declarative_base()


class SchemaStatus(str, Enum):
    ACTIVE = "active"
    IN_REVIEW = "in_review"
    DEPRECATED = "deprecated"


class DocumentTypeClassification(BaseModel):
    document_type: str = Field(..., description="Classified document type")
    confidence: float = Field(..., ge=0, le=1,
                              description="Classification confidence")
    country: str = Field(...,
                         description="Country of document issuance (ISO 3166-1 alpha-2 code)")
    alternative_types: List[Dict[str, float]] = Field(
        default_factory=list, description="Alternative document types with confidence scores")


class FieldModification(BaseModel):
    field_name: str = Field(...,
                            description="Name of the field being modified")
    action: str = Field(..., description="Action: 'add', 'update', 'remove'")
    old_definition: Optional[Dict[str, Any]] = Field(
        default=None, description="Previous field definition (for update/remove)")
    new_definition: Optional[Dict[str, Any]] = Field(
        default=None, description="New field definition (for add/update)")


class SchemaModificationRequest(BaseModel):
    modifications: Dict[str, Optional[Dict[str, Any]]] = Field(
        ..., description="Field modifications to apply to the schema (use null to remove fields)")
    change_description: Optional[str] = Field(
        default=None, description="Description of the changes being made")


class SchemaChange(BaseModel):
    change_type: str = Field(
        ..., description="Type of change: 'field_added', 'field_updated', 'field_removed'")
    field_name: str = Field(..., description="Name of the field that changed")
    old_value: Optional[Dict[str, Any]] = Field(
        default=None, description="Previous value (for updates/removals)")
    new_value: Optional[Dict[str, Any]] = Field(
        default=None, description="New value (for additions/updates)")


class SchemaModificationResponse(BaseModel):
    schema_id: str = Field(..., description="ID of the schema being modified")
    current_version: int = Field(...,
                                 description="Current version of the schema")
    proposed_version: int = Field(...,
                                  description="Proposed new version number")
    changes: List[SchemaChange] = Field(...,
                                        description="List of changes detected")
    original_schema: Dict[str,
                          Any] = Field(..., description="Original schema definition")
    modified_schema: Dict[str, Any] = Field(
        ..., description="Schema after applying modifications")
    change_summary: str = Field(..., description="Summary of changes made")
    modification_metadata: Dict[str, Any] = Field(
        ..., description="Metadata about the modification")


class DocumentSchema(Base):
    __tablename__ = "document_schemas"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    document_type = Column(String, nullable=False, index=True)
    country = Column(String, nullable=False, index=True)
    document_schema = Column(JSON, nullable=False)
    status = Column(SQLEnum(SchemaStatus), default=SchemaStatus.IN_REVIEW, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    version = Column(Integer, default=1, nullable=False)
    
    __table_args__ = (
        Index('idx_document_type_country', 'document_type', 'country'),
    )
