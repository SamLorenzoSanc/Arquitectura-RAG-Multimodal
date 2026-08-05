from __future__ import annotations

import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

import httpx

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
)

from sqlalchemy.ext.asyncio import AsyncSession

from services.database import get_db
from routes.auth import get_current_user
from models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/map",
    tags=["Map"],
)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
AEMET_API_KEY = os.getenv("AEMET_API_KEY")
AEMET_URL = "https://opendata.aemet.es/opendata/api"
SENTINEL_CLIENT_ID = os.getenv("SENTINEL_CLIENT_ID")
SENTINEL_CLIENT_SECRET = os.getenv("SENTINEL_CLIENT_SECRET")
SENTINEL_TOKEN_URL = "https://services.sentinel-hub.com/oauth/token"
SENTINEL_PROCESS_URL = "https://services.sentinel-hub.com/api/v1/process"
HTTP_TIMEOUT = 30

CACHE: dict[str, dict] = {}
CACHE_MINUTES = 10


def cache_valid(key: str):

    if key not in CACHE:

        return False

    expires = CACHE[key]["expires"]

    return expires > datetime.utcnow()


def get_cache(key: str):

    return CACHE[key]["value"]


def save_cache(key: str, value: Any):

    CACHE[key] = {
        "value": value,
        "expires": datetime.utcnow() + timedelta(minutes=CACHE_MINUTES),
    }


async def get_json(
    url: str,
    *,
    params=None,
    headers=None,
):

    async with httpx.AsyncClient(
        timeout=HTTP_TIMEOUT,
    ) as client:

        response = await client.get(
            url,
            params=params,
            headers=headers,
        )

        response.raise_for_status()

        return response.json()


CANARIAS = {
    "lat": 28.2916,
    "lon": -16.6291,
}


async def sentinel_token():

    cache_key = "sentinel_token"

    if cache_valid(cache_key):

        return get_cache(cache_key)

    async with httpx.AsyncClient() as client:

        response = await client.post(
            SENTINEL_TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": SENTINEL_CLIENT_ID,
                "client_secret": SENTINEL_CLIENT_SECRET,
            },
        )

        response.raise_for_status()

        token = response.json()["access_token"]

        save_cache(
            cache_key,
            token,
        )

        return token


async def openmeteo_weather():

    cache_key = "openmeteo"

    if cache_valid(cache_key):

        return get_cache(cache_key)

    params = {
        "latitude": CANARIAS["lat"],
        "longitude": CANARIAS["lon"],
        "current": [
            "temperature_2m",
            "relative_humidity_2m",
            "apparent_temperature",
            "precipitation",
            "rain",
            "wind_speed_10m",
            "wind_direction_10m",
            "cloud_cover",
        ],
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "sunrise",
            "sunset",
        ],
        "timezone": "Europe/Madrid",
    }

    data = await get_json(
        OPEN_METEO_URL,
        params=params,
    )

    result = {
        "provider": "Open-Meteo",
        "timestamp": datetime.utcnow(),
        "current": data["current"],
        "daily": data["daily"],
    }

    save_cache(
        cache_key,
        result,
    )

    return result


# ============================================================
# AEMET
# ============================================================


async def aemet_weather():

    if AEMET_API_KEY is None:

        return {
            "provider": "AEMET",
            "enabled": False,
            "message": "API KEY not configured",
        }

    cache_key = "aemet"

    if cache_valid(cache_key):

        return get_cache(cache_key)

    endpoint = f"{AEMET_URL}/prediccion/especifica/municipio/diaria/" "38038"

    headers = {
        "api_key": AEMET_API_KEY,
    }

    response = await get_json(
        endpoint,
        headers=headers,
    )

    data_url = response["datos"]

    prediction = await get_json(
        data_url,
    )

    result = {
        "provider": "AEMET",
        "prediction": prediction,
    }

    save_cache(
        cache_key,
        result,
    )

    return result


# ============================================================
# SENTINEL HUB
# ============================================================


