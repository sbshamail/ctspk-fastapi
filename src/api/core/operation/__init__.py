from datetime import datetime, timezone
from fastapi import Query
from sqlmodel import Session, SQLModel, select
from typing import List

from src.api.core.operation.list_operation_helper import (
    applyFilters,
)


# Update only the fields that are provided in the request
# customFields = ["phone", "firstname", "lastname", "email"]
def updateOp(
    instance,
    request,
    session,
    customFields=None,
):
    if customFields:
        for field in customFields:
            if hasattr(request, field):
                value = getattr(request, field)
                if value is not None:
                    setattr(instance, field, value)
    else:
        data = request.model_dump(exclude_unset=True)
        for key, value in data.items():
            setattr(instance, key, value)
    if hasattr(instance, "updated_at"):
        instance.updated_at = datetime.now(timezone.utc)
    session.add(instance)

    return instance


def listop(
    session: Session,
    Model: type[SQLModel],
    filters: dict[str, any],
    searchFields: List[str],
    join_options: list = [],
    page: int = None,
    skip: int = 0,
    limit: int = Query(10, ge=1, le=100),
):

    # Compute skip based on page
    if page is not None:
        skip = (page - 1) * limit

    # Start building base statement (without limit/offset for total count)
    statement = select(Model)

    # Apply JOINs (like selectinload)
    if join_options:
        for option in join_options:
            statement = statement.options(option)

    searchTerm = filters.get("searchTerm")
    columnFilters = filters.get("columnFilters")
    dateRange = filters.get("dateRange")
    numberRange = filters.get("numberRange")
    customFilters = filters.get("customFilters")
    # Apply Filters
    statement = applyFilters(
        statement,
        Model=Model,
        searchTerm=searchTerm,
        searchFields=searchFields,
        columnFilters=columnFilters,
        dateRange=dateRange,
        numberRange=numberRange,
        customFilters=customFilters,
    )

    # Total count (before pagination)
    total = session.exec(statement).all()
    total_count = len(total)

    # Now apply pagination (skip/limit)
    paginated_stmt = statement.offset(skip).limit(limit)

    results = session.exec(paginated_stmt).all()

    return {"data": results, "total": total_count}
