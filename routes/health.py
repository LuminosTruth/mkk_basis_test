from common.models.health import HealthResponse
from routes.base_route import public_router


@public_router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")
