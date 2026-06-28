import pytest
from src.database.models import Tenant, Asset, AssetRelationship, Base

def test_database_schema_metadata():
    """
    Test that the SQLAlchemy models are properly configured.
    Because we don't have a live Postgres DB available in the test runner, 
    we test the SQLAlchemy metadata directly.
    """
    tables = Base.metadata.tables
    
    # 1. Verify tables exist
    assert "tenants" in tables
    assert "assets" in tables
    assert "asset_relationships" in tables
    
    # 2. Verify Asset columns
    asset_table = tables["assets"]
    assert "id" in asset_table.columns
    assert "tenant_id" in asset_table.columns
    assert "type" in asset_table.columns
    assert "value" in asset_table.columns
    assert "status" in asset_table.columns
    assert "metadata" in asset_table.columns
    
    # 3. Verify Foreign Keys
    # Asset.tenant_id -> Tenant.id
    tenant_fk = list(asset_table.c.tenant_id.foreign_keys)[0]
    assert tenant_fk.target_fullname == "tenants.id"
    
    # 4. Verify AssetRelationship edge table logic
    relationship_table = tables["asset_relationships"]
    source_fk = list(relationship_table.c.source_asset_id.foreign_keys)[0]
    assert source_fk.target_fullname == "assets.id"
    
    target_fk = list(relationship_table.c.target_asset_id.foreign_keys)[0]
    assert target_fk.target_fullname == "assets.id"
