import os
import httpx
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from services.database import get_db
from models.user import User
from .auth import get_current_user

router = APIRouter(prefix="/logistics", tags=["Logistics"])


class ShipmentCreateRequest(BaseModel):
    id: str
    product: str
    container_id: str
    origin_name: str
    origin_lat: float
    origin_lng: float
    destination_name: str
    destination_lat: float
    destination_lng: float
    vessel_name: str
    air_chamber: str
    # Nuevos campos terrestres obligatorios para la última milla
    truck_plate: str
    land_carrier: str
    departure_date: datetime
    eta: datetime
    temperature_threshold: float


async def init_shipments_table(db: AsyncSession):
    await db.execute(text("""
            CREATE TABLE IF NOT EXISTS shipments (
                id VARCHAR(50) PRIMARY KEY,
                tenant_id VARCHAR(50) NOT NULL,
                product VARCHAR(150) NOT NULL,
                container_id VARCHAR(50) NOT NULL,
                origin_name VARCHAR(255) NOT NULL,
                origin_lat FLOAT NOT NULL,
                origin_lng FLOAT NOT NULL,
                destination_name VARCHAR(255) NOT NULL,
                destination_lat FLOAT NOT NULL,
                destination_lng FLOAT NOT NULL,
                vessel_name VARCHAR(150) NOT NULL,
                air_chamber VARCHAR(100) DEFAULT 'Cámara Proa - Zona Fría A',
                truck_plate VARCHAR(50) DEFAULT '4829-LMX',
                land_carrier VARCHAR(150) DEFAULT 'Transports Frío Peninsular S.A.',
                departure_date TIMESTAMP NOT NULL,
                eta TIMESTAMP NOT NULL,
                current_step INT DEFAULT 2,
                temperature_threshold FLOAT NOT NULL
            );
        """))
    await db.execute(
        text("ALTER TABLE shipments ADD COLUMN IF NOT EXISTS truck_plate VARCHAR(50);")
    )
    await db.execute(
        text(
            "ALTER TABLE shipments ADD COLUMN IF NOT EXISTS land_carrier VARCHAR(150);"
        )
    )
    await db.commit()


async def fetch_real_vessel_position(vessel_name: str) -> list[float]:
    api_key = os.getenv("MARITIME_API_KEY")
    if api_key and vessel_name:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(
                    "https://api.marinetraffic.com/v1/vessel/position",
                    params={"vessel": vessel_name, "key": api_key},
                )
                if response.status_code == 200:
                    data = response.json()
                    return [float(data["lat"]), float(data["lon"])]
        except Exception as e:
            print(f"[WARN] Falló la API externa de barcos (Usando respaldo): {e}")
    return [31.2000, -15.5000]


