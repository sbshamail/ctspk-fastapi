from typing import Any, Optional, Union
import json
from decimal import Decimal

from fastapi import HTTPException
from fastapi.encoders import (
    jsonable_encoder,
)
from fastapi.responses import (
    JSONResponse,
)


def format_monetary_values(obj, path_key=None):
    """Recursively format monetary fields in the response"""
    MONETARY_FIELDS = {
        'price', 'sale_price', 'purchase_price', 'min_price', 'max_price',
        'unit_price', 'unit_purchase_price', 'amount', 'paid_total',
        'cancelled_amount', 'total_amount', 'order_amount', 'refund_amount',
        'approved_amount', 'total_cost', 'net_amount', 'balance_after',
        'discount', 'coupon_discount', 'item_discount', 'discount_amount',
        'sales_tax', 'delivery_fee', 'item_tax', 'tax_amount',
        'shipping_cost', 'restocking_fee', 'subtotal', 'total',
        'admin_commission_amount', 'admin_commission', 'shop_earning',
        'current_stock_value'
    }

    if isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            if key in MONETARY_FIELDS and isinstance(value, (int, float, Decimal)) and value is not None:
                # Return as string with 2 decimal places
                result[key] = f"{float(value):.2f}"
            elif isinstance(value, (dict, list)):
                result[key] = format_monetary_values(value, key)
            else:
                result[key] = value
        return result
    elif isinstance(obj, list):
        return [format_monetary_values(item, path_key) for item in obj]
    elif isinstance(obj, (int, float, Decimal)) and path_key in MONETARY_FIELDS:
        return f"{float(obj):.2f}"
    else:
        return obj


def api_response(
    code: int,
    detail: str,
    data: Optional[Union[dict, list]] = None,
    total: Optional[int] = None,
):

    # Convert data to JSON-able format
    encoded_data = jsonable_encoder(data)

    # Format monetary fields to 2 decimal places (as strings)
    formatted_data = format_monetary_values(encoded_data)

    content = {
        "success": (1 if code < 300 else 0),
        "detail": detail,
        "data": formatted_data,
    }

    if total is not None:
        content["total"] = total

    # Raise error if code >= 400
    if code >= 400:
        raise HTTPException(
            status_code=code,
            detail=detail,
        )
        # return JSONResponse(status_code=code, content=content)

    return JSONResponse(
        status_code=code,
        content=content,
    )


def raiseExceptions(*conditions: tuple[Any, int | None, str | None, bool | None]):
    """
    Example usage:
        resp = raiseExceptions(
            (user, 404, "User not found"),
            (is_active, 403, "User is disabled",True),
        )
        if resp: return resp
    """
    for cond in conditions:
        # Unpack with defaults
        condition = cond[0] if len(cond) > 0 else False  # Condition
        code = cond[1] if len(cond) > 1 else 400
        detail = cond[2] if len(cond) > 2 else "error"
        isCond = cond[3] if len(cond) > 3 else False

        if isCond and condition:
            if condition:  # Fail if condition is True
                return api_response(code, detail)
        elif not condition and not isCond:  # Fail if condition is False
            return api_response(code, detail)
    return None  # everything passed
