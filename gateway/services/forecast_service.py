import requests
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
from prophet import Prophet
from statsmodels.tsa.statespace.sarimax import SARIMAX
from fastapi import HTTPException

# Coordenadas agrícolas clave en Canarias
CANARIAS_COORDS = {
    "Tenerife_Norte": {"lat": 28.39, "lon": -16.52},
    "Gran_Canaria_Sur": {"lat": 27.76, "lon": -15.57},
    "La_Palma": {"lat": 28.61, "lon": -17.91}
}

def fetch_open_meteo_weather(island: str, start_date: str = "2023-01-01") -> pd.DataFrame:
    """Extrae datos meteorológicos históricos y de tendencia para Canarias."""
    coords = CANARIAS_COORDS.get(island, CANARIAS_COORDS["Tenerife_Norte"])
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    url = (
        f"https://archive-api.open-meteo.com/v1/archive?"
        f"latitude={coords['lat']}&longitude={coords['lon']}&"
        f"start_date={start_date}&end_date={today_str}&"
        f"daily=temperature_2m_max,precipitation_sum&timezone=Atlantic/Canary"
    )
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        data = res.json()["daily"]
        df = pd.DataFrame({
            "ds": pd.to_datetime(data["time"]),
            "max_temp": data["temperature_2m_max"],
            "precipitation": data["precipitation_sum"]
        })
        return df
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Error obteniendo datos climáticos de Open-Meteo: {str(e)}")

def fetch_commodity_prices(start_date: str = "2023-01-01") -> pd.DataFrame:
    """Extrae precios de insumos/fletes (Petróleo Crudo) desde Yahoo Finance."""
    try:
        ticker = yf.Ticker("CL=F")
        df = ticker.history(start=start_date).reset_index()
        
        # Mapeo flexible de columnas de yfinance
        date_col = "Date" if "Date" in df.columns else "ds"
        df = df[[date_col, "Close"]].rename(columns={date_col: "ds", "Close": "oil_price"})
        
        # Eliminar zona horaria para asegurar cruce limpio en pd.merge
        df["ds"] = pd.to_datetime(df["ds"]).dt.tz_localize(None)
        return df
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Error obteniendo datos de YFinance: {str(e)}")

def build_unified_dataset(island: str) -> pd.DataFrame:
    """Combina datos climáticos, insumos y genera una serie temporal unificada."""
    df_weather = fetch_open_meteo_weather(island)
    df_oil = fetch_commodity_prices()
    
    # Cruce de series temporales con relleno de fines de semana/festivos
    df = pd.merge(df_weather, df_oil, on="ds", how="left").bfill().ffill()
    
    # Agrupación mensual para reducir ruido temporal
    df_monthly = df.set_index("ds").resample("MS").agg({
        "max_temp": "mean",
        "precipitation": "sum",
        "oil_price": "mean"
    }).reset_index()

    # Generación de la variable objetivo simulada (en producción se conecta a BD/ISTAC)
    np.random.seed(42)
    base_price = 2.5
    df_monthly["y"] = (
        base_price 
        + (df_monthly["max_temp"] * 0.03) 
        + (df_monthly["oil_price"] * 0.01) 
        + np.random.normal(0, 0.1, len(df_monthly))
    )
    
    return df_monthly

def calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """Calcula las métricas de rendimiento RMSE y MAPE de forma segura."""
    mask = y_true != 0
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    mape = float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)
    return {"RMSE": round(rmse, 4), "MAPE": round(mape, 2)}

def run_prophet_forecast(df: pd.DataFrame, months: int, price_adjustment: float):
    """Ejecuta el modelo Prophet preservando exógenas históricas y proyectando las futuras."""
    model = Prophet(seasonality_mode="multiplicative")
    model.add_regressor("max_temp")
    model.add_regressor("oil_price")
    model.fit(df)

    # Construir dataframe futuro
    future = model.make_future_dataframe(periods=months, freq="MS")
    
    # Preservar datos exógenos históricos reales y rellenar únicamente la proyección futura
    future = pd.merge(future, df[["ds", "max_temp", "oil_price"]], on="ds", how="left")
    
    future["max_temp"] = future["max_temp"].fillna(df["max_temp"].mean())
    future["oil_price"] = future["oil_price"].fillna(
        df["oil_price"].iloc[-1] * (1 + (price_adjustment / 100.0))
    )

    forecast = model.predict(future)
    
    # Evaluación in-sample con datos históricos
    in_sample_pred = forecast.iloc[:len(df)]["yhat"].values
    metrics = calculate_metrics(df["y"].values, in_sample_pred)

    # Puntos proyectados hacia el futuro
    result_df = forecast.tail(months)[["ds", "yhat", "yhat_lower", "yhat_upper"]]
    points = [
        {
            "date": row["ds"].strftime("%Y-%m-%d"),
            "predicted_value": round(row["yhat"], 2),
            "lower_bound": round(row["yhat_lower"], 2),
            "upper_bound": round(row["yhat_upper"], 2),
        }
        for _, row in result_df.iterrows()
    ]
    return metrics, points

def run_arimax_forecast(df: pd.DataFrame, months: int, price_adjustment: float):
    """Ejecuta el modelo ARIMAX utilizando statsmodels."""
    exog = df[["max_temp", "oil_price"]]
    model = SARIMAX(df["y"], exog=exog, order=(1, 1, 1), seasonal_order=(1, 0, 0, 12))
    fit_model = model.fit(disp=False)

    # Construcción de variables exógenas futuras
    future_exog = pd.DataFrame({
        "max_temp": [df["max_temp"].mean()] * months,
        "oil_price": [df["oil_price"].iloc[-1] * (1 + (price_adjustment / 100.0))] * months
    })

    forecast_res = fit_model.get_forecast(steps=months, exog=future_exog)
    pred_mean = forecast_res.predicted_mean
    conf_int = forecast_res.conf_int()

    # Evaluación in-sample
    in_sample_pred = fit_model.fittedvalues.values
    metrics = calculate_metrics(df["y"].values, in_sample_pred)

    future_dates = pd.date_range(
        start=df["ds"].iloc[-1] + pd.DateOffset(months=1), 
        periods=months, 
        freq="MS"
    )
    
    points = []
    for date, val, (lower, upper) in zip(future_dates, pred_mean, conf_int.values):
        points.append({
            "date": date.strftime("%Y-%m-%d"),
            "predicted_value": round(float(val), 2),
            "lower_bound": round(float(lower), 2),
            "upper_bound": round(float(upper), 2),
        })
    return metrics, points