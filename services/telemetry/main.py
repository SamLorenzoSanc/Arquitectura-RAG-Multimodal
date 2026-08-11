"""Telemetry service: MQTT → Postgres (riego / reefer).

Topics:
  finca/{crop_id}/riego   → caudal, humedad_suelo, valvula
  reefer/{container_id}/temp → temperatura, humedad
"""

from __future__ import annotations

import asyncio
import json
import os
import threading
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse, urlunparse
from uuid import uuid4

import asyncpg
import paho.mqtt.client as mqtt
from fastapi import FastAPI
from pydantic import BaseModel

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@postgres:5432/agrops",
)
MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPICS = os.getenv(
    "MQTT_TOPICS",
    "finca/+/riego,reefer/+/temp",
).split(",")

app = FastAPI(title="AgroPS Telemetry Service", version="1.0.0")
_pool: asyncpg.Pool | None = None
_loop: asyncio.AbstractEventLoop | None = None
_latest: dict[str, Any] = {}


def _asyncpg_dsn(url: str) -> str:
    u = url.replace("postgresql+asyncpg://", "postgresql://")
    parsed = urlparse(u)
    return urlunparse(parsed._replace(scheme="postgresql", query=""))


class ReadingOut(BaseModel):
    topic: str
    entity_type: str
    entity_id: str
    metric: str
    value: float
    unit: str | None = None
    payload: dict[str, Any] = {}
    recorded_at: str


def _parse_topic(topic: str) -> tuple[str, str, str]:
    parts = topic.strip("/").split("/")
    if len(parts) >= 3 and parts[0] == "finca":
        return "finca", parts[1], parts[2]
    if len(parts) >= 3 and parts[0] == "reefer":
        return "reefer", parts[1], parts[2]
    return "unknown", "unknown", parts[-1] if parts else "metric"


async def _ensure_table(conn: asyncpg.Connection) -> None:
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sensor_readings (
            id varchar(36) PRIMARY KEY,
            topic text NOT NULL,
            entity_type varchar(32) NOT NULL,
            entity_id varchar(64) NOT NULL,
            metric varchar(64) NOT NULL,
            value double precision NOT NULL,
            unit varchar(32),
            payload jsonb,
            recorded_at timestamptz NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_sensor_readings_entity
          ON sensor_readings(entity_type, entity_id, recorded_at DESC);
        """
    )


async def _store_reading(
    topic: str,
    payload: dict[str, Any],
) -> None:
    if not _pool:
        return
    entity_type, entity_id, metric = _parse_topic(topic)
    value = payload.get("value")
    if value is None:
        for key in ("temp", "temperature", "caudal", "humedad", "humidity"):
            if key in payload:
                value = payload[key]
                metric = key
                break
    if value is None:
        return
    unit = payload.get("unit")
    rid = str(uuid4())
    recorded_at = datetime.now(timezone.utc)
    async with _pool.acquire() as conn:
        await _ensure_table(conn)
        await conn.execute(
            """
            INSERT INTO sensor_readings
              (id, topic, entity_type, entity_id, metric, value, unit, payload, recorded_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8::jsonb,$9)
            """,
            rid,
            topic,
            entity_type,
            entity_id,
            metric,
            float(value),
            unit,
            json.dumps(payload),
            recorded_at,
        )
    key = f"{entity_type}:{entity_id}:{metric}"
    _latest[key] = {
        "topic": topic,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "metric": metric,
        "value": float(value),
        "unit": unit,
        "payload": payload,
        "recorded_at": recorded_at.isoformat(),
    }


def _on_message(_client, _userdata, msg: mqtt.MQTTMessage) -> None:
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
    except Exception:
        payload = {"value": float(msg.payload.decode("utf-8", errors="ignore") or 0)}
    if _loop and _loop.is_running():
        asyncio.run_coroutine_threadsafe(
            _store_reading(msg.topic, payload),
            _loop,
        )


def _start_mqtt() -> None:
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    except AttributeError:
        client = mqtt.Client()
    client.on_message = _on_message

    def on_connect(c, *_args):
        print("[telemetry] MQTT connected", flush=True)
        for t in MQTT_TOPICS:
            t = t.strip()
            if t:
                c.subscribe(t)
                print(f"[telemetry] subscribed {t}", flush=True)

    client.on_connect = on_connect
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.loop_start()


@app.on_event("startup")
async def startup() -> None:
    global _pool, _loop
    _loop = asyncio.get_running_loop()
    dsn = _asyncpg_dsn(DATABASE_URL)
    kwargs: dict[str, Any] = {"min_size": 1, "max_size": 3}
    if "render.com" in dsn or "ssl=require" in DATABASE_URL:
        kwargs["ssl"] = True
    _pool = await asyncpg.create_pool(dsn, **kwargs)
    async with _pool.acquire() as conn:
        await _ensure_table(conn)
    threading.Thread(target=_start_mqtt, daemon=True).start()


@app.on_event("shutdown")
async def shutdown() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "telemetry"}


@app.get("/v1/latest")
async def latest() -> dict[str, Any]:
    return {"items": list(_latest.values())}


@app.get("/v1/finca/{crop_id}")
async def finca_readings(crop_id: str, limit: int = 20) -> dict[str, Any]:
    if not _pool:
        return {"items": []}
    async with _pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT topic, entity_type, entity_id, metric, value, unit, payload, recorded_at
            FROM sensor_readings
            WHERE entity_type = 'finca' AND entity_id = $1
            ORDER BY recorded_at DESC
            LIMIT $2
            """,
            crop_id,
            limit,
        )
    items = []
    for r in rows:
        items.append(
            {
                "topic": r["topic"],
                "entity_type": r["entity_type"],
                "entity_id": r["entity_id"],
                "metric": r["metric"],
                "value": r["value"],
                "unit": r["unit"],
                "payload": json.loads(r["payload"]) if r["payload"] else {},
                "recorded_at": r["recorded_at"].isoformat(),
            }
        )
    return {"items": items}
