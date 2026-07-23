from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class ForecastRequest(BaseModel):
    product_id: str = Field(..., description="ID del producto agrícola", example="platano_canarias")
    island: str = Field(..., description="Isla o zona de cultivo", example="Tenerife_Norte")
    months: int = Field(default=6, ge=1, le=24, description="Horizonte temporal en meses")
    price_adjustment: float = Field(default=0.0, description="Ajuste porcentual de sensibilidad en insumos/combustibles")

class ForecastMetric(BaseModel):
    MAPE: float = Field(..., description="Mean Absolute Percentage Error")
    RMSE: float = Field(..., description="Root Mean Square Error")
    execution_time_ms: Optional[float] = Field(None, description="Tiempo de ejecución del modelo en ms")

class ForecastPoint(BaseModel):
    date: str
    predicted_value: float
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    demand_tons: Optional[int] = None

class ForecastResponse(BaseModel):
    product_id: str
    island: str
    model_type: str
    metrics: Dict[str, Any]
    forecast: List[Dict[str, Any]]

class ComparisonPoint(BaseModel):
    date: str
    prophet_prediction: float
    arimax_prediction: float

class ComparisonResponse(BaseModel):
    product_id: str
    island: str
    prophet_metrics: Dict[str, Any]
    arimax_metrics: Dict[str, Any]
    best_model: str
    forecast_comparison: List[ComparisonPoint]