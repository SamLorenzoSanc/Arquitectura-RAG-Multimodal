from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SyntheticDatasetRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    knowledge_base_id: str | None = None
    document_ids: list[str] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
    department_ids: list[str] = Field(default_factory=list)
    limit: int = Field(default=100, ge=1, le=500)
    enqueue_hitl: bool = True


class DemoDatasetRequest(BaseModel):
    catalog_id: str = Field(min_length=1, max_length=80)
    name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    knowledge_base_id: str | None = None
    department_ids: list[str] = Field(default_factory=list)


class KnowledgeBaseDepartmentsUpdate(BaseModel):
    department_ids: list[str] = Field(default_factory=list)
    mode: Literal["replace", "add"] = "replace"


class DatasetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    knowledge_base_id: str | None = None
    department_ids: list[str] | None = None
    mapping: dict[str, str] | None = None


class DatasetAddColumn(BaseModel):
    column_name: str = Field(min_length=1, max_length=80)
    prompt_template: str = Field(min_length=1, max_length=4000)
    limit: int = Field(default=25, ge=1, le=100)


class DatasetImportTraces(BaseModel):
    limit: int = Field(default=50, ge=1, le=200)


class DatasetGuardrailsRequest(BaseModel):
    limit: int = Field(default=100, ge=1, le=500)
