from fastapi import APIRouter

router = APIRouter(
    prefix="/metrics",
    tags=["Metrics"]
)


@router.get("")
async def metrics():

    return {
        "requests": 0,
        "latency": 0
    }