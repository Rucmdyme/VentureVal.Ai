from fastapi import Request, HTTPException
from typing import Optional, Callable
from functools import wraps
from services.user_service import UserService
import logging

logger = logging.getLogger(__name__)
user_service = UserService()

async def get_idtoken_from_request(request: Request) -> Optional[str]:
    """
    Extract idtoken from request payload (POST/PUT/PATCH) or query params (GET/DELETE).
    """
    if request.method in ("POST", "PUT", "PATCH"):
        try:
            body = await request.json() if hasattr(request, 'json') else None
            if body and isinstance(body, dict) and 'idtoken' in body:
                return body['idtoken']
        except Exception:
            pass
    # Always check query params as fallback
    idtoken = request.query_params.get('idtoken')
    return idtoken

async def get_user_details(request: Request) -> Optional[dict]:
    """
    Returns user details if idtoken is present and valid, else None.
    Raises HTTPException if idtoken is present but invalid.
    """
    idtoken = await get_idtoken_from_request(request)
    if not idtoken:
        return None
    try:
        return await user_service.get_current_user(idtoken)
    except HTTPException as e:
        raise
    except Exception as e:
        logger.error(f"Error validating idtoken: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired idtoken")

def require_user_or_none(func: Callable) -> Callable:
    """
    Decorator for FastAPI endpoints. Injects user_info (dict or None) as kwarg.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        request: Request = kwargs.get('request')
        if not request:
            # Try to find request in args
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
        user_info = None
        if request:
            user_info = await get_user_details(request)
        kwargs['user_info'] = user_info
        return await func(*args, **kwargs)
    return wrapper
