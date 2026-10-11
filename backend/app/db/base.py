from typing import Any
from datetime import datetime
from pydantic import BaseModel, Field


# For MongoDB compatibility, we don't use SQLAlchemy Base
# Instead, models should inherit from MongoBase (Pydantic BaseModel)
class MongoBase(BaseModel):
    """Base model for MongoDB documents"""

    id: str | None = Field(default=None, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

    def to_mongo(self) -> dict[str, Any]:
        """Convert to MongoDB document"""
        data = self.model_dump(by_alias=True, exclude_none=True)
        if "_id" in data and data["_id"] is None:
            del data["_id"]
        return data


# For backward compatibility with existing imports
Base = MongoBase
