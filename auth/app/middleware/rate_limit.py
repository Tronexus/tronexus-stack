from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from app.services.rate_limit_service import is_banned, check_rate_limit


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/health":
            return await call_next(request)

        ip = request.client.host if request.client else "unknown"

        try:
            if await is_banned(ip):
                return JSONResponse({"detail": "Too many requests. Try again later."}, status_code=429)
            if not await check_rate_limit(ip, request.url.path):
                return JSONResponse({"detail": "Rate limit exceeded."}, status_code=429)
        except Exception:
            pass

        return await call_next(request)
