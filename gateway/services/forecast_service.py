import requests
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
from prophet import Prophet
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.stattools import adfuller
from fastapi import HTTPException

# Coordenadas agrícolas clave en Canarias
CANARIAS_COORDS = {
    "Tenerife_Norte": {"lat": 28.39, "lon": -16.52},
    "Gran_Canaria_Sur": {"lat": 27.76, "lon": -15.57},
    "La_Palma": {"lat": 28.61, "lon": -17.91},
}

# Precio base y sensibilidad por cultivo (€/kg) — proxy ISTAC/Mercamadrid
PRODUCT_PROFILES = {
    "platano_canarias": {
        "name": "Plátano de Canarias IGP",
        "base": 1.15,
        "temp_beta": 0.025,
        "rain_beta": -0.0012,
        "oil_beta": 0.008,
        "seasonal_amp": 0.12,
    },
    "aguacate_hass": {
        "name": "Aguacate Hass",
        "base": 3.40,
        "temp_beta": 0.04,
        "rain_beta": -0.002,
        "oil_beta": 0.012,
        "seasonal_amp": 0.35,
    },
    "papa_bonita": {
        "name": "Papa Bonita",
        "base": 1.80,
        "temp_beta": 0.018,
        "rain_beta": 0.0008,
        "oil_beta": 0.01,
        "seasonal_amp": 0.22,
    },
    "tomate_canario": {
        "name": "Tomate de Exportación",
        "base": 1.45,
        "temp_beta": 0.03,
        "rain_beta": -0.0015,
        "oil_beta": 0.009,
        "seasonal_amp": 0.18,
    },
}

EXOGENOUS_VARS = [
    {
        "id": "max_temp",
        "label": "Temperatura máxima",
        "unit": "°C",
        "farmer_impact": "Estrés térmico y calidad del fruto; afecta oferta y precio.",
        "course_link": "Regresor exógeno en ARIMAX / Prophet (Tema 3–4)",
    },
    {
        "id": "precipitation",
        "label": "Precipitación acumulada",
        "unit": "mm",
        "farmer_impact": "Riego natural vs. enfermedad/exceso de humedad; volumen de cosecha.",
        "course_link": "Variable exógena estacional (SARIMAX / ARIMAX)",
    },
    {
        "id": "oil_price",
        "label": "Petróleo (CL=F)",
        "unit": "USD",
        "farmer_impact": "Coste de flete, fertilizantes y plásticos; comprime margen del agricultor.",
        "course_link": "Shock externo / regresor de costes (ARIMAX)",
    },
]


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
        res = requests.get(url, timeout=15)
        res.raise_for_status()
        data = res.json()["daily"]
        return pd.DataFrame(
            {
                "ds": pd.to_datetime(data["time"]),
                "max_temp": data["temperature_2m_max"],
                "precipitation": data["precipitation_sum"],
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Error obteniendo datos climáticos de Open-Meteo: {str(e)}",
        )


def fetch_commodity_prices(start_date: str = "2023-01-01") -> pd.DataFrame:
    """Extrae precios de insumos/fletes (Petróleo Crudo) desde Yahoo Finance."""
    try:
        ticker = yf.Ticker("CL=F")
        df = ticker.history(start=start_date).reset_index()

        date_col = "Date" if "Date" in df.columns else "ds"
        df = df[[date_col, "Close"]].rename(columns={date_col: "ds", "Close": "oil_price"})
        df["ds"] = pd.to_datetime(df["ds"]).dt.tz_localize(None)
        return df
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Error obteniendo datos de YFinance: {str(e)}",
        )


def _synthetic_price(df_monthly: pd.DataFrame, product_id: str) -> pd.Series:
    profile = PRODUCT_PROFILES.get(product_id, PRODUCT_PROFILES["platano_canarias"])
    month = df_monthly["ds"].dt.month
    seasonal = profile["seasonal_amp"] * np.sin(2 * np.pi * (month - 3) / 12)
    noise = np.random.default_rng(42).normal(0, 0.08, len(df_monthly))
    return (
        profile["base"]
        + profile["temp_beta"] * (df_monthly["max_temp"] - 22)
        + profile["rain_beta"] * df_monthly["precipitation"]
        + profile["oil_beta"] * (df_monthly["oil_price"] - 70) / 10
        + seasonal
        + noise
    ).clip(lower=0.35)


