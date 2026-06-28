import uuid
from fastapi import APIRouter, Header, Depends
from sqlalchemy.orm import Session

from src.schemas.ai import QueryRequest, QueryResponse
from src.ai.capabilities.query_agent import execute_query
from src.api.routes.ingestion import get_db

router = APIRouter()

@router.post("/query", response_model=QueryResponse)
def handle_query(
    request: QueryRequest,
    x_tenant_id: uuid.UUID = Header(..., description="The ID of the tenant making the query"),
    db: Session = Depends(get_db)
):
    """
    Allows a user to ask natural language questions about their assets.
    """
    answer = execute_query(request.query, db, x_tenant_id)
    return QueryResponse(response=answer)
