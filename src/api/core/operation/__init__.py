from sqlalchemy.exc import DataError
from datetime import datetime, timezone
from fastapi import Query
from sqlalchemy import ScalarResult
from sqlmodel import Session, SQLModel, select
from typing import List, Optional
from src.lib.db_con import get_session

from src.api.core.response import api_response
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


def _exec(session, statement, Model):
    result = session.exec(statement)
    # If it's already Category objects, just return .all()
    if isinstance(result, ScalarResult):  # SQLAlchemy 2.x ScalarResult
        return result.all()
    else:
        # Fallback: try scalars (for select(Category))
        try:
            return result.scalars().all()
        except Exception:
            return result.all()


def listop(
    session: Session,
    Model: type[SQLModel],
    filters: dict[str, any],
    searchFields: List[str],
    join_options: list = [],
    page: int = None,
    skip: int = 0,
    limit: int = Query(10, ge=1, le=200),
    Statement=None,
    otherFilters=None,
    sort=None,
):

    # Compute skip based on page
    if page is not None and page > 0:
        skip = (page - 1) * limit

    # ✅ Fix: avoid boolean check on SQLAlchemy statements
    statement = Statement if Statement is not None else select(Model)

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
        otherFilters=otherFilters,
        sort=sort,
    )

    # Total count (before pagination)
    total = _exec(session, statement, Model)
    total_count = len(total)

    # Now apply pagination (skip/limit)
    paginated_stmt = statement.offset(skip).limit(limit)
    results = _exec(session, paginated_stmt, Model)

    return {"data": results, "total": total_count}


def listRecords(
    query_params: dict,
    searchFields: list[str],
    Model,
    customFilters: Optional[List[List[str]]] = None,
    join_options: list = [],
    Schema: type[SQLModel] = None,
    otherFilters=None,
    Statement=None,
):
    session = next(get_session())  # get actual Session object
    try:
        # Extract params from query dict
        dateRange = query_params.get("dateRange")
        numberRange = query_params.get("numberRange")
        searchTerm = query_params.get("searchTerm")
        columnFilters = query_params.get("columnFilters")
        page = int(query_params.get("page", 1))
        skip = int(query_params.get("skip", 0))
        limit = int(query_params.get("limit", 10))
        sort = query_params.get("sort")

        filters = {
            "searchTerm": searchTerm,
            "columnFilters": columnFilters,
            "dateRange": dateRange,
            "numberRange": numberRange,
            "customFilters": customFilters,
        }

        result = listop(
            session=session,
            Model=Model,
            searchFields=searchFields,
            filters=filters,
            skip=skip,
            page=page,
            limit=limit,
            join_options=join_options,
            otherFilters=otherFilters,
            Statement=Statement,
            sort=sort,
        )

        if not result["data"]:
            return api_response(400, "No Result found")
        # Convert each SQLModel Model instance into a ModelRead Pydantic model
        if not Schema:
            return result
        list_data = [Schema.model_validate(prod) for prod in result["data"]]
        return api_response(
            200,
            f"data found",
            list_data,
            result["total"],
        )
    except DataError as e:
        # This will catch OFFSET/limit errors and send proper API response
        return api_response(
            400,
            f"Invalid pagination values: {str(e).splitlines()[0]}",
        )
    finally:
        session.close()
