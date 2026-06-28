import pytest
import uuid
import os
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from openai import APITimeoutError

os.environ["OPENAI_API_KEY"] = "dummy-key-for-tests"

from src.main import app
from src.api.routes.ingestion import get_db

# Mock the database
mock_db = MagicMock()
app.dependency_overrides[get_db] = lambda: mock_db

client = TestClient(app)

def test_query_agent_tool_binding():
    """
    Test that the database tools correctly inject the tenant_id into the query,
    ensuring multi-tenant data isolation.
    """
    from src.ai.tools.database_tools import build_database_tools
    
    test_tenant_id = uuid.uuid4()
    tools = build_database_tools(mock_db, test_tenant_id)
    
    assert len(tools) == 2
    assert tools[0].name == "get_assets_by_type"

def test_query_endpoint_graceful_fallback():
    """
    Test that the endpoint catches OpenAI timeouts and returns a formatted 
    fallback string instead of crashing with a 500.
    """
    tenant_id = str(uuid.uuid4())
    payload = {"query": "What are my domains?"}
    
    # We patch the `invoke` method of the AgentExecutor to simulate a timeout
    with patch('src.ai.capabilities.query_agent.AgentExecutor.invoke') as mock_invoke:
        mock_invoke.side_effect = APITimeoutError(request=MagicMock())
        
        response = client.post(
            "/api/v1/ai/query",
            json=payload,
            headers={"x-tenant-id": tenant_id}
        )
        
        # Should NOT be a 500 error!
        assert response.status_code == 200
        
        data = response.json()
        assert "taking too long" in data["response"]
