import pytest
import uuid
import os
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

os.environ["OPENAI_API_KEY"] = "dummy-key-for-tests"

from src.main import app
from src.api.routes.ingestion import get_db
from src.schemas.enrichment import EnrichmentResult
from src.api.routes.enrichment import enrichment_cache

mock_db = MagicMock()
app.dependency_overrides[get_db] = lambda: mock_db
client = TestClient(app)

def test_enrichment_cache():
    # Clear cache before test
    enrichment_cache.clear()

    tenant_id = uuid.uuid4()
    asset_id = uuid.uuid4()
    
    mock_asset = MagicMock()
    mock_asset.id = asset_id
    mock_asset.tenant_id = tenant_id
    mock_asset.type = "domain"
    mock_asset.value = "example.com"
    mock_asset.tags = ["prod"]
    mock_asset.metadata_ = {}
    
    mock_db.query().filter().first.return_value = mock_asset
    mock_result = EnrichmentResult(category="Web Property", confidence="High")
    
    # First call - should trigger invoke (LLM MISS)
    with patch('langchain_core.runnables.base.RunnableSequence.invoke', return_value=mock_result) as mock_invoke:
        response1 = client.post(
            f"/api/v1/ai/enrich/{asset_id}",
            headers={"x-tenant-id": str(tenant_id)}
        )
        assert response1.status_code == 200
        assert mock_invoke.call_count == 1
        
    # Second call - should HIT CACHE and NOT trigger invoke
    with patch('langchain_core.runnables.base.RunnableSequence.invoke', return_value=mock_result) as mock_invoke2:
        response2 = client.post(
            f"/api/v1/ai/enrich/{asset_id}",
            headers={"x-tenant-id": str(tenant_id)}
        )
        assert response2.status_code == 200
        assert mock_invoke2.call_count == 0 # LLM was entirely bypassed!
        
        data = response2.json()
        assert data["category"] == "Web Property"
