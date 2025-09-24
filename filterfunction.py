@router.get("/list", response_model=list[ProductRead])
def list(
    query_params: ListQueryParams,
):
    query_params = vars(query_params)
    searchFields = ["title", "description", "category.title"]
    return listRecords(
        query_params=query_params,
        searchFields=searchFields,
        Model=Product,
        Schema=ProductRead,
    )


def listop(
    session: Session,
    Model: type[SQLModel],
    filters: dict[str, any],
    searchFields: List[str],
    join_options: list = [],
    page: int = None,
    skip: int = 0,
    limit: int = Query(10, ge=1, le=200),
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


def listRecords(
    query_params: dict,
    searchFields: list[str],
    Model,
    join_options: list = [],
    Schema: type[SQLModel] = None,
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

        filters = {
            "searchTerm": searchTerm,
            "columnFilters": columnFilters,
            "dateRange": dateRange,
            "numberRange": numberRange,
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
        )

        if not result["data"]:
            return api_response(404, "No Result found")
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
    finally:
        session.close()


import ast
from datetime import datetime, timezone
import json
from typing import List, Optional
from fastapi import HTTPException
from sqlmodel import SQLModel, and_, or_
from sqlmodel.sql.expression import Select, SelectOfScalar

from src.api.core.utility import parse_date

# Optional Type Handling Function
from fastapi import HTTPException
from sqlalchemy.sql import sqltypes as SATypes
from sqlalchemy import cast, String


def _get_column_type(attr):
    # attr is InstrumentedAttribute of a column
    try:
        return attr.property.columns[0].type
    except Exception:
        return None  # relationship or something unexpected


def _is_string_type(t):
    return isinstance(t, (SATypes.String, SATypes.Text))


def _is_integer_type(t):
    return isinstance(t, (SATypes.Integer, SATypes.BigInteger, SATypes.SmallInteger))


def _is_numeric_type(t):
    return isinstance(
        t, (SATypes.Numeric, SATypes.Float, SATypes.DECIMAL)
    ) or _is_integer_type(t)


def _is_bool_type(t):
    return isinstance(t, SATypes.Boolean)


def _is_datetime_type(t):
    return isinstance(t, SATypes.DateTime)


def _coerce_value_for_column(col_type, value, col_name: str):
    """Coerce incoming value (possibly a string) to a Python value compatible with the column type."""
    if col_type is None:
        # Fallback – treat as string
        return value

    if _is_numeric_type(col_type):
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            v = value.strip()
            try:
                if _is_integer_type(col_type):
                    return int(v)
                else:
                    return float(v)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Column '{col_name}' expects a number; got '{value}'.",
                )
        raise HTTPException(400, f"Column '{col_name}' expects a number.")
    elif _is_bool_type(col_type):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            v = value.strip().lower()
            if v in ("true", "1", "yes"):
                return True
            if v in ("false", "0", "no"):
                return False
        raise HTTPException(400, f"Column '{col_name}' expects a boolean.")
    elif _is_datetime_type(col_type):
        if isinstance(value, str):
            # reuse your existing parse_date
            return parse_date(value)
        raise HTTPException(400, f"Column '{col_name}' expects a datetime string.")
    else:
        # string-like or other -> ensure string
        return str(value) if not isinstance(value, str) else value


def resolve_column(Model, col: str, statement):  # nested object filter
    """
    Given 'product.owner.role.title', return (attr, updated_statement).
    """
    parts = col.split(".")
    current_model = Model
    attr = None

    for i, part in enumerate(parts):  # enumerate = index + value in one go
        mapper_attr = getattr(current_model, part)

        if hasattr(mapper_attr, "property") and hasattr(mapper_attr.property, "mapper"):
            # It's a relationship -> join it
            related_model = mapper_attr.property.mapper.class_
            statement = statement.join(mapper_attr, isouter=True)
            current_model = related_model
        else:
            # It's a column
            attr = mapper_attr

    return attr, statement


def applyFilters(
    statement: SelectOfScalar,
    Model: type[SQLModel],
    searchTerm: Optional[str] = None,
    searchFields: Optional[List[str]] = None,
    columnFilters: Optional[List[List[str]]] = None,
    dateRange: Optional[List[str]] = None,
    numberRange: Optional[List[str]] = None,
    customFilters: Optional[List[List[str]]] = None,
):
    # Global search
    if searchTerm and searchFields:
        # search_filters = [
        #     getattr(Model, field).ilike(f"%{searchTerm}%") for field in searchTerms
        # ]
        search_filters = []
        for col in searchFields:
            attr, statement = resolve_column(Model, col, statement)
            search_filters.append(attr.ilike(f"%{searchTerm}%"))
        statement = statement.where(or_(*search_filters))

    # Column-specific search
    if columnFilters:
        try:
            filters = []
            parsed_terms = (
                ast.literal_eval(  # parsing work for all string, array, object, tupple
                    columnFilters
                )
            )  # in js write=JSON.parse(columnFilters);
            columnFilters = [
                tuple(sublist) for sublist in parsed_terms
            ]  # in js write=parsed_terms.map(sublist => tuple(sublist));

            for col, value in columnFilters:
                # if len(parts) > 1:
                #     # e.g., Product.owner.full_name
                #     rel_name, rel_col = parts[0], parts[1]
                #     rel_model = getattr(Model, rel_name).property.mapper.class_
                #     statement = statement.join(getattr(Model, rel_name))  # JOIN relation
                #     attr = getattr(rel_model, rel_col)
                # nested object filter
                attr, statement = resolve_column(Model, col, statement)

                # optional handling formats
                col_type = _get_column_type(attr)
                value = _coerce_value_for_column(col_type, value, col)

                if isinstance(value, str):
                    filters.append(attr.ilike(f"%{value}%"))
                else:
                    filters.append(attr == value)

            statement = statement.where(and_(*filters))
            return statement
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="columnFilters must be JSON list like [['field', 'value']]",
            )

    if customFilters:
        filters = []
        for col, value in customFilters:
            attr, statement = resolve_column(Model, col, statement)
            # optional handling formats
            col_type = _get_column_type(attr)
            value = _coerce_value_for_column(col_type, value, col)

            if isinstance(value, str):
                filters.append(attr.ilike(f"%{value}%"))
            else:
                filters.append(attr == value)

        statement = statement.where(and_(*filters))

        return statement

    # Number range
    if numberRange:
        # number_range should be like ("amount", "0", "100000")
        parsed = tuple(json.loads(numberRange))
        column_name, *values = parsed  # first element is column name, rest are values

        # Assign safely
        min_val = float(values[0]) if len(values) >= 1 and values[0] else None
        max_val = float(values[1]) if len(values) >= 2 else None

        # Ensure numeric types

        column = getattr(Model, column_name)
        if min_val is not None and max_val is not None:
            statement = statement.where(column.between(min_val, max_val))
        elif min_val is not None:
            statement = statement.where(column >= min_val)
        elif max_val is not None:
            statement = statement.where(column <= max_val)

    # Date range
    if dateRange:
        dateRangeParse = json.loads(dateRange)
        dateRange = tuple(dateRangeParse)

        column_name = dateRange[0]  # e.g. "created_at"
        column = getattr(Model, column_name)  # map to SQLModel column

        start_date = parse_date(dateRange[1])
        end_date = (
            parse_date(dateRange[2])
            if len(dateRange) > 2 and dateRange[2]
            else datetime.now(timezone.utc)
        )

        # If user didn’t specify end time, set to 23:59:59
        if (
            end_date.hour == 0
            and end_date.minute == 0
            and end_date.second == 0
            and end_date.microsecond == 0
        ):
            end_date = end_date.replace(
                hour=23, minute=59, second=59, microsecond=999999
            )

        statement = statement.where(and_(column >= start_date, column <= end_date))

    return statement
