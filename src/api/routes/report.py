import os
import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

from src.api.routes.ingestion import get_db
from src.database.models import Asset, AssetStatus
from src.schemas.report import ReportResponse
from src.ai.prompts.report_prompt import report_prompt

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/generate", response_model=ReportResponse)
def generate_executive_report(
    x_tenant_id: uuid.UUID = Header(...),
    db: Session = Depends(get_db)
):
    """
    AI Capability 4: Report Generation.
    Aggregates active assets and uses an LLM to generate a Markdown executive summary.
    """
    # 1. Fetch all ACTIVE assets for this tenant securely
    assets = db.query(Asset).filter(
        Asset.tenant_id == x_tenant_id,
        Asset.status == AssetStatus.ACTIVE
    ).all()

    # 2. Format the data for the LLM context
    if not assets:
        asset_data = "No active assets found in the environment."
    else:
        # We only send necessary fields to save token space
        asset_lines = []
        for a in assets:
            score = a.metadata_.get("risk_score", "Unscored") if a.metadata_ else "Unscored"
            category = a.metadata_.get("category", "Uncategorized") if a.metadata_ else "Uncategorized"
            asset_lines.append(f"- {a.type} ({a.value}) | Category: {category} | Risk Score: {score}")
        asset_data = "\n".join(asset_lines)

    # 3. Setup LLM (Using standard string output to return Markdown, not JSON)
    try:
        llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0, 
            request_timeout=30.0 # Reports can take longer to generate
        )
    except Exception as e:
        logger.error(f"LLM init error: {e}")
        raise HTTPException(status_code=500, detail="AI Service unavailable")

    # 4. Execute the chain (Prompt -> LLM -> String Parser)
    chain = report_prompt | llm | StrOutputParser()
    
    try:
        markdown_result = chain.invoke({"asset_data": asset_data})
    except Exception as e:
        logger.error(f"AI report generation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate report")

    return ReportResponse(markdown_content=markdown_result)
