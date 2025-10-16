import ast
from datetime import datetime, timezone
import json
from typing import List, Optional
from fastapi import HTTPException
from sqlmodel import SQLModel, and_, asc, desc, func, or_
from sqlmodel.sql.expression import Select, SelectOfScalar

from src.api.core.response import api_response
from src.api.core.utility import parse_date
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import sqltypes as SATypes


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
                raise api_response(
                    400,
                    f"Column '{col_name}' expects a number; got '{value}'.",
                )
        raise api_response(400, f"Column '{col_name}' expects a number.")
    elif _is_bool_type(col_type):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            v = value.strip().lower()
            if v in ("true", "1", "yes"):
                return True
            if v in ("false", "0", "no"):
                return False
        raise api_response(400, f"Column '{col_name}' expects a boolean.")
    elif _is_datetime_type(col_type):
        if isinstance(value, str):
            # reuse your existing parse_date
            return parse_date(value)
        raise api_response(400, f"Column '{col_name}' expects a datetime string.")
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


# ===================
# ADVANCED FILTERS ====================================
# ===================
# -------------------------
# string_array_filter
# -------------------------
def string_array_filter(statement: Select, Model, parsed_filters):
    """
    parsed_filters expected format:
    [
        ["tags", ["tag1","tag2"]],              # match any of these tags (OR)
        ["keywords", ["k1"]]                    # match any of these keywords
    ]

    For each tuple:
    - column (string) -> column must be a JSON/ARRAY column on model
    - values (list[str]) -> any match is accepted (OR)
    """
    filters = []
    for entry in parsed_filters:
        if not isinstance(entry, (list, tuple)) or len(entry) < 2:
            continue

        col_name = entry[0]
        values = entry[1]
        if not isinstance(values, (list, tuple)):
            values = [values]

        attr, statement = resolve_column(Model, col_name, statement)
        col_type = _get_column_type(attr)

        ors = []
        # ✅ Force cast to JSONB for Postgres
        for v in values:
            try:
                ors.append(sa_cast(attr, JSONB).contains([v]))
            except Exception:
                ors.append(attr.cast(SATypes.Text).ilike(f"%{v}%"))

        filters.append(or_(*ors))

    if filters:
        statement = statement.where(and_(*filters))
    return statement

    # -------------------------


# object_array_filter
# -------------------------
def object_array_filter(statement: Select, Model, parsed_filters):
    """
    parsed_filters expected examples (multiple forms supported):

    Example A (match by attribute name only):
    [
        ["attributes", ["name","color"]]
    ]

    Example B (match nested 'values' by inner key/value; multiple values ORed):
    [
        ["attributes",
            ["values", ["value", "Red"]],
            ["values", ["value", "Green"]]
        ]
    ]

    Example C (combine):
    [
        ["attributes",
        ["name","Size"],
        ["values", ["value","Small"], ["value","Medium"]]
        ]
    ]

    Logic:
    - For each top-level object-array column (e.g. attributes) we build conditions that must all hold (AND)
    - Inside a single kind of condition (e.g. multiple ["values", ["value","Red"], ["value","Green"]])
        we OR those (because any value match inside 'values' should pass)
    - Each top-level column entry becomes one AND group (you can pass multiple columns if needed)
    """
    filters = []

    for entry in parsed_filters:
        if not isinstance(entry, (list, tuple)) or len(entry) < 2:
            continue

        col_name = entry[0]
        subconds = entry[
            1:
        ]  # list of arrays like ["name","color"] or ["values", ["value","Red"], ...]

        try:
            attr, statement = resolve_column(Model, col_name, statement)
        except Exception:
            continue

        col_type = _get_column_type(attr)
        # We expect JSON column for object-array; if not JSON, try text fallback
        if not (isinstance(col_type, SATypes.JSON) or isinstance(col_type, JSONB)):
            # Non-JSON fallback: try text search (single condition)
            inner_conds = []
            for sc in subconds:
                if isinstance(sc, (list, tuple)) and len(sc) >= 2:
                    k = sc[0]
                    v = sc[1] if len(sc) == 2 else sc[1:]
                    # create simple text match fallback
                    inner_conds.append(attr.cast(SATypes.Text).ilike(f"%{v}%"))
            if inner_conds:
                filters.append(and_(*inner_conds))
            continue

        # Build JSON containment conditions
        # We'll collect per-kind lists: e.g. name_conditions, values_conditions, etc.
        kind_map: dict[str, list] = {}

        for sc in subconds:
            # Normalize each sub-condition into kind and payloads
            if not isinstance(sc, (list, tuple)) or len(sc) < 2:
                continue
            kind = sc[0]  # e.g., "name" or "values"
            payloads = sc[1:]
            # Flatten single [key, value] to tuple as payload
            if kind not in kind_map:
                kind_map[kind] = []
            # Allow payloads to be either ["value", "Red"] or ["value","Green"]
            # If payloads already a pair or many pairs, we append them
            for p in payloads:
                kind_map[kind].append(p)

        # For each kind, build a condition. For JSONB containment we construct small partial JSON objects
        per_column_conds = []
        for kind, payloads in kind_map.items():
            # payload may be e.g. ["color"] (single string) or ["value","Red"] or list of such sublists
            # We need to support:
            #   - matching top-level key: ["name", "color"]
            #   - matching nested 'values' array: ["values", ["value","Red"]]
            per_kind_ors = []
            for payload in payloads:
                # payload might be like ["value","Red"] or just "color" depending how caller structured it.
                if isinstance(payload, (list, tuple)) and len(payload) >= 2:
                    # nested key/value pair
                    key = payload[0]
                    val = payload[1]
                    # for nested structures (kind == 'values'), we should construct:
                    # attr.contains([{"values": [{"value": val}]}])
                    if kind == "values":
                        fragment = [{kind: [{key: val}]}]
                    else:
                        fragment = [{kind: {key: val}}]
                else:
                    # treat as a simple equality on kind key e.g. ["name","color"] where payload may actually be "color"
                    # If payload is direct scalar, use {kind: payload}
                    scalar_val = payload
                    fragment = [{kind: scalar_val}]
                try:
                    per_kind_ors.append(attr.contains(fragment))
                except Exception:
                    # fallback: cast to text and ilike
                    per_kind_ors.append(attr.cast(SATypes.Text).ilike(f"%{payload}%"))

            if per_kind_ors:
                # Multiple payloads for same kind → OR them (e.g., value=Red OR value=Green)
                per_column_conds.append(or_(*per_kind_ors))

        # All different kinds for the same column should be ANDed (eg name must match AND values must match)
        if per_column_conds:
            filters.append(and_(*per_column_conds))

    if filters:
        statement = statement.where(and_(*filters))
    return statement


