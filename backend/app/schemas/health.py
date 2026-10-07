from pydantic import BaseModel, Field


class HealthCheck(BaseModel):
    name: str
    status: str
    detail: str | None = None


class HealthResponse(BaseModel):
    status: str = Field(description="ok or degraded")
    checks: list[HealthCheck]
