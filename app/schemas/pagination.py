from typing import Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field, conint

# Define a generic type for the items
T = TypeVar("T")


class PaginationParams(BaseModel):
    """Parameters for pagination."""
    
    skip: int = Field(0, ge=0, description="Number of records to skip")
    limit: conint(ge=1, le=100) = Field(20, description="Maximum number of records to return")


class PaginatedResponse(BaseModel, Generic[T]):
    """Response model for paginated results."""
    
    items: List[T] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    skip: int = Field(..., description="Number of records skipped")
    limit: int = Field(..., description="Maximum number of records returned")
    
    @classmethod
    def create(cls, items: List[T], total: int, skip: int, limit: int):
        """Create a paginated response."""
        return cls(
            items=items,
            total=total,
            skip=skip,
            limit=limit,
        ) 