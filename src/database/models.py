import uuid
from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

def utc_now():
    return datetime.now(timezone.utc)

class AssetStatus(str, Enum):
    ACTIVE = "active"
    STALE = "stale"
    ARCHIVED = "archived"

class Tenant(Base):
    """
    Represents an isolated customer or organization.
    All assets and relationships belong to a tenant.
    """
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    assets = relationship("Asset", back_populates="tenant", cascade="all, delete-orphan")

class Asset(Base):
    """
    Represents a discovered digital asset (IP, Domain, Certificate, etc).
    """
    __tablename__ = "assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    
    # Core identifying fields
    type = Column(String, nullable=False, index=True) # e.g., "domain", "ip_address"
    value = Column(String, nullable=False, index=True) # e.g., "api.example.com"
    status = Column(String, nullable=False, default=AssetStatus.ACTIVE, index=True)
    
    # Discovery metadata
    first_seen = Column(DateTime(timezone=True), default=utc_now)
    last_seen = Column(DateTime(timezone=True), default=utc_now)
    source = Column(String, nullable=False) # e.g., "amass", "nmap"
    
    # Flexible tags and metadata
    tags = Column(ARRAY(String), default=list)
    metadata_ = Column("metadata", JSONB, default=dict) # Underscore to avoid SQLAlchemy conflicts

    tenant = relationship("Tenant", back_populates="assets")
    
    __table_args__ = (
        UniqueConstraint('tenant_id', 'type', 'value', name='uix_tenant_type_value'),
    )
    
    # Define relationships where this asset is the source or target
    source_relations = relationship(
        "AssetRelationship", 
        foreign_keys="AssetRelationship.source_asset_id",
        back_populates="source_asset",
        cascade="all, delete-orphan"
    )
    target_relations = relationship(
        "AssetRelationship", 
        foreign_keys="AssetRelationship.target_asset_id",
        back_populates="target_asset",
        cascade="all, delete-orphan"
    )

class AssetRelationship(Base):
    """
    Represents a directed edge in the graph between two assets.
    e.g., Domain (Source) -> resolves_to -> IP Address (Target)
    """
    __tablename__ = "asset_relationships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    
    source_asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    target_asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    
    relationship_type = Column(String, nullable=False) # e.g., "resolves_to", "hosts"
    discovered_at = Column(DateTime(timezone=True), default=utc_now)

    source_asset = relationship("Asset", foreign_keys=[source_asset_id], back_populates="source_relations")
    target_asset = relationship("Asset", foreign_keys=[target_asset_id], back_populates="target_relations")
