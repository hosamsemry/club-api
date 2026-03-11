import time
import json
import logging

from rest_framework_simplejwt.authentication import JWTAuthentication

logger = logging.getLogger("api")


class APILoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.jwt_authenticator = JWTAuthentication()

    def __call__(self, request):
        start_time = time.time()

        user_id = None
        user_email = "Anonymous"

        # Try to authenticate JWT manually for logging purposes
        try:
            auth_result = self.jwt_authenticator.authenticate(request)
            if auth_result is not None:
                user, _ = auth_result
                user_id = user.id
                user_email = getattr(user, "email", "Unknown")
        except Exception:
            pass

        try:
            body = request.body.decode("utf-8")
            body = json.loads(body) if body else {}
        except Exception:
            body = {}

        # Hide sensitive fields
        sensitive_fields = {"password", "access", "refresh", "token"}
        if isinstance(body, dict):
            body = {
                key: ("***" if key in sensitive_fields else value)
                for key, value in body.items()
            }

        response = self.get_response(request)

        duration = round((time.time() - start_time) * 1000, 2)

        logger.info(
            f"{request.method} {request.path} | "
            f"user_id={user_id} | user={user_email} | "
            f"status={response.status_code} | duration={duration}ms | "
            f"body={body}"
        )

        return response