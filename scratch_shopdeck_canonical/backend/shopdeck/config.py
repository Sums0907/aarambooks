import os

def _get_int(key: str, default: int) -> int:
    val = os.environ.get(key)
    if val is not None:
        try:
            return int(val)
        except ValueError:
            raise ValueError(f"Invalid integer configuration for {key}: {val}")
    return default

def _get_str_strict(key: str) -> str:
    val = os.environ.get(key)
    if not val:
        raise ValueError(f"Missing required configuration: {key}")
    return val

MCP_BASE_URL = _get_str_strict("SHOPDECK_MCP_URL")
DATABASE_URL_SYNC = _get_str_strict("DATABASE_URL_SYNC")

# MCP Request and Auth Limits
MCP_REQUEST_TIMEOUT = _get_int("SHOPDECK_MCP_REQUEST_TIMEOUT", 120)
MCP_AUTH_TIMEOUT = _get_int("SHOPDECK_MCP_AUTH_TIMEOUT", 30)
AUTH_REDIRECT_PORT = _get_int("SHOPDECK_AUTH_REDIRECT_PORT", 8080)

# Synchronization Checkpoints and Constraints
BOOTSTRAP_LOOKBACK_DAYS = _get_int("SHOPDECK_BOOTSTRAP_LOOKBACK_DAYS", 30)
CLOCK_SKEW_OVERLAP_MINUTES = _get_int("SHOPDECK_CLOCK_SKEW_OVERLAP_MINUTES", 5)
EVENT_REPLAY_WINDOW_MINUTES = _get_int("SHOPDECK_EVENT_REPLAY_WINDOW_MINUTES", 1440)
AWB_BATCH_SIZE = _get_int("SHOPDECK_AWB_BATCH_SIZE", 500)

# Database Concurrency
LOCK_NAMESPACE = os.environ.get("SHOPDECK_LOCK_NAMESPACE", "SHOPDECK_SYNC_PROD")

# Network Resilience
MCP_RETRY_COUNT = _get_int("SHOPDECK_MCP_RETRY_COUNT", 3)
MCP_RETRY_BACKOFF = _get_int("SHOPDECK_MCP_RETRY_BACKOFF", 5)

# Per-Table Sync Cadences (in minutes)
CADENCE_MINUTES = {
    "order_line_items": _get_int("SHOPDECK_CADENCE_ORDER_LINE_ITEMS", 5),
    "ndr_action_log": _get_int("SHOPDECK_CADENCE_NDR_ACTION_LOG", 5),
    "ndr_proxy": _get_int("SHOPDECK_CADENCE_NDR_PROXY", 5),
    "order_summary": _get_int("SHOPDECK_CADENCE_ORDER_SUMMARY", 15),
    "customer_info": _get_int("SHOPDECK_CADENCE_CUSTOMER_INFO", 60),
    "cancel_reason_events": _get_int("SHOPDECK_CADENCE_CANCEL_REASON_EVENTS", 60),
    "order_cancellation_events": _get_int("SHOPDECK_CADENCE_ORDER_CANCELLATION_EVENTS", 60),
    "return_exchange_events": _get_int("SHOPDECK_CADENCE_RETURN_EXCHANGE_EVENTS", 60),
    "post_order_survey_submit_events": _get_int("SHOPDECK_CADENCE_POST_ORDER_SURVEY_SUBMIT_EVENTS", 60),
    "rating_review_feedback_submit_events": _get_int("SHOPDECK_CADENCE_RATING_REVIEW_FEEDBACK_SUBMIT_EVENTS", 60),
    "payment_gateway_events": _get_int("SHOPDECK_CADENCE_PAYMENT_GATEWAY_EVENTS", 60),
    "checkout_external_events": _get_int("SHOPDECK_CADENCE_CHECKOUT_EXTERNAL_EVENTS", 60),
    "checkout_input_error_events": _get_int("SHOPDECK_CADENCE_CHECKOUT_INPUT_ERROR_EVENTS", 60),
}

# Identity and Auth Configuration
IDENTITY_API_URL = os.environ.get("IDENTITY_API_URL", "https://api-identity.aarambooks.cloud")

# CORS Settings
# If not provided, defaults to "*". In production, provide a comma-separated list.
ALLOWED_ORIGINS_STR = os.environ.get("ALLOWED_ORIGINS", "*")
ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS_STR.split(",")] if ALLOWED_ORIGINS_STR != "*" else ["*"]
