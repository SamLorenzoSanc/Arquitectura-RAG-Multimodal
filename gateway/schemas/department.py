from pydantic import BaseModel
from typing import Optional


class DepartmentCreateRequest(BaseModel):
    organization_id: str
    name: str
    description: Optional[str] = None


class DepartmentUpdateRequest(BaseModel):
    name: str
    description: Optional[str] = None


class AddMemberPayload(BaseModel):
    email: str
    role_id: Optional[str] = None


# Compatibilidad legacy.
class DepartmentMemberRequest(BaseModel):
    user_id: Optional[str] = None
    email: Optional[str] = None
    role_id: Optional[str] = None
