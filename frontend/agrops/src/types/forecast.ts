// src/types/forecast.ts

export interface ForecastRequest {
    product_id: string;
    island: string;
    months: number;
    price_adjustment: number;
}

export interface ForecastMetric {
    MAPE: number;
    RMSE: number;
    execution_time_ms?: number;
}

export interface ForecastPoint {
    date: string;
    predicted_value: number;
    lower_bound?: number;
    upper_bound?: number;
    demand_tons?: number;
}

export interface ForecastResponse {
    product_id: string;
    island: string;
    model_type: "Prophet" | "ARIMAX";
    metrics: ForecastMetric;
    forecast: ForecastPoint[];
}

export interface ComparisonPoint {
    date: string;
    prophet_prediction: number;
    arimax_prediction: number;
}

export interface ComparisonResponse {
    product_id: string;
    island: string;
    prophet_metrics: ForecastMetric;
    arimax_metrics: ForecastMetric;
    best_model: string;
    forecast_comparison: ComparisonPoint[];
}

export interface WeatherRecord {
    ds: string;
    temperature_2m_max?: number;
    precipitation_sum?: number;
    [key: string]: any;
}

export default interface CommodityRecord {
    ds: string;
    close?: number;
    [key: string]: any;
}