import os
import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from langchain_openai import ChatOpenAI

from src.api.routes.ingestion import get_db
from src.database.models import Asset
from src.schemas.scoring import RiskScoreResult
from src.ai.prompts.scoring_prompt import scoring_prompt

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/score/{asset_id}", response_model=RiskScoreResult)
def score_asset(
    asset_id: uuid.UUID,
    x_tenant_id: uuid.UUID = Header(..., description="The tenant ID owning the asset"),
    db: Session = Depends(get_db)
):
    """
    AI Capability 2: Risk Scoring.
    Analyzes an asset using an LLM and saves a deterministic 0-100 score to its metadata.
    """
    # 1. Fetch asset with strict tenant isolation
    asset = db.query(Asset).filter(Asset.id == asset_id, Asset.tenant_id == x_tenant_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    # 2. Initialize LLM with strict JSON schema enforcement
    try:
        llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0, # Deterministic evaluation
            request_timeout=15.0
        ).with_structured_output(RiskScoreResult)
    except Exception as e:
        logger.error(f"Failed to initialize scoring LLM: {e}")
        raise HTTPException(status_code=500, detail="AI Service unavailable")

    # 3. Execute the AI chain
    chain = scoring_prompt | llm
    
    try:
        result: RiskScoreResult = chain.invoke({
            "type": asset.type,
            "value": asset.value,
            "tags": ", ".join(asset.tags) if asset.tags else "None"
        })
    except Exception as e:
        logger.error(f"AI scoring failed for asset {asset_id}: {e}")
        raise HTTPException(status_code=500, detail="AI scoring execution failed")

    # 4. Save the result back to the database
    if asset.metadata_ is None:
        asset.metadata_ = {}
        
    if isinstance(result, dict):
        asset.metadata_['risk_score'] = result.get('score', 0)
        asset.metadata_['risk_reason'] = result.get('reason', '')
    else:
        asset.metadata_['risk_score'] = result.score
        asset.metadata_['risk_reason'] = result.reason
    flag_modified(asset, "metadata_") # Tell SQLAlchemy the JSONB field changed
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database save failed after scoring: {e}")
        raise HTTPException(status_code=500, detail="Failed to save score")

    return result