async def sentinel_ndvi():

    if SENTINEL_CLIENT_ID is None:

        return {
            "provider": "Sentinel",
            "enabled": False,
        }

    cache_key = "sentinel"

    if cache_valid(cache_key):

        return get_cache(cache_key)

    token = await sentinel_token()

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    body = {
        "input": {
            "bounds": {
                "bbox": [
                    -18.4,
                    27.5,
                    -13.1,
                    29.6,
                ]
            },
            "data": [
                {
                    "type": "sentinel-2-l2a",
                }
            ],
        },
        "output": {
            "width": 512,
            "height": 512,
        },
        "evalscript": """

//VERSION=3

function setup(){
    return{
        input:["B04","B08"],
        output:{bands:1}
    }

}

function evaluatePixel(sample){
    let ndvi=(sample.B08-sample.B04)/(sample.B08+sample.B04);
    return [ndvi];
}

""",
    }

    async with httpx.AsyncClient(
        timeout=120,
    ) as client:
        response = await client.post(
            SENTINEL_PROCESS_URL,
            headers=headers,
            json=body,
        )

    result = {
        "provider": "Sentinel-2",
        "status": response.status_code,
        "image": response.content,
    }

    save_cache(
        cache_key,
        result,
    )

    return result


async def map_dashboard():

    weather, aemet, sentinel = await asyncio.gather(
        openmeteo_weather(),
        aemet_weather(),
        sentinel_ndvi(),
    )

    return {
        "timestamp": datetime.utcnow(),
        "weather": weather,
        "forecast": aemet,
        "satellite": sentinel,
    }


@router.get("/dashboard")
async def map_dashboard():

    weather, aemet, sentinel = await asyncio.gather(
        openmeteo_weather(),
        aemet_weather(),
        sentinel_ndvi(),
    )

    return {
        "timestamp": datetime.utcnow(),
        "weather": weather,
        "forecast": aemet,
        "satellite": sentinel,
    }


@router.get("/weather")
async def weather(
    current_user: User = Depends(get_current_user),
):

    return await openmeteo_weather()


@router.get("/forecast")
async def forecast(
    current_user: User = Depends(get_current_user),
):
    return await aemet_weather()


@router.get("/sentinel")
async def sentinel(
    current_user: User = Depends(get_current_user),
):

    return await sentinel_ndvi()


@router.get("/canarias")
async def canarias(
    current_user: User = Depends(get_current_user),
):

    dashboard = await map_dashboard()

    return {
        "name": "Canarias",
        "center": {
            "lat": CANARIAS["lat"],
            "lon": CANARIAS["lon"],
            "zoom": 8,
        },
        "layers": {
            "weather": dashboard["weather"],
            "forecast": dashboard["forecast"],
            "satellite": dashboard["satellite"],
        },
    }


@router.get("/cultivos")
async def get_cultivos_endpoint(current_user: User = Depends(get_current_user)):

    return [
        {
            "id": "1",
            "nombre": "Parcela Norte",
            "cultivo": "Plátano",
            "isla": "Tenerife",
            "lat": 28.45,
            "lon": -16.25,
            "temperatura": 23,
            "humedad": 70,
            "lluvia": 2,
            "viento": 15,
            "ndvi": 0.78,
        },
        {
            "id": "2",
            "nombre": "Finca La Palma",
            "cultivo": "Aguacate",
            "isla": "La Palma",
            "lat": 28.68,
            "lon": -17.76,
            "temperatura": 21,
            "humedad": 76,
            "lluvia": 4,
            "viento": 12,
            "ndvi": 0.65,
        },
        {
            "id": "3",
            "nombre": "Campo Sur",
            "cultivo": "Tomate",
            "isla": "Gran Canaria",
            "lat": 27.95,
            "lon": -15.6,
            "temperatura": 25,
            "humedad": 60,
            "lluvia": 0,
            "viento": 20,
            "ndvi": 0.52,
        },
    ]


@router.get("/health")
async def health():

    checks = await asyncio.gather(
        openmeteo_weather(),
        aemet_weather(),
        sentinel_ndvi(),
        return_exceptions=True,
    )

    providers = [
        "OpenMeteo",
        "AEMET",
        "Sentinel",
    ]

    result = {}

    for provider, value in zip(
        providers,
        checks,
    ):

        result[provider] = {
            "status": "OK" if not isinstance(value, Exception) else "ERROR"
        }

    return result
