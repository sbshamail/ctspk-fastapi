from fastapi import Query, Depends
from typing import Annotated, Optional


class list_query_params:
    def __init__(
        self,
        dateRange: Optional[str] = Query(
            None, description="Example : ['created_at', '01-01-2025', '01-12-2025']"
        ),
        numberRange: Optional[str] = Query(
            None, description="Example : ['amount', 0, 100000]"
        ),
        searchTerm: str | None = Query(None, description="Search term"),
        columnFilters: Optional[str] = Query(
            None, description="Example : '[['name','car'],['description','product']]"
        ),
        page: int = Query(1, description="Page number"),
        skip: int = Query(0, description="Number of items to skip"),
        limit: int = Query(10, description="Number of items to return"),
    ):
        self.dateRange = dateRange
        self.skip = skip
        self.limit = limit
        self.searchTerm = searchTerm
        self.columnFilters = columnFilters
        self.page = page
        self.numberRange = numberRange
