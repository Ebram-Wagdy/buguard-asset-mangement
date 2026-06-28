import pytest
import uuid
import os
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

os.environ["OPENAI_API_KEY"] = "dummy-key-for-tests"

from src.main import app
from src.api.routes.ingestion import get_db
from src.schemas.scoring import RiskScoreResult

mock_db = MagicMock()
app.dependency_overrides[get_db] = lambda: mock_db

client = TestClient(app)

def test_score_asset_endpoint():
    """
    Test that the scoring endpoint correctly fetches an asset, runs the AI,
    and updates the JSONB metadata field.
    """
    app.dependency_overrides[get_db] = lambda: mock_db
    
    tenant_id = uuid.uuid4()
    asset_id = uuid.uuid4()
    
    # 1. Mock DB asset
    mock_asset = MagicMock()
    mock_asset.id = asset_id
    mock_asset.tenant_id = tenant_id
    mock_asset.type = "domain"
    mock_asset.value = "evil-phishing.com"
    mock_asset.tags = ["malicious", "phishing"]
    mock_asset.metadata_ = {}
    
    mock_db.query().filter().first.return_value = mock_asset
    
    # 2. Mock LLM result
    mock_result = RiskScoreResult(score=99, reason="Known phishing domain")
    
    with patch('langchain_core.runnables.base.RunnableSequence.invoke', return_value=mock_result):
        response = client.post(
            f"/api/v1/ai/score/{asset_id}",
            headers={"x-tenant-id": str(tenant_id)}
        )
        
        # Verify success
        assert response.status_code == 200
        data = response.json()
        assert data["score"] == 99
        assert data["reason"] == "Known phishing domain"
        # Verify database save
        assert mock_asset.metadata_["risk_score"] == 99
        assert mock_asset.metadata_["risk_reason"] == "Known phishing domain"
        mock_db.commit.assert_called()
