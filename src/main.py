from fastapi import FastAPI
import logging

logging.basicConfig(level=logging.INFO)

from contextlib import asynccontextmanager
from src.database.session import SessionLocal, engine
from src.database.models import Tenant, Base
from sqlalchemy import text
import uuid

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure all tables are created automatically
    Base.metadata.create_all(bind=engine)
    
    # Seed the database with the default test tenant on startup
    db = SessionLocal()
    try:
        test_id = "11111111-1111-1111-1111-111111111111"
        db.execute(text("INSERT INTO tenants (id, name) VALUES (:tid, 'Test Tenant') ON CONFLICT DO NOTHING"), {"tid": test_id})
        db.commit()
    except Exception as e:
        logging.error(f"Failed to seed test tenant: {e}")
    finally:
        db.close()
    yield

app = FastAPI(
    title="DarkAtlas Asset Management System",
    description="API for ingesting and tracking internet-facing assets with AI capabilities.",
    version="1.0.0",
    lifespan=lifespan
)

from src.api.routes.ingestion import router as ingestion_router
from src.api.routes.query import router as query_router
from src.api.routes.scoring import router as scoring_router
from src.api.routes.enrichment import router as enrichment_router
from src.api.routes.report import router as report_router

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Service is running"}

app.include_router(ingestion_router, prefix="/api/v1/assets", tags=["ingestion"])
app.include_router(query_router, prefix="/api/v1/ai", tags=["ai"])
app.include_router(scoring_router, prefix="/api/v1/ai", tags=["ai"])
app.include_router(enrichment_router, prefix="/api/v1/ai", tags=["ai"])
app.include_router(report_router, prefix="/api/v1/ai/report", tags=["ai"])