def build_unified_dataset(
    island: str, product_id: str = "platano_canarias"
) -> pd.DataFrame:
    """Combina clima + petróleo y genera serie de precio del cultivo."""
    df_weather = fetch_open_meteo_weather(island)
    df_oil = fetch_commodity_prices()

    df = pd.merge(df_weather, df_oil, on="ds", how="left").bfill().ffill()

    df_monthly = (
        df.set_index("ds")
        .resample("MS")
        .agg(
            {
                "max_temp": "mean",
                "precipitation": "sum",
                "oil_price": "mean",
            }
        )
        .reset_index()
        .dropna()
    )

    df_monthly["y"] = _synthetic_price(df_monthly, product_id)
    return df_monthly


def calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    mask = y_true != 0
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    mape = float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)
    mae = float(np.mean(np.abs(y_true - y_pred)))
    return {
        "RMSE": round(rmse, 4),
        "MAPE": round(mape, 2),
        "MAE": round(mae, 4),
    }


def run_stationarity_test(series: pd.Series) -> dict:
    """Test ADF (Dickey-Fuller) — Tema 1: raíz unitaria / estacionariedad."""
    clean = series.dropna()
    if len(clean) < 12:
        return {
            "test": "ADF",
            "stationary": False,
            "adf_stat": None,
            "pvalue": None,
            "interpretation": "Serie demasiado corta para el test ADF.",
        }
    result = adfuller(clean, autolag="AIC")
    pvalue = float(result[1])
    stationary = pvalue < 0.05
    return {
        "test": "ADF (Augmented Dickey-Fuller)",
        "adf_stat": round(float(result[0]), 4),
        "pvalue": round(pvalue, 4),
        "lags_used": int(result[2]),
        "n_obs": int(result[3]),
        "critical_values": {k: round(float(v), 4) for k, v in result[4].items()},
        "stationary": stationary,
        "interpretation": (
            "Se rechaza H0 (hay raíz unitaria): la serie es estacionaria (p<0.05)."
            if stationary
            else "No se rechaza H0: posible no estacionariedad → diferenciar (I(d) en ARIMA/ARIMAX)."
        ),
    }


def run_volatility_ewma(series: pd.Series, lam: float = 0.94) -> dict:
    """Volatilidad EWMA (inspirado en Tema 7 / riesgo de mercado sobre precio)."""
    rets = series.pct_change().dropna()
    if rets.empty:
        return {"lambda": lam, "latest_vol_pct": 0.0, "series": []}
    var = float(rets.var())
    vols = []
    for r in rets.values:
        var = lam * var + (1 - lam) * float(r) ** 2
        vols.append(float(np.sqrt(var) * 100))
    return {
        "lambda": lam,
        "latest_vol_pct": round(vols[-1], 3) if vols else 0.0,
        "mean_vol_pct": round(float(np.mean(vols)), 3) if vols else 0.0,
        "series": [
            {"date": d.strftime("%Y-%m-%d"), "vol_pct": round(v, 3)}
            for d, v in zip(rets.index[-min(24, len(vols)) :], vols[-min(24, len(vols)) :])
        ],
    }


