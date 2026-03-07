from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def _normalize_errors(data):
    if isinstance(data, list):
        return {"detail": data}

    if isinstance(data, dict):
        normalized = {}
        for key, value in data.items():
            if isinstance(value, list):
                normalized[key] = value
            else:
                normalized[key] = [value]
        return normalized

    return {"detail": [str(data)]}


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
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
        message = "Validation error"
    elif status_code == 401:
        message = "Authentication failed"
    elif status_code == 403:
        message = "Permission denied"
    elif status_code == 404:
        message = "Not found"
    else:
        message = "Request failed"

    response.data = {
        "success": False,
        "message": message,
        "errors": _normalize_errors(response.data),
    }

    return response