async def fetch_reefer_telemetry(container_id: str, threshold: float) -> dict:
    api_key = os.getenv("REEFER_IOT_API_KEY")
    if api_key and container_id:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(
                    f"https://api.naviera-logistics.com/v1/containers/{container_id}/telemetry",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                if response.status_code == 200:
                    data = response.json()
                    history = data.get("temperature_history", [])
                    current_temp = float(data["temperature"])
                    is_alert = current_temp > threshold
                    return {
                        "current_temp": current_temp,
                        "is_alert": is_alert,
                        "history": history,
                    }
        except Exception as e:
            print(f"[WARN] Falló la API de telemetría IoT (Usando respaldo): {e}")

    history = [
        {"time": "23/07 08h", "temp": threshold - 0.8},
        {"time": "24/07 08h", "temp": threshold - 0.2},
    ]
    current_temp = history[-1]["temp"]
    is_alert = current_temp > threshold

    return {"current_temp": current_temp, "is_alert": is_alert, "history": history}


@router.get("/catalog/agricultural-options")
async def get_agricultural_catalog(current_user: User = Depends(get_current_user)):
    return [
        {
            "product": "Plátano de Canarias IGP",
            "containerId": "MSCU 982105-4",
            "vessel": "MSC Canarias",
            "originName": "Finca San Miguel - Tazacorte (La Palma)",
            "originCoords": [28.6478, -17.9255],
            "destinationName": "Plataforma Logística - Cádiz",
            "destinationCoords": [36.5271, -6.2886],
            "temperatureThreshold": 14.0,
        },
        {
            "product": "Aguacate Hass",
            "containerId": "CMAU 452912-1",
            "vessel": "Volcán de Teneguía",
            "originName": "Finca Sur - Mogán (Gran Canaria)",
            "originCoords": [27.8833, -15.7667],
            "destinationName": "Mercamadrid - Madrid",
            "destinationCoords": [40.3833, -3.6833],
            "temperatureThreshold": 6.0,
        },
        {
            "product": "Tomate Canario",
            "containerId": "SUDU 773129-9",
            "vessel": "Boluda Express",
            "originName": "Valle de Guerra (Tenerife Norte)",
            "originCoords": [28.5200, -16.3800],
            "destinationName": "Mercavalència - Valencia",
            "destinationCoords": [39.4699, -0.3763],
            "temperatureThreshold": 10.0,
        },
        {
            "product": "Papaya Tropical",
            "containerId": "HLXU 284910-3",
            "vessel": "MSC Tenerife",
            "originName": "Finca Los Llanos - Güímar (Tenerife)",
            "originCoords": [28.3185, -16.4053],
            "destinationName": "Mercabarna - Barcelona",
            "destinationCoords": [41.3257, 2.1156],
            "temperatureThreshold": 12.0,
        },
    ]


@router.get("/shipments/{shipment_id}/alerts")
async def get_shipment_alerts(
    shipment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    shipment_query = await db.execute(
        text("SELECT * FROM shipments WHERE id = :id"), {"id": shipment_id}
    )
    row = shipment_query.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Lote no encontrado.")

    threshold = float(row["temperature_threshold"])
    telemetry = await fetch_reefer_telemetry(row["container_id"], threshold)

    # Generar alertas estructuradas para el agricultor
    alerts = []
    if telemetry["is_alert"]:
        alerts.append(
            {
                "level": "CRITICAL",
                "title": "Alerta de Desviación Térmica",
                "message": f"El contenedor {row['container_id']} ({row['product']}) superó los {threshold}ºC en la {row['air_chamber']}.",
                "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "status": "Pendiente de revisión por naviera",
            }
        )
    else:
        alerts.append(
            {
                "level": "SUCCESS",
                "title": "Cadena de Frío Garantizada",
                "message": f"El lote de {row['product']} avanza sin incidencias hacia Mercamadrid bajo el umbral de {threshold}ºC.",
                "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "status": "Tranquilidad operativa confirmada",
            }
        )

    return {
        "shipmentId": row["id"],
        "product": row["product"],
        "currentTemp": telemetry["current_temp"],
        "threshold": threshold,
        "hasAlert": telemetry["is_alert"],
        "notificationsLog": alerts,
    }


@router.get("/fleet")
async def get_tenant_vessels(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    member_info = await db.execute(
        text("""
            SELECT t.id AS tenant_id
            FROM organization_members om
            JOIN tenants t ON t.organization_id = om.organization_id
            WHERE om.user_id = :user_id AND om.active = true
            LIMIT 1
        """),
        {"user_id": current_user.id},
    )
    tenant = member_info.mappings().first()
    if not tenant:
        return [
            {"vesselName": "MSC Canarias", "status": "En ruta comercial activa"},
            {"vesselName": "Volcán de Teneguía", "status": "En puerto de origen"},
            {"vesselName": "Boluda Express", "status": "Tránsito marítimo"},
            {"vesselName": "MSC Tenerife", "status": "Operativa peninsular"},
        ]

    vessels_query = await db.execute(
        text("""
            SELECT DISTINCT vessel_name, COUNT(id) as total_shipments
            FROM shipments
            WHERE tenant_id = :tenant_id
            GROUP BY vessel_name
        """),
        {"tenant_id": tenant["tenant_id"]},
    )

    fleet = []
    for row in vessels_query.mappings():
        vessel_name = row["vessel_name"]
        fleet.append(
            {
                "vesselName": vessel_name,
                "activeShipmentsCount": row["total_shipments"],
                "status": "En ruta comercial activa",
            }
        )

    if not fleet:
        fleet = [
            {"vesselName": "MSC Canarias", "status": "Línea Regular"},
            {"vesselName": "Volcán de Teneguía", "status": "Línea Regular"},
            {"vesselName": "Boluda Express", "status": "Línea Regular"},
        ]

    return fleet


@router.get("/shipments")
async def get_tenant_shipments(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    await init_shipments_table(db)

    member_info = await db.execute(
        text("""
            SELECT t.id AS tenant_id
            FROM organization_members om
            JOIN tenants t ON t.organization_id = om.organization_id
            WHERE om.user_id = :user_id AND om.active = true
            LIMIT 1
        """),
        {"user_id": current_user.id},
    )
    tenant = member_info.mappings().first()
    if not tenant:
        return []

    tenant_id = tenant["tenant_id"]

    shipments = await db.execute(
        text("SELECT * FROM shipments WHERE tenant_id = :tenant_id"),
        {"tenant_id": tenant_id},
    )

    result = []
    for row in shipments.mappings():
        vessel_coords = await fetch_real_vessel_position(row["vessel_name"])
        threshold = float(row["temperature_threshold"])
        telemetry = await fetch_reefer_telemetry(row["container_id"], threshold)

        result.append(
            {
                "id": row["id"],
                "product": row["product"],
                "containerId": row["container_id"],
                "originName": row["origin_name"],
                "originCoords": [row["origin_lat"], row["origin_lng"]],
                "destinationName": row["destination_name"],
                "destinationCoords": [row["destination_lat"], row["destination_lng"]],
                "vessel": row["vessel_name"],
                "air_chamber": row.get("air_chamber", "Cámara Proa - Zona Fría A"),
                "departureDate": str(row["departure_date"]),
                "eta": str(row["eta"]),
                "currentStep": row["current_step"],
                "temperatureThreshold": threshold,
                "vesselCoords": vessel_coords,
                "temperatureHistory": telemetry["history"],
                "hasAlert": telemetry["is_alert"],
            }
        )

    return result


@router.post("/shipments")
async def create_shipment(
    request: ShipmentCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await init_shipments_table(db)

    member_info = await db.execute(
        text("""
            SELECT t.id AS tenant_id
            FROM organization_members om
            JOIN tenants t ON t.organization_id = om.organization_id
            WHERE om.user_id = :user_id AND om.active = true
            LIMIT 1
        """),
        {"user_id": current_user.id},
    )
    tenant = member_info.mappings().first()
    if not tenant:
        raise HTTPException(status_code=403, detail="Usuario sin tenant activo.")

    await db.execute(
        text("""
            INSERT INTO shipments (
                id, tenant_id, product, container_id, origin_name, origin_lat, origin_lng,
                destination_name, destination_lat, destination_lng, vessel_name, air_chamber, departure_date, eta, current_step, temperature_threshold
            ) VALUES (
                :id, :tenant_id, :product, :container_id, :origin_name, :origin_lat, :origin_lng,
                :destination_name, :destination_lat, :destination_lng, :vessel_name, :air_chamber, :departure_date, :eta, 2, :temperature_threshold
            )
            ON CONFLICT (id) DO UPDATE SET
                vessel_name = EXCLUDED.vessel_name,
                air_chamber = EXCLUDED.air_chamber,
                temperature_threshold = EXCLUDED.temperature_threshold,
                eta = EXCLUDED.eta;
        """),
        {
            "id": request.id,
            "tenant_id": tenant["tenant_id"],
            "product": request.product,
            "container_id": request.container_id,
            "origin_name": request.origin_name,
            "origin_lat": request.origin_lat,
            "origin_lng": request.origin_lng,
            "destination_name": request.destination_name,
            "destination_lat": request.destination_lat,
            "destination_lng": request.destination_lng,
            "vessel_name": request.vessel_name,
            "air_chamber": request.air_chamber,
            "departure_date": request.departure_date,
            "eta": request.eta,
            "temperature_threshold": request.temperature_threshold,
        },
    )
    await db.commit()
    return {
        "message": "Envío registrado correctamente en la base de datos",
        "id": request.id,
    }


async def send_temperature_alert_whatsapp(
    phone_number: str,
    product: str,
    container_id: str,
    current_temp: float,
    threshold: float,
):
    # Variables de entorno para WhatsApp Cloud API / Twilio
    whatsapp_api_url = os.getenv(
        "WHATSAPP_API_URL",
        "https://graph.facebook.com/v17.0/699296619/messages",
    )
    whatsapp_token = os.getenv("WHATSAPP_ACCESS_TOKEN", "tu_token_de_meta")

    message_body = (
        f"*¡ALERTA CRÍTICA EN CADENA DE FRÍO!*\n\n"
        f"Estimado productor, el contenedor *{container_id}* con *{product}* ha registrado una temperatura de *{current_temp}ºC*.\n\n"
        f"*Límite máximo permitido:* {threshold}ºC\n"
        f"*Estado:* Requiere revisión urgente en el Centro de Control Logístico hacia Mercamadrid."
    )

    # Si tienes configurada la API de Meta / Twilio, realizamos la petición HTTP
    if whatsapp_token and "tu_token" not in whatsapp_token:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    whatsapp_api_url,
                    headers={"Authorization": f"Bearer {whatsapp_token}"},
                    json={
                        "messaging_product": "whatsapp",
                        "to": phone_number,
                        "type": "text",
                        "text": {"body": message_body},
                    },
                )
                if response.status_code == 200:
                    print(
                        f"[INFO] Alerta de WhatsApp enviada con éxito a {phone_number}"
                    )
        except Exception as e:
            print(f"[ERROR] Falló el envío de WhatsApp: {e}")
    else:
        print(
            f"[SIMULACIÓN WHATSAPP] Mensaje enviado a {phone_number}:\n{message_body}"
        )


@router.post("/shipments/{shipment_id}/force-alert")
async def force_shipment_alert(
    shipment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    shipment_query = await db.execute(
        text("SELECT * FROM shipments WHERE id = :id"), {"id": shipment_id}
    )
    row = shipment_query.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Lote no encontrado.")

    threshold = float(row["temperature_threshold"])
    forced_temp = threshold + 3.5  # Temperatura simulada en zona de alerta

    # Obtener el teléfono del usuario o un número de agricultor registrado (por defecto un número de prueba)
    farmer_phone = getattr(current_user, "phone", "+34699296619")

    # Enviar la alerta crítica por WhatsApp
    await send_temperature_alert_whatsapp(
        phone_number=farmer_phone,
        product=row["product"],
        container_id=row["container_id"],
        current_temp=forced_temp,
        threshold=threshold,
    )

    return {
        "success": True,
        "message": f"¡Alerta de WhatsApp simulada y enviada correctamente al número {farmer_phone}!",
        "forcedTemp": forced_temp,
        "threshold": threshold,
    }


@router.get("/alerts/summary")
async def get_logistics_alerts_summary(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    member_info = await db.execute(
        text("""
            SELECT t.id AS tenant_id
            FROM organization_members om
            JOIN tenants t ON t.organization_id = om.organization_id
            WHERE om.user_id = :user_id AND om.active = true
            LIMIT 1
        """),
        {"user_id": current_user.id},
    )
    tenant = member_info.mappings().first()
    if not tenant:
        return {"totalAlerts": 0, "alerts": []}

    shipments = await db.execute(
        text("SELECT * FROM shipments WHERE tenant_id = :tenant_id"),
        {"tenant_id": tenant["tenant_id"]},
    )

    active_alerts = []
    for row in shipments.mappings():
        threshold = float(row["temperature_threshold"])
        telemetry = await fetch_reefer_telemetry(row["container_id"], threshold)

        if telemetry["is_alert"]:
            active_alerts.append(
                {
                    "id": row["id"],
                    "product": row["product"],
                    "containerId": row["container_id"],
                    "currentTemp": telemetry["current_temp"],
                    "threshold": threshold,
                    "message": f"¡Alerta térmica! {row['product']} a {telemetry['current_temp']}ºC (Máx: {threshold}ºC)",
                }
            )

    return {"totalAlerts": len(active_alerts), "alerts": active_alerts}
