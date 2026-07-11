from pydantic import BaseModel


class ModelInfo(BaseModel):
    name: str
    provider: str
    context_window: int
    embedding_model: str


class ModelSelection(BaseModel):
    model_name: str


class ModelSelectionResponse(BaseModel):
    active_model: str