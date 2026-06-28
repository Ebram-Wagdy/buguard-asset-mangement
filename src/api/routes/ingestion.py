from fastapi import APIRouter, Header, HTTPException, Depends
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
import uuid
import logging

from src.schemas.asset import AssetCreate, BulkImportResponse, FailedRecord
from src.database.models import Asset, AssetStatus, utc_now

logger = logging.getLogger(__name__)
router = APIRouter()

from src.database.session import SessionLocal

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/import", response_model=BulkImportResponse)
def import_assets(
    payload: List[dict], # Accept raw dicts so we can catch validation errors per-item
    x_tenant_id: uuid.UUID = Header(..., description="The ID of the tenant owning the assets"),
    db: Session = Depends(get_db)
):
    """
    Idempotent bulk import endpoint.
    Upserts valid assets into the database. Malformed records are gracefully skipped and logged.
    """
    successful_count = 0
    failed_records = []
    valid_assets = []

    # 1. Graceful Degradation: Validate each record individually
    for item in payload:
        try:
            validated_asset = AssetCreate.model_validate(item)
            valid_assets.append(validated_asset)
        except Exception as e:
            failed_records.append(FailedRecord(record=item, error=str(e)))

    if not valid_assets:
        return BulkImportResponse(successful_count=0, failed_records=failed_records)

    # 2. Strict Idempotency & Lifecycle Reversion via PostgreSQL UPSERT
    # Prepare data for insertion
    insert_values = []
    for asset in valid_assets:
        insert_values.append({
            "id": uuid.uuid4(), # Generate new UUID for the insert path
            "tenant_id": x_tenant_id,
            "type": asset.type,
            "value": asset.value,
            "status": AssetStatus.ACTIVE,
            "first_seen": utc_now(),
            "last_seen": utc_now(),
            "source": asset.source,
            "tags": asset.tags,
            "metadata_": asset.metadata_
        })

    try:
        stmt = insert(Asset).values(insert_values)
        
        # ON CONFLICT DO UPDATE logic
        update_dict = {
            # Update last_seen
            "last_seen": utc_now(),
            # Constitution: Revert stale/archived to active
            "status": AssetStatus.ACTIVE,
            # Merge tags
            "tags": stmt.excluded.tags,
            "metadata": stmt.excluded.metadata
        }
        
        # We conflict on the natural composite key
        stmt = stmt.on_conflict_do_update(
            index_elements=['tenant_id', 'type', 'value'],
            set_=update_dict
        )
        
        db.execute(stmt)
        db.commit()
        successful_count = len(valid_assets)
        
    except Exception as e:
        db.rollback()
        logger.error(f"Database error during upsert: {e}")
        raise HTTPException(status_code=500, detail="Database transaction failed")

    return BulkImportResponse(
        successful_count=successful_count,
        failed_records=failed_records
    )
