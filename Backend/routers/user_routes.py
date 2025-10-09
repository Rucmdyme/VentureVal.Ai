
from fastapi import APIRouter, Response
from models import schemas
from services.user_service import UserService


user_service = UserService()

router = APIRouter(prefix="/user", tags=["user"])

@router.post("/signup")
async def signup(request: schemas.SignupRequest):
	return await user_service.signup(request)

@router.post("/login")
async def login(request: schemas.LoginRequest):
	return await user_service.login(request)

@router.get("/user-info")
async def get_user_info(token: str, response: Response):
	return await user_service.get_current_user(token)

@router.post("/reset-password")
async def reset_password(request: schemas.ResetPasswordRequest):
	return await user_service.reset_password(request)

@router.post("/verify-email")
async def resend_verification(request: schemas.ResendVerificationLink):
	return await user_service.resend_verification(request)
