import logging
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def _format_item(item):
    if isinstance(item, dict):
        sub_items = [
            f"{str(k).replace('_', ' ').capitalize()}: {_format_item(v)}"
            if not str(k).isdigit()
            else _format_item(v)
            for k, v in item.items()
        ]
        return "; ".join(sub_items)
    if isinstance(item, list):
        return ", ".join(_format_item(i) for i in item)
    return str(item)


def _normalize_errors(data):
    if isinstance(data, list):
        return {"detail": [_format_item(item) for item in data]}

    if isinstance(data, dict):
        normalized = {}
        for key, value in data.items():
            if isinstance(value, list):
                normalized[key] = [_format_item(item) for item in value]
            elif isinstance(value, dict):
                normalized[key] = [_format_item(value)]
            else:
                normalized[key] = [str(value)]
        return normalized

    return {"detail": [str(data)]}


def _extract_primary_message(errors, fallback_message):
    if not isinstance(errors, dict) or not errors:
        return fallback_message

    # 1. Detail / Non-field errors take highest priority
    for key in ("detail", "non_field_errors", "error"):
        if key in errors and errors[key]:
            val = errors[key]
            if isinstance(val, list) and val:
                return str(val[0])
            if isinstance(val, str) and val:
                return val

    # 2. Extract first field-specific error with formatted field name
    for field, msgs in errors.items():
        if field in ("success", "message", "errors"):
            continue
        field_str = str(field)
        field_label = field_str.replace("_", " ").strip().capitalize()
        if isinstance(msgs, list) and msgs:
            return f"{field_label}: {msgs[0]}"
        elif isinstance(msgs, str) and msgs:
            return f"{field_label}: {msgs}"

    return fallback_message


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        logger.exception("Unhandled API error", exc_info=exc)
        return Response(
            {
                "success": False,
                "message": "Internal server error",
                "errors": {
                    "detail": ["An unexpected error occurred."]
                },
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    status_code = response.status_code

    if status_code == 400:
        fallback_message = "Validation error"
    elif status_code == 401:
        fallback_message = "Authentication required. Please sign in."
    elif status_code == 403:
        fallback_message = "Permission denied. You do not have access to perform this action."
    elif status_code == 404:
        fallback_message = "Resource not found"
    else:
        fallback_message = "Request failed"

    normalized_errors = _normalize_errors(response.data)
    primary_message = _extract_primary_message(normalized_errors, fallback_message)

    response.data = {
        "success": False,
        "message": primary_message,
        "errors": normalized_errors,
    }

    return response