def analyze_exogenous_impact(df: pd.DataFrame, product_id: str) -> dict:
    """Correlaciones, coeficientes ARIMAX y sensibilidad (shocks) sobre el precio."""
    profile = PRODUCT_PROFILES.get(product_id, PRODUCT_PROFILES["platano_canarias"])

    corr = {
        "max_temp": float(df["y"].corr(df["max_temp"])),
        "precipitation": float(df["y"].corr(df["precipitation"])),
        "oil_price": float(df["y"].corr(df["oil_price"])),
    }

    exog_cols = ["max_temp", "precipitation", "oil_price"]
    model = SARIMAX(
        df["y"],
        exog=df[exog_cols],
        order=(1, 1, 1),
        seasonal_order=(0, 0, 0, 0),
        enforce_stationarity=False,
        enforce_invertibility=False,
    )
    fit = model.fit(disp=False)

    params = fit.params
    coefficients = []
    for col in exog_cols:
        coef = 0.0
        if col in params.index:
            coef = float(params[col])
        else:
            # statsmodels a veces nombra regressors como x1, x2…
            matches = [k for k in params.index if col in str(k)]
            if matches:
                coef = float(params[matches[0]])
        meta = next(v for v in EXOGENOUS_VARS if v["id"] == col)
        coefficients.append(
            {
                "variable": col,
                "label": meta["label"],
                "unit": meta["unit"],
                "coefficient": round(coef, 5),
                "direction": "↑ precio" if coef > 0 else "↓ precio",
                "farmer_impact": meta["farmer_impact"],
                "course_link": meta["course_link"],
                "pearson_corr": round(corr[col], 4),
            }
        )

    # Sensibilidad: shock +10% en cada exógena (ceteris paribus, último mes)
    last = df.iloc[-1]
    base_exog = last[exog_cols].astype(float)
    # Predicción un paso con exógenas actuales vs shock
    sensitivity = []
    for col in exog_cols:
        shocked = base_exog.copy()
        shocked[col] = shocked[col] * 1.10
        try:
            base_fc = fit.get_forecast(steps=1, exog=pd.DataFrame([base_exog])).predicted_mean.iloc[0]
            shock_fc = fit.get_forecast(steps=1, exog=pd.DataFrame([shocked])).predicted_mean.iloc[0]
            delta = float(shock_fc - base_fc)
            pct = float(delta / base_fc * 100) if base_fc else 0.0
        except Exception:
            delta, pct = 0.0, 0.0
        meta = next(v for v in EXOGENOUS_VARS if v["id"] == col)
        sensitivity.append(
            {
                "variable": col,
                "label": meta["label"],
                "shock": "+10%",
                "price_delta_eur": round(delta, 4),
                "price_delta_pct": round(pct, 2),
            }
        )

    return {
        "product": profile["name"],
        "product_id": product_id,
        "correlations": {k: round(v, 4) for k, v in corr.items()},
        "arimax_coefficients": coefficients,
        "sensitivity_shocks": sensitivity,
        "aic": round(float(fit.aic), 2),
        "bic": round(float(fit.bic), 2),
        "model_order": {"p": 1, "d": 1, "q": 1},
        "narrative": (
            "El precio al agricultor se modela como serie temporal con regressores "
            "exógenos (clima + coste energético). ARIMAX captura dependencia "
            "autoregresiva y el efecto contemporáneo de las variables; Prophet "
            "descompone tendencia y estacionalidad con los mismos regressores."
        ),
    }


def build_price_analysis(
    island: str,
    product_id: str,
    months: int = 6,
    price_adjustment: float = 0.0,
) -> dict:
    """Informe completo para el panel académico / demo al tribunal."""
    df = build_unified_dataset(island, product_id)
    stationarity = run_stationarity_test(df["y"])
    # También ADF sobre primera diferencia si no es estacionaria
    if not stationarity.get("stationary"):
        stationarity["diff1"] = run_stationarity_test(df["y"].diff())

    impact = analyze_exogenous_impact(df, product_id)
    volatility = run_volatility_ewma(df.set_index("ds")["y"])

    p_metrics, p_points = run_prophet_forecast(df, months, price_adjustment)
    a_metrics, a_points = run_arimax_forecast(df, months, price_adjustment)
    best = "Prophet" if p_metrics["MAPE"] < a_metrics["MAPE"] else "ARIMAX"

    history = [
        {
            "date": row["ds"].strftime("%Y-%m-%d"),
            "price": round(float(row["y"]), 3),
            "max_temp": round(float(row["max_temp"]), 2),
            "precipitation": round(float(row["precipitation"]), 2),
            "oil_price": round(float(row["oil_price"]), 2),
        }
        for _, row in df.tail(24).iterrows()
    ]

    return {
        "product_id": product_id,
        "island": island,
        "stationarity": stationarity,
        "exogenous_impact": impact,
        "volatility_ewma": volatility,
        "history": history,
        "prophet_metrics": p_metrics,
        "arimax_metrics": a_metrics,
        "best_model": best,
        "forecast_comparison": [
            {
                "date": p["date"],
                "prophet_prediction": p["predicted_value"],
                "arimax_prediction": a["predicted_value"],
                "prophet_lower": p.get("lower_bound"),
                "prophet_upper": p.get("upper_bound"),
                "arimax_lower": a.get("lower_bound"),
                "arimax_upper": a.get("upper_bound"),
            }
            for p, a in zip(p_points, a_points)
        ],
        "methodology": [
            {
                "topic": "Tema 1",
                "concept": "Estacionariedad / ADF",
                "applied": "Test Dickey-Fuller sobre el precio del cultivo antes de ARIMAX.",
            },
            {
                "topic": "Tema 3",
                "concept": "ARIMAX / SARIMAX",
                "applied": "Precio ~ ARIMA(1,1,1) + temperatura, precipitación y petróleo.",
            },
            {
                "topic": "Tema 4",
                "concept": "Prophet",
                "applied": "Tendencia + estacionalidad multiplicativa + regressores climáticos/coste.",
            },
            {
                "topic": "Tema 7",
                "concept": "Volatilidad EWMA",
                "applied": "Riesgo de precio para el agricultor (λ=0.94) sobre retornos mensuales.",
            },
        ],
    }


