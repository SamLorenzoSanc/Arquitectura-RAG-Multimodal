from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from schemas.tenant import TenantCreate, AssignTenantRequest
from uuid import uuid4
from services.database import get_db
from .auth import get_current_user 

router = APIRouter(prefix="/tenants", tags=["Tenants"])



@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_tenant(tenant: TenantCreate, db: Session = Depends(get_db)):
    """Crea una nueva empresa o Tenant usando una organización por defecto existente."""
    tenant_id = str(uuid4())
    
    try:
        # 1. Buscamos la organización por defecto existente
        org = db.execute(
            text("SELECT id FROM organizations LIMIT 1")
        ).mappings().first()
        
        if not org:
            raise HTTPException(
                status_code=400, 
                detail="No existe ninguna organización en la BD. Crea una primero."
            )
            
        organization_id = org["id"]

        # 2. Insertamos el Tenant solo con las columnas que sí existen
        db.execute(
            text("""
            INSERT INTO tenants (id, organization_id, name, created_at)
            VALUES (:id, :organization_id, :name, NOW())
            """),
            {
                "id": tenant_id, 
                "organization_id": organization_id, 
                "name": tenant.name
            }
        )
        db.commit()
        
        return {
            "tenant_id": tenant_id, 
            "organization_id": organization_id, 
            "name": tenant.name, 
            "status": "created"
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al crear el Tenant: {str(e)}")
    
    

@router.post("/assign")
async def assign_tenant_to_user(data: AssignTenantRequest, db: Session = Depends(get_db)):
    tenant_exists = db.execute(
        text("SELECT id FROM tenants WHERE id = :id"), {"id": data.tenant_id}
    ).first()
    
    if not tenant_exists:
        raise HTTPException(status_code=404, detail="El Tenant especificado no existe.")

    try:
        result = db.execute(
            text("""
            UPDATE users 
            SET tenant_id = :tenant_id 
            WHERE id = :user_id
            """),
            {"tenant_id": data.tenant_id, "user_id": data.user_id}
        )
        db.commit()
        
        return {"status": "success", "message": "Tenant asignado correctamente al usuario."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al asignar el Tenant: {str(e)}")