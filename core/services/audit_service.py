from core.models import AuditLog


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
        return AuditLog.objects.create(
            action=action,
            club=club,
            user=user,
            details=details or {},
            path=path,
            method=method,
            status_code=status_code,
            ip_address=ip_address,
        )
