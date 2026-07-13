from pydantic import BaseModel
from uuid import UUID


class DepartmentCreateRequest(BaseModel):
    organization_id: UUID
    name: str
    description: str | None = None


class DepartmentUpdateRequest(BaseModel):
    name: str
    description: str | None = None


class DepartmentMemberRequest(BaseModel):
    user_id: UUID