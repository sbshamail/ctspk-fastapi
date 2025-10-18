from typing import Annotated, Any, Dict, Optional

from fastapi import Depends, Query
from sqlmodel import Session

from src.api.core.dependencies.query_params import list_query_params
from src.lib.db_con import get_session
from src.api.core.security import (
    is_authenticated,
    require_permission,
    require_signin,
    require_admin,
)


GetSession = Annotated[Session, Depends(get_session)]

requireSignin = Annotated[dict, Depends(require_signin)]
requireAdmin = Annotated[dict, Depends(require_admin)]
isAuthenticated = Annotated[dict | None, Depends(is_authenticated)]
ListQueryParams = Annotated[dict, Depends(list_query_params)]


def requirePermission(*permissions: str):
    return Depends(require_permission(*permissions))
