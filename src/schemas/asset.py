import re
import ipaddress
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict

class AssetCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')

    type: str = Field(..., description="The type of the asset (e.g., domain, ip_address)")
    value: str = Field(..., description="The actual value of the asset")
    source: str = Field(..., description="The tool or source that discovered this asset")
    tags: List[str] = Field(default_factory=list)
    metadata_: Dict[str, Any] = Field(default_factory=dict, alias="metadata")

    @field_validator('tags')
    def normalize_tags(cls, v):
        """Lowercase and strip whitespace from all tags."""
        if not v:
            return []
        return [tag.strip().lower() for tag in v if tag.strip()]

    @field_validator('value')
    def validate_value(cls, v, info):
        """Basic validation based on the type."""
        v = v.strip()
        asset_type = info.data.get('type')
        if asset_type == 'ip_address':
            try:
                ipaddress.ip_address(v)
            except ValueError:
                raise ValueError(f"Invalid IP address format: {v}")
        return v

class FailedRecord(BaseModel):
    record: Dict[str, Any]
    error: str

class BulkImportResponse(BaseModel):
    successful_count: int
    failed_records: List[FailedRecord]