def applyFilters(
    statement: SelectOfScalar,
    Model: type[SQLModel],
    searchTerm: Optional[str] = None,
    searchFields: Optional[List[str]] = None,
    columnFilters: Optional[List[List[str]]] = None,
    dateRange: Optional[List[str]] = None,
    numberRange: Optional[List[str]] = None,
    customFilters: Optional[List[List[str]]] = None,
    otherFilters=None,
    sort: Optional[str] = None,
    stringArrayFilters: Optional[List[List[str]]] = None,
    objectArrayFilters: Optional[List[List[str]]] = None,
):
    if otherFilters:
        # pass the current statement through the hook
        statement = otherFilters(statement, Model)
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
            parsed_terms = ast.literal_eval(columnFilters)
            columnFilters = [tuple(sublist) for sublist in parsed_terms]

            # Group filters by column name
            grouped = {}
            for col, value in columnFilters:
                grouped.setdefault(col, []).append(value)

            filters = []
            for col, values in grouped.items():
                attr, statement = resolve_column(Model, col, statement)
                col_type = _get_column_type(attr)

                coerced_values = [
                    _coerce_value_for_column(col_type, v, col) for v in values
                ]

                # If multiple values → OR
                ors = []
                for v in coerced_values:
                    if isinstance(v, str):
                        ors.append(attr.ilike(f"%{v}%"))
                    else:
                        ors.append(attr == v)
                filters.append(or_(*ors))

            statement = statement.where(and_(*filters))
            return statement

        except Exception as e:
            return api_response(
                400,
                f" {e}",
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

        # Sorting

    if sort:
        try:
            column_name, direction = json.loads(sort)
            attr, statement = resolve_column(Model, column_name, statement)
            col_type = _get_column_type(attr)

            # Case-insensitive sorting for strings
            if _is_string_type(col_type):
                order_expr = func.lower(attr)
            else:
                order_expr = attr

            if direction.lower() in ["asc", "asc"]:
                statement = statement.order_by(asc(order_expr))
            elif direction.lower() in ["desc", "desc"]:
                statement = statement.order_by(desc(order_expr))
        except Exception as e:
            return api_response(
                400,
                f"Invalid sort parameter: {e}",
            )
    if stringArrayFilters:
        string_array_raw = stringArrayFilters
        if string_array_raw:
            try:
                parsed = (
                    ast.literal_eval(string_array_raw)
                    if isinstance(string_array_raw, str)
                    else string_array_raw
                )
                statement = string_array_filter(statement, Model, parsed)
            except Exception as e:
                return api_response(400, f"stringArrayFilter parse error: {e}")
    if objectArrayFilters:
        object_array_raw = objectArrayFilters

        if object_array_raw:
            try:
                parsed = (
                    ast.literal_eval(object_array_raw)
                    if isinstance(object_array_raw, str)
                    else object_array_raw
                )
                statement = object_array_filter(statement, Model, parsed)
            except Exception as e:
                return api_response(400, f"objectArrayFilter parse error: {e}")

    return statement
