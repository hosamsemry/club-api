from core.models import AuditLog
import logging

logger = logging.getLogger(__name__)

class AuditService:
    @staticmethod
    def log(
        *,
        action,
        club=None,
        user=None,
        details=None,
        path="",
        method="",
        status_code=None,
        ip_address=None,
    ):
        try:
            return AuditService._create_log(
                action=action,
                club=club,
                user=user,
                details=details,
                path=path,
                method=method,
                status_code=status_code,
                ip_address=ip_address,
            )
        except Exception as e:
            logger.error(f"Failed to log audit action: {e}")
            return None
