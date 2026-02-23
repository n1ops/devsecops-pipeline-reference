from slowapi import Limiter
from starlette.requests import Request


def _get_client_ip(request: Request) -> str:
    """Extract client IP from behind AWS ALB.

    ALB appends the real client IP as the rightmost entry in X-Forwarded-For.
    We take the LAST entry to prevent spoofing via client-controlled headers.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # ALB appends real client IP as the last entry
        return forwarded.split(",")[-1].strip()
    if request.client:
        return request.client.host
    return "127.0.0.1"


limiter = Limiter(
    key_func=_get_client_ip,
    default_limits=["100/minute"],
)
