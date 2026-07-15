from pydantic import BaseModel
from typing import Optional


class DepartmentCreateRequest(BaseModel):
    organization_id: str
    name: str
    description: Optional[str] = None


class DepartmentUpdateRequest(BaseModel):
    name: str
    description: Optional[str] = None


class DepartmentMemberRequest(BaseModel):
    user_id: str