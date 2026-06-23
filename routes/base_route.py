from fastapi import APIRouter, Depends

from common.services.auth import require_api_key

public_router = APIRouter(
    prefix="/api/public/v1",
    tags=["Public API"],
)

private_router = APIRouter(
    prefix="/api/private/v1",
    tags=["Private API"],
    dependencies=[Depends(require_api_key)],
)

internal_router = APIRouter(
    prefix="/api/internal/v1",
    tags=["Internal API"],
    dependencies=[Depends(require_api_key)],
)
