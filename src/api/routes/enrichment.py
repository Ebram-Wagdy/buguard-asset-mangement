import os
import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from langchain_openai import ChatOpenAI

from src.api.routes.ingestion import get_db
from src.database.models import Asset
from src.schemas.enrichment import EnrichmentResult
from src.ai.prompts.enrichment_prompt import enrichment_prompt

router = APIRouter()
logger = logging.getLogger(__name__)

# LLM Caching: Constitution Rule 4
# A simple in-memory cache dictionary to save money on repetitive LLM calls.
# Key: (asset_type, asset_value), Value: EnrichmentResult
enrichment_cache = {}

@router.post("/enrich/{asset_id}", response_model=EnrichmentResult)
def enrich_asset(
    asset_id: uuid.UUID,
    x_tenant_id: uuid.UUID = Header(..., description="Tenant ID"),
    db: Session = Depends(get_db)
):
    asset = db.query(Asset).filter(Asset.id == asset_id, Asset.tenant_id == x_tenant_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    cache_key = (asset.type, asset.value)

    # 1. Check Cache
    if cache_key in enrichment_cache:
        result = enrichment_cache[cache_key]
        logger.info(f"Cache HIT for {cache_key}")
    else:
        logger.info(f"Cache MISS for {cache_key}. Calling LLM...")
        # 2. Setup LLM
        try:
            llm = ChatOpenAI(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                temperature=0,
                request_timeout=15.0
            ).with_structured_output(EnrichmentResult)
        except Exception as e:
            logger.error(f"LLM init error: {e}")
            raise HTTPException(status_code=500, detail="AI Service unavailable")

        # 3. Execute
        chain = enrichment_prompt | llm
        try:
            result: EnrichmentResult = chain.invoke({
                "type": asset.type,
                "value": asset.value,
                "tags": ", ".join(asset.tags) if asset.tags else "None"
            })
        except Exception as e:
            logger.error(f"AI enrichment failed: {e}")
            raise HTTPException(status_code=500, detail="AI enrichment execution failed")
            
        # 4. Save to Cache
        enrichment_cache[cache_key] = result

    # 5. Save to Database
    if asset.metadata_ is None:
        asset.metadata_ = {}
        
    if isinstance(result, dict):
        category = result.get('category', 'Unknown')
        confidence = result.get('confidence', 0)
        rationale = result.get('rationale', '')
    else:
        category = result.category
        confidence = result.confidence
        rationale = result.rationale
        
    asset.metadata_['enrichment_category'] = category
    asset.metadata_['enrichment_confidence'] = confidence
    asset.metadata_['enrichment_rationale'] = rationale
    flag_modified(asset, "metadata_")
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save enrichment")

    return result
