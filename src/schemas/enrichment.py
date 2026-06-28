from pydantic import BaseModel, Field

class EnrichmentResult(BaseModel):
    category: str = Field(..., description="The high-level category of the asset (e.g., Cloud Infrastructure, Web Property, Network Device, Code Repository)")
    confidence: str = Field(..., description="Confidence level of this categorization: High, Medium, or Low")
