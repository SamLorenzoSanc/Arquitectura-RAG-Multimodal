from fastapi import APIRouter, Query
from schemas.forecast import (
    ForecastRequest,
    ForecastResponse,
    ComparisonResponse,
)
from services.forecast_service import (
    build_unified_dataset,
    run_prophet_forecast,
    run_arimax_forecast,
    fetch_open_meteo_weather,
    fetch_commodity_prices,
    build_price_analysis,
)

router = APIRouter(prefix="/forecast", tags=["Análisis de Demanda y Precios"])


@router.post("/prophet", response_model=ForecastResponse)
async def forecast_prophet(request: ForecastRequest):
    """Genera pronósticos de demanda/precio utilizando Facebook Prophet con exógenas."""
    df = build_unified_dataset(request.island, request.product_id)
    metrics, forecast_points = run_prophet_forecast(
        df, request.months, request.price_adjustment
    )

    return ForecastResponse(
        product_id=request.product_id,
        island=request.island,
        model_type="Prophet",
        metrics=metrics,
        forecast=forecast_points,
    )


@router.post("/arimax", response_model=ForecastResponse)
async def forecast_arimax(request: ForecastRequest):
    """Genera pronósticos de demanda/precio utilizando ARIMAX (Statsmodels)."""
    df = build_unified_dataset(request.island, request.product_id)
    metrics, forecast_points = run_arimax_forecast(
        df, request.months, request.price_adjustment
    )

    return ForecastResponse(
        product_id=request.product_id,
        island=request.island,
        model_type="ARIMAX",
        metrics=metrics,
        forecast=forecast_points,
    )


@router.post("/compare", response_model=ComparisonResponse)
async def compare_models(request: ForecastRequest):
    """Ejecuta Prophet y ARIMAX en paralelo, comparando su precisión (RMSE/MAPE)."""
    df = build_unified_dataset(request.island, request.product_id)

    p_metrics, p_points = run_prophet_forecast(
        df, request.months, request.price_adjustment
    )
    a_metrics, a_points = run_arimax_forecast(
        df, request.months, request.price_adjustment
    )

    best_model = "Prophet" if p_metrics["MAPE"] < a_metrics["MAPE"] else "ARIMAX"

    comparison = []
    for p, a in zip(p_points, a_points):
        comparison.append(
            {
                "date": p["date"],
                "prophet_prediction": p["predicted_value"],
                "arimax_prediction": a["predicted_value"],
            }
        )

    return ComparisonResponse(
        product_id=request.product_id,
        island=request.island,
        prophet_metrics=p_metrics,
        arimax_metrics=a_metrics,
        best_model=best_model,
        forecast_comparison=comparison,
    )


@router.post("/analysis")
async def price_driver_analysis(request: ForecastRequest):
    """
    Informe académico: estacionariedad (ADF), impacto de variables exógenas
    sobre el precio al agricultor, sensibilidad (+10%), volatilidad EWMA,
    y comparación Prophet vs ARIMAX.
    """
    return build_price_analysis(
        island=request.island,
        product_id=request.product_id,
        months=request.months,
        price_adjustment=request.price_adjustment,
    )


@router.get("/exogenous/weather")
async def get_weather_data(
    island: str = Query("Tenerife_Norte", description="Isla/Zona agrícola"),
):
    """Obtiene la serie temporal pura de datos meteorológicos para auditoría."""
    df_weather = fetch_open_meteo_weather(island)
    df_weather["ds"] = df_weather["ds"].dt.strftime("%Y-%m-%d")
    # Alias para el frontend legacy
    records = df_weather.to_dict(orient="records")
    for row in records:
        row["temperature_2m_max"] = row.get("max_temp")
        row["precipitation_sum"] = row.get("precipitation")
    return {"island": island, "data": records}


@router.get("/exogenous/commodities")
async def get_commodity_data():
    """Obtiene el historial de precios de insumos/petróleo para auditoría."""
    df_oil = fetch_commodity_prices()
    df_oil["ds"] = df_oil["ds"].dt.strftime("%Y-%m-%d")
    records = df_oil.to_dict(orient="records")
    for row in records:
        row["close"] = row.get("oil_price")
    return {"ticker": "CL=F", "data": records}