def run_prophet_forecast(df: pd.DataFrame, months: int, price_adjustment: float):
    """Ejecuta Prophet con regressores exógenos (clima + petróleo)."""
    model = Prophet(seasonality_mode="multiplicative")
    model.add_regressor("max_temp")
    model.add_regressor("precipitation")
    model.add_regressor("oil_price")
    model.fit(df)

    future = model.make_future_dataframe(periods=months, freq="MS")
    future = pd.merge(
        future,
        df[["ds", "max_temp", "precipitation", "oil_price"]],
        on="ds",
        how="left",
    )

    future["max_temp"] = future["max_temp"].fillna(df["max_temp"].mean())
    future["precipitation"] = future["precipitation"].fillna(df["precipitation"].mean())
    future["oil_price"] = future["oil_price"].fillna(
        df["oil_price"].iloc[-1] * (1 + (price_adjustment / 100.0))
    )

    forecast = model.predict(future)

    in_sample_pred = forecast.iloc[: len(df)]["yhat"].values
    metrics = calculate_metrics(df["y"].values, in_sample_pred)

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
    """ARIMAX/SARIMAX con temperatura, precipitación y petróleo."""
    exog_cols = ["max_temp", "precipitation", "oil_price"]
    exog = df[exog_cols]
    model = SARIMAX(
        df["y"],
        exog=exog,
        order=(1, 1, 1),
        seasonal_order=(1, 0, 0, 12),
        enforce_stationarity=False,
        enforce_invertibility=False,
    )
    fit_model = model.fit(disp=False)

    future_exog = pd.DataFrame(
        {
            "max_temp": [df["max_temp"].mean()] * months,
            "precipitation": [df["precipitation"].mean()] * months,
            "oil_price": [df["oil_price"].iloc[-1] * (1 + (price_adjustment / 100.0))]
            * months,
        }
    )

    forecast_res = fit_model.get_forecast(steps=months, exog=future_exog)
    pred_mean = forecast_res.predicted_mean
    conf_int = forecast_res.conf_int()

    in_sample_pred = fit_model.fittedvalues.values
    metrics = calculate_metrics(df["y"].values, in_sample_pred)
    metrics["AIC"] = round(float(fit_model.aic), 2)
    metrics["BIC"] = round(float(fit_model.bic), 2)

    future_dates = pd.date_range(
        start=df["ds"].iloc[-1] + pd.DateOffset(months=1),
        periods=months,
        freq="MS",
    )

    points = []
    for date, val, (lower, upper) in zip(future_dates, pred_mean, conf_int.values):
        points.append(
            {
                "date": date.strftime("%Y-%m-%d"),
                "predicted_value": round(float(val), 2),
                "lower_bound": round(float(lower), 2),
                "upper_bound": round(float(upper), 2),
            }
        )
    return metrics, points
