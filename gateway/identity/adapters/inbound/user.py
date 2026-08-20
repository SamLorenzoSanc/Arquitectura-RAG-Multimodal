from fastapi import APIRouter, Depends

from identity.adapters.inbound.auth import get_current_user, get_identity
from identity.composition import IdentityContainer
from models.user import User

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/")
async def list_users(hexagon: IdentityContainer = Depends(get_identity)):
    return await hexagon.list_users.execute()


@router.get("/roles")
async def list_roles(hexagon: IdentityContainer = Depends(get_identity)):
    return await hexagon.list_roles.execute()


@router.get("/me/roles")
async def get_my_roles(
    current_user: User = Depends(get_current_user),
    hexagon: IdentityContainer = Depends(get_identity),
):
    return await hexagon.my_roles.execute(current_user.id)
