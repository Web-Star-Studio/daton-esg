from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.models import User
from app.schemas import AuthMeResponse

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.get("/me", response_model=AuthMeResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> AuthMeResponse:
    return AuthMeResponse.model_validate(current_user)
