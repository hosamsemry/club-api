from django.http import FileResponse
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.permissions import RolePermission
from reporting.models import DailyClubReport
from reporting.serializers import DailyClubReportSerializer
from reporting.services.daily_report_service import DailyReportService
from reporting.services.export_service import ReportExportService
from reporting.tasks import regenerate_daily_report_for_club


class DailyClubReportViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DailyClubReportSerializer
    permission_classes = [permissions.IsAuthenticated, RolePermission]
    required_roles = ["owner", "manager"]
    ordering = ["-report_date"]

    def get_queryset(self):
        user = self.request.user
        queryset = DailyClubReport.objects.select_related("club").filter(club=user.club)

        report_date = self.request.query_params.get("report_date")
        if report_date:
            queryset = queryset.filter(report_date=report_date)

        start_date = self.request.query_params.get("start_date")
        if start_date:
            queryset = queryset.filter(report_date__gte=start_date)

        end_date = self.request.query_params.get("end_date")
        if end_date:
            queryset = queryset.filter(report_date__lte=end_date)

        return queryset.order_by("-report_date")

    @action(detail=True, methods=["get"], url_path="export/csv")
    def export_csv(self, request, pk=None):
        report = self.get_object()
        if not report.csv_file:
            report = ReportExportService.generate_csv(report=report)

        return FileResponse(
            report.csv_file.open("rb"),
            as_attachment=True,
            filename=f"daily-report-{report.report_date}.csv",
            content_type="text/csv",
        )

    @action(detail=True, methods=["post"], url_path="regenerate")
    def regenerate(self, request, pk=None):
        report = self.get_object()
        task = regenerate_daily_report_for_club.delay(report.club_id, report.report_date.isoformat())

        return Response(
            {
                "detail": "Report regeneration scheduled.",
                "task_id": task.id,
            },
            status=status.HTTP_202_ACCEPTED,
        )
