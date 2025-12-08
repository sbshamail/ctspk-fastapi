from datetime import datetime, timezone
from typing import Optional, Any, Dict
from pydantic import BaseModel, ConfigDict, model_serializer
from sqlmodel import Field, SQLModel


class TimeStampedModel(SQLModel):
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None


class TimeStampReadModel(SQLModel):
    created_at: datetime
    updated_at: Optional[datetime] = None

    # model_config = ConfigDict(from_attributes=True)

    @model_serializer
    def serialize_model(self) -> Dict[str, Any]:
        """
        Automatically format all monetary fields to 2 decimal places
        This applies to all Read models that inherit from TimeStampReadModel
        """
        # Import here to avoid circular import
        from src.api.core.decimal_formatter import format_monetary_dict

        # Get all fields from the model
        data = {}
        for field_name in self.model_fields.keys():
            data[field_name] = getattr(self, field_name, None)

        # Format monetary fields to 2 decimals
        return format_monetary_dict(data)
