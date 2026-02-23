import uuid
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import settings
from app.database import Base, engine
from app.rate_limit import limiter
from app.routers import auth, health, tasks

logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Secure Task Management API — DevSecOps Pipeline Reference",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
)


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Catch unhandled exceptions and return safe JSON without stack traces."""
    logger.error("Unhandled exception: %s", str(exc), exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# --- Pure ASGI Security Headers Middleware ---
class SecurityHeadersMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                security_headers = [
                    (b"x-content-type-options", b"nosniff"),
                    (b"x-frame-options", b"DENY"),
                    (b"x-xss-protection", b"0"),
                    (b"strict-transport-security", b"max-age=31536000; includeSubDomains"),
                    (b"referrer-policy", b"strict-origin-when-cross-origin"),
                    (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
                    (b"content-security-policy", b"default-src 'none'; frame-ancestors 'none'"),
                    (b"cross-origin-opener-policy", b"same-origin"),
                    (b"cross-origin-resource-policy", b"same-origin"),
                ]
                if not path.startswith("/health"):
                    security_headers.append(
                        (b"cache-control", b"no-store, no-cache, must-revalidate")
                    )
                    security_headers.append((b"pragma", b"no-cache"))
                headers.extend(security_headers)
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_headers)


# --- Pure ASGI Request ID Middleware ---
class RequestIDMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = str(uuid.uuid4())
        scope.setdefault("state", {})
        scope["state"]["request_id"] = request_id

        async def send_with_request_id(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode()))
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_request_id)


# --- Pure ASGI Request Body Size Limit Middleware ---
class MaxBodySizeMiddleware:
    """Reject requests with body exceeding the size limit, regardless of transfer encoding."""
    MAX_BODY_BYTES = 1_048_576  # 1 MB

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Fast path: reject immediately if Content-Length exceeds limit
        headers = dict(scope.get("headers", []))
        content_length = headers.get(b"content-length")
        if content_length:
            try:
                if int(content_length) > self.MAX_BODY_BYTES:
                    response = JSONResponse(
                        status_code=413,
                        content={"detail": "Request body too large"},
                    )
                    await response(scope, receive, send)
                    return
            except (ValueError, TypeError):
                pass  # Malformed Content-Length; let the ASGI server handle it

        # Streaming path: wrap receive to count bytes (handles chunked encoding)
        bytes_received = 0

        async def counting_receive():
            nonlocal bytes_received
            message = await receive()
            if message["type"] == "http.request":
                bytes_received += len(message.get("body", b""))
                if bytes_received > self.MAX_BODY_BYTES:
                    raise ValueError("Request body too large")
            return message

        try:
            await self.app(scope, counting_receive, send)
        except ValueError as e:
            if "Request body too large" in str(e):
                response = JSONResponse(
                    status_code=413,
                    content={"detail": "Request body too large"},
                )
                await response(scope, receive, send)
            else:
                raise


# --- Rate Limiting ---
app.state.limiter = limiter
@app.exception_handler(RateLimitExceeded)
async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    retry_after = getattr(exc, "detail", "60")
    # Extract seconds from slowapi's detail string (e.g., "Rate limit exceeded: 5 per 1 minute")
    response = JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded"},
    )
    response.headers["Retry-After"] = "60"
    return response

# Middleware ordering: add_middleware wraps outermost-last.
# Execution order (request): SecurityHeaders -> RequestID -> CORS -> SlowAPI -> App
# Execution order (response): App -> SlowAPI -> CORS -> RequestID -> SecurityHeaders
# This ensures: security headers are always on the final response,
# CORS runs before rate limiting, and request IDs are on all responses.

app.add_middleware(SlowAPIMiddleware)

# CORS: use explicit origins in production, wildcard only in debug mode
_origins = settings.get_allowed_origins()
if _origins:
    _allow_credentials = "*" not in _origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_origins,
        allow_credentials=_allow_credentials,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

app.add_middleware(MaxBodySizeMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(tasks.router)
