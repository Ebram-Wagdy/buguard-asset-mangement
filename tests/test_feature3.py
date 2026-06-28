import pytest
import uuid
from pydantic import ValidationError
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from src.schemas.asset import AssetCreate
from src.api.routes.ingestion import router
from fastapi import FastAPI

# --- Unit Tests: Pydantic Schemas ---

def test_asset_create_valid():
    data = {
        "type": "domain",
        "value": "example.com",
        "source": "nmap",
        "tags": [" PROD ", "internal"],
        "metadata": {"port": 443}
    }
    asset = AssetCreate.model_validate(data)
    assert asset.type == "domain"
    # Tags should be normalized: lowercase and stripped
    assert asset.tags == ["prod", "internal"]
    assert asset.metadata_ == {"port": 443}

def test_asset_create_invalid_ip():
    data = {
        "type": "ip_address",
        "value": "999.999.999.999", # Invalid IP
        "source": "nmap"
    }
    with pytest.raises(ValidationError):
        AssetCreate.model_validate(data)

# --- Integration/Unit Tests: FastAPI Route ---

app = FastAPI()
app.include_router(router, prefix="/api/v1/assets")

def test_ingestion_endpoint_graceful_degradation():
    """
    Test that the endpoint catches bad records and still processes good ones
    without returning a 500 server error.
    """
    # Mock the DB dependency
    mock_db = MagicMock()
    app.dependency_overrides[router.dependencies[0].dependency if router.dependencies else next(iter(app.router.routes)).endpoint] = lambda: mock_db
    
    # Wait, overriding dependencies robustly for tests
    from src.api.routes.ingestion import get_db
    app.dependency_overrides[get_db] = lambda: mock_db

    client = TestClient(app)
    
    tenant_id = str(uuid.uuid4())
    payload = [
        {
            "type": "domain",
            "value": "valid.com",
            "source": "amass"
        },
        {
            "type": "ip_address",
            "value": "invalid_ip_string", # This will fail validation
            "source": "nmap"
        }
    ]
    
    response = client.post(
        "/api/v1/assets/import",
        json=payload,
        headers={"x-tenant-id": tenant_id}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["successful_count"] == 1
    assert len(data["failed_records"]) == 1
    assert data["failed_records"][0]["record"]["value"] == "invalid_ip_string"
    
    # Assert the DB execute was called for the 1 valid record
    mock_db.execute.assert_called_once()
    mock_db.commit.assert_called_once()
