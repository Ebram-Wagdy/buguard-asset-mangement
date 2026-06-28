from pydantic import BaseModel, Field

class ReportResponse(BaseModel):
    markdown_content: str = Field(..., description="The generated executive summary in Markdown format")
