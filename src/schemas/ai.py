from pydantic import BaseModel, Field

class QueryRequest(BaseModel):
    query: str = Field(..., description="The natural language query from the user")

class QueryResponse(BaseModel):
    response: str = Field(..., description="The AI's natural language answer based strictly on database data")
