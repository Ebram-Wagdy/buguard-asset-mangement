import uuid
from sqlalchemy.orm import Session
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from src.database.models import Asset, AssetStatus

# Input Schemas for Tools
class AssetSearchInput(BaseModel):
    asset_type: str = Field(description="The type of asset to search for (e.g., 'domain', 'ip_address').")

class AssetStatusInput(BaseModel):
    status: AssetStatus = Field(description="The status to search for (e.g., 'active', 'stale', 'archived').")

class AssetTagInput(BaseModel):
    tag: str = Field(description="The tag to search for (e.g., 'external', 'prod', 'database').")

def build_database_tools(db: Session, tenant_id: uuid.UUID) -> list[StructuredTool]:
    """
    Factory function to create LangChain tools tightly bound to a specific tenant and database session.
    This strictly enforces data isolation at the tool layer.
    """
    
    def get_assets_by_type(asset_type: str) -> str:
        """Search the database for assets of a specific type."""
        assets = db.query(Asset).filter(
            Asset.tenant_id == tenant_id, 
            Asset.type == asset_type
        ).limit(100).all() # Simple limit to prevent context window explosion
        
        if not assets:
            return f"No assets found of type '{asset_type}'."
            
        details = [f"Value: {a.value}, Status: {a.status}, Tags: {a.tags}" for a in assets]
        return f"Found {len(assets)} '{asset_type}' assets:\n" + "\n".join(details)

    def get_assets_by_status(status: AssetStatus) -> str:
        """Search the database for assets with a specific status."""
        assets = db.query(Asset).filter(
            Asset.tenant_id == tenant_id, 
            Asset.status == status
        ).limit(100).all()
        
        if not assets:
            return f"No assets found with status '{status}'."
            
        details = [f"Type: {a.type}, Value: {a.value}, Tags: {a.tags}" for a in assets]
        return f"Found {len(assets)} assets with status '{status}':\n" + "\n".join(details)

    def get_assets_by_tag(tag: str) -> str:
        """Search the database for assets with a specific tag."""
        assets = db.query(Asset).filter(
            Asset.tenant_id == tenant_id, 
            Asset.tags.any(tag)
        ).limit(100).all()
        
        if not assets:
            return f"No assets found with tag '{tag}'."
            
        details = [f"Type: {a.type}, Value: {a.value}, Status: {a.status}" for a in assets]
        return f"Found {len(assets)} assets with tag '{tag}':\n" + "\n".join(details)

    # Wrap them as LangChain Structured Tools
    return [
        StructuredTool.from_function(
            func=get_assets_by_type,
            name="get_assets_by_type",
            description="Use this tool to find all assets belonging to a specific category or type (like domains, IPs, certificates).",
            args_schema=AssetSearchInput
        ),
        StructuredTool.from_function(
            func=get_assets_by_status,
            name="get_assets_by_status",
            description="Use this tool to find all assets that have a specific status (active, stale, archived).",
            args_schema=AssetStatusInput
        ),
        StructuredTool.from_function(
            func=get_assets_by_tag,
            name="get_assets_by_tag",
            description="Use this tool to find all assets that have a specific tag (like external, internal, prod, dev).",
            args_schema=AssetTagInput
        )
    ]
