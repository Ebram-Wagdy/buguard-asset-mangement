from pydantic import BaseModel, Field

class RiskScoreResult(BaseModel):
    score: int = Field(..., ge=0, le=100, description="The risk score from 0 to 100. 0 is completely safe, 100 is critical danger.")
    reason: str = Field(..., description="A short, one-sentence explanation of why this score was assigned.")
