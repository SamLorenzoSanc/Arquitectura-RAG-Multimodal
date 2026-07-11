from fastapi import APIRouter

router = APIRouter(
    prefix="/models",
    tags=["Models"]
)


@router.get("")
async def list_models():

    return {
        "models": [
            "llama3",
            "mistral",
            "phi4"
        ]
    }


@router.post("/select")
async def select_model(model: str):

    return {
        "selected": model
    }