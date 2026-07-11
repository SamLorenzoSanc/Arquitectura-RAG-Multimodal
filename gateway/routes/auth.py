from fastapi import APIRouter

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.post("/login")
async def login():

    return {
        "token": "jwt-token"
    }


@router.post("/register")
async def register():

    return {
        "status": "registered"
    }


@router.post("/logout")
async def logout():

    return {
        "status": "logged out"
    }