import pytest
import uuid
import os
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

os.environ["OPENAI_API_KEY"] = "dummy-key-for-tests"

from src.main import app
from src.api.routes.ingestion import get_db

mock_db = MagicMock()
app.dependency_overrides[get_db] = lambda: mock_db
client = TestClient(app)

def test_report_generation_endpoint():
    """
    Tests that the report generation endpoint securely pulls assets 
    and returns a formatted Markdown string from the LLM.
    """
    tenant_id = uuid.uuid4()
    
    # Mock DB assets
    mock_asset = MagicMock()
    mock_asset.type = "domain"
    mock_asset.value = "test.com"
    mock_asset.metadata_ = {"risk_score": 90, "category": "Web Property"}
    
    mock_db.query().filter().all.return_value = [mock_asset]
    
    # Mock LLM chain invoke to return a markdown string
    expected_markdown = "# Executive Summary\n\nCritical risk found on test.com (Score 90)."
    
    with patch('langchain_core.runnables.base.RunnableSequence.invoke', return_value=expected_markdown):
        response = client.get(
            "/api/v1/ai/report/generate",
            headers={"x-tenant-id": str(tenant_id)}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "markdown_content" in data
        assert "Executive Summary" in data["markdown_content"]
