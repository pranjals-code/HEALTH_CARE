"""
Prometheus metrics for API and authentication monitoring.
"""
from prometheus_client import Counter, Histogram

# HTTP metrics
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "path", "status_code"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path", "status_code"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

HTTP_RESPONSE_STATUS_TOTAL = Counter(
    "http_response_status_total",
    "Total HTTP responses grouped by status code",
    ["path", "status_code"],
)

# Authentication metrics
LOGIN_ATTEMPTS_TOTAL = Counter(
    "auth_login_attempts_total",
    "Total login attempts",
    ["auth_method"],
)

FAILED_AUTH_ATTEMPTS_TOTAL = Counter(
    "auth_failed_attempts_total",
    "Total failed authentication attempts",
    ["auth_method", "reason"],
)


def record_login_attempt(auth_method: str = "password") -> None:
    """Increment login-attempt counter."""
    LOGIN_ATTEMPTS_TOTAL.labels(auth_method=auth_method).inc()


def record_failed_auth_attempt(
    reason: str,
    auth_method: str = "password",
) -> None:
    """Increment failed-authentication counter."""
    FAILED_AUTH_ATTEMPTS_TOTAL.labels(auth_method=auth_method, reason=reason).inc()
