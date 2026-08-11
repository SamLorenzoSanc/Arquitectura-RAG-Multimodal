"""Construye el perfil operativo del agricultor para inyectar en Hybrid/Agentic."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


CROP_PRODUCT_MAP = {
    "plátano": "platano_canarias",
    "platano": "platano_canarias",
    "tomate": "tomate",
    "papa": "papa",
    "papas": "papa",
    "aguacate": "aguacate",
    "vid": "vino",
    "viña": "vino",
    "vina": "vino",
}

ISLAND_CODE_MAP = {
    "la palma": "La_Palma",
    "gran canaria": "Gran_Canaria",
    "tenerife": "Tenerife_Norte",
    "lanzarote": "Lanzarote",
    "fuerteventura": "Fuerteventura",
    "la gomera": "La_Gomera",
    "el hierro": "El_Hierro",
}


def map_crop_to_product_id(cultivo: str | None) -> str:
    if not cultivo:
        return "platano_canarias"
    key = cultivo.strip().lower()
    for needle, product in CROP_PRODUCT_MAP.items():
        if needle in key:
            return product
    return "platano_canarias"


def map_island_to_code(isla: str | None) -> str:
    if not isla:
        return "La_Palma"
    key = isla.strip().lower().replace("_", " ")
    return ISLAND_CODE_MAP.get(key, isla.replace(" ", "_"))


def _row_to_dict(row) -> dict[str, Any]:
    return dict(row) if row is not None else {}


from services.geo_polygon import polygon_area_ha, polygon_vertex_count


def format_parcel_markdown(parcel: dict[str, Any], treatments: list[dict[str, Any]]) -> str:
    poly = parcel.get("poligono")
    if isinstance(poly, str):
        import json

        try:
            poly = json.loads(poly)
        except Exception:
            poly = None
    n_vertices = polygon_vertex_count(poly if isinstance(poly, dict) else None)
    area_poly = polygon_area_ha(poly if isinstance(poly, dict) else None)

    lines = [
        f"### Parcela: {parcel.get('nombre') or 'Sin nombre'}",
        f"- ID: {parcel.get('id')}",
        f"- Código parcela: {parcel.get('parcela_codigo') or 'n/d'}",
        f"- Ref. catastral: {parcel.get('ref_catastral') or 'n/d'}",
        f"- Cultivo: {parcel.get('cultivo')} | Variedad: {parcel.get('variedad') or 'n/d'}",
        f"- Isla: {parcel.get('isla')} | Centroide: {parcel.get('lat')}, {parcel.get('lon')}",
        f"- Superficie: {parcel.get('superficie_ha') or area_poly or 'n/d'} ha",
        f"- Geometría: {'polígono con ' + str(n_vertices) + ' vértices' if n_vertices else 'punto (sin polígono)'}",
        f"- Riego: {parcel.get('sistema_riego') or 'n/d'}",
        f"- Fuente de agua: {parcel.get('fuente_agua') or 'n/d'}",
        f"- Dotación: {parcel.get('dotacion_m3_ha_anio') or 'n/d'} m³/ha·año",
        f"- Comunidad de regantes: {parcel.get('comunidad_regantes') or 'n/d'}",
        f"- Certificaciones: {parcel.get('certificaciones') or 'n/d'}",
    ]
    if parcel.get("notas"):
        lines.append(f"- Notas: {parcel['notas']}")
    if treatments:
        lines.append("- Tratamientos fitosanitarios recientes:")
        for t in treatments:
            lines.append(
                f"  - {t.get('fecha')}: {t.get('producto')} "
                f"({t.get('materia_activa') or 's/m.a.'}) "
                f"dosis={t.get('dosis') or 'n/d'}, "
                f"plaga={t.get('plaga_objetivo') or 'n/d'}, "
                f"carencia={t.get('carencia_dias') if t.get('carencia_dias') is not None else 'n/d'} días"
            )
    else:
        lines.append("- Tratamientos fitosanitarios: ninguno registrado")
    return "\n".join(lines)


async def load_treatments(db: AsyncSession, crop_id: str, limit: int = 8) -> list[dict[str, Any]]:
    result = await db.execute(
        text(
            """
            SELECT id, crop_id, fecha, producto, materia_activa, dosis,
                   plaga_objetivo, carencia_dias, observaciones
            FROM crop_treatments
            WHERE crop_id = :crop_id
            ORDER BY fecha DESC
            LIMIT :limit
            """
        ),
        {"crop_id": crop_id, "limit": limit},
    )
    out = []
    for r in result.mappings().all():
        item = dict(r)
        if item.get("fecha") is not None:
            item["fecha"] = str(item["fecha"])
        out.append(item)
    return out


async def load_parcel(
    db: AsyncSession,
    *,
    crop_id: str,
    user_id: str | None = None,
) -> Optional[dict[str, Any]]:
    clauses = ["id = :crop_id"]
    params: dict[str, Any] = {"crop_id": crop_id}
    if user_id:
        clauses.append("user_id = :user_id")
        params["user_id"] = user_id
    result = await db.execute(
        text(
            f"""
            SELECT id, user_id, organization_id, nombre, cultivo, isla, lat, lon,
                   temperatura, humedad, lluvia, viento, ndvi, sentinel_tile,
                   ref_catastral, superficie_ha, variedad, sistema_riego,
                   fuente_agua, dotacion_m3_ha_anio, comunidad_regantes,
                   certificaciones, notas, parcela_codigo, poligono
            FROM crops
            WHERE {' AND '.join(clauses)}
            LIMIT 1
            """
        ),
        params,
    )
    row = result.mappings().first()
    return dict(row) if row else None


async def load_user_parcels(
    db: AsyncSession,
    user_id: str,
    organization_id: str | None = None,
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"user_id": user_id}
    org_filter = ""
    if organization_id:
        org_filter = " AND (organization_id = :organization_id OR organization_id IS NULL)"
        params["organization_id"] = organization_id
    result = await db.execute(
        text(
            f"""
            SELECT id, user_id, organization_id, nombre, cultivo, isla, lat, lon,
                   temperatura, humedad, lluvia, viento, ndvi, sentinel_tile,
                   ref_catastral, superficie_ha, variedad, sistema_riego,
                   fuente_agua, dotacion_m3_ha_anio, comunidad_regantes,
                   certificaciones, notas, parcela_codigo, poligono
            FROM crops
            WHERE user_id = :user_id{org_filter}
            ORDER BY nombre
            """
        ),
        params,
    )
    return [dict(r) for r in result.mappings().all()]


async def load_recent_telemetry(
    db: AsyncSession, crop_id: str, limit: int = 5
) -> list[dict[str, Any]]:
    """Últimas lecturas IoT (telemetry-service → sensor_readings)."""
    try:
        result = await db.execute(
            text(
                """
                SELECT metric, value, unit, recorded_at
                FROM sensor_readings
                WHERE entity_type = 'finca' AND entity_id = :cid
                ORDER BY recorded_at DESC
                LIMIT :lim
                """
            ),
            {"cid": str(crop_id), "lim": limit},
        )
        return [dict(r) for r in result.mappings().all()]
    except Exception:
        return []


async def build_farmer_context(
    db: AsyncSession,
    *,
    user_id: str,
    crop_id: str | None = None,
    organization_id: str | None = None,
    fallback_crop: str | None = None,
    fallback_island: str | None = None,
) -> dict[str, Any]:
    """
    Devuelve:
      - markdown: bloque para system prompt
      - profile: dict serializable (metadata / farmer_profile)
      - product_id / island_code: para tools de precios/clima
    """
    parcel: Optional[dict[str, Any]] = None
    treatments: list[dict[str, Any]] = []
    telemetry: list[dict[str, Any]] = []

    if crop_id:
        parcel = await load_parcel(db, crop_id=crop_id, user_id=user_id)

    if parcel is None:
        parcels = await load_user_parcels(db, user_id, organization_id)
        if parcels:
            parcel = parcels[0]

    if parcel:
        treatments = await load_treatments(db, str(parcel["id"]))
        telemetry = await load_recent_telemetry(db, str(parcel["id"]))
        markdown = (
            "## PERFIL_OPERATIVO_AGRICULTOR\n"
            "Hechos estructurados de la explotación (prioridad sobre conjeturas):\n"
            + format_parcel_markdown(parcel, treatments)
        )
        if telemetry:
            markdown += "\n\n#### Telemetría reciente (MQTT)\n"
            for t in telemetry:
                markdown += (
                    f"- {t.get('metric')}: {t.get('value')} {t.get('unit') or ''} "
                    f"@ {t.get('recorded_at')}\n"
                )
        product_id = map_crop_to_product_id(parcel.get("cultivo"))
        island_code = map_island_to_code(parcel.get("isla"))
        profile = {
            "crop_id": parcel.get("id"),
            "nombre": parcel.get("nombre"),
            "cultivo": parcel.get("cultivo"),
            "variedad": parcel.get("variedad"),
            "isla": parcel.get("isla"),
            "ref_catastral": parcel.get("ref_catastral"),
            "parcela_codigo": parcel.get("parcela_codigo"),
            "superficie_ha": parcel.get("superficie_ha"),
            "poligono": parcel.get("poligono"),
            "sistema_riego": parcel.get("sistema_riego"),
            "fuente_agua": parcel.get("fuente_agua"),
            "dotacion_m3_ha_anio": parcel.get("dotacion_m3_ha_anio"),
            "comunidad_regantes": parcel.get("comunidad_regantes"),
            "certificaciones": parcel.get("certificaciones"),
            "treatments": treatments,
            "telemetry": telemetry,
            "product_id": product_id,
            "island_code": island_code,
        }
        return {
            "markdown": markdown,
            "profile": profile,
            "product_id": product_id,
            "island_code": island_code,
        }

    product_id = fallback_crop or "platano_canarias"
    island_code = fallback_island or "La_Palma"
    markdown = (
        "## PERFIL_OPERATIVO_AGRICULTOR\n"
        f"Sin parcela registrada. Usando cultivo={product_id}, zona={island_code}."
    )
    return {
        "markdown": markdown,
        "profile": {
            "crop_id": None,
            "cultivo": product_id,
            "isla": island_code,
            "product_id": product_id,
            "island_code": island_code,
            "treatments": [],
            "telemetry": [],
        },
        "product_id": product_id,
        "island_code": island_code,
    }
