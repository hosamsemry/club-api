from django.http import FileResponse, HttpResponse
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.permissions import RolePermission
from reporting.models import DailyClubReport
from reporting.serializers import (
    DailyClubReportSerializer,
    RevenueQuerySerializer,
    RevenueResponseSerializer,
    TransactionRowSerializer,
    TransactionsQuerySerializer,
)
from reporting.services.daily_report_service import DailyReportService
from reporting.services.export_service import ReportExportService
from reporting.services.revenue_range_service import RevenueRangeService
from reporting.services.transaction_history_service import UnifiedTransactionsService
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


class RevenueViewSet(viewsets.ViewSet):
    """
    GET /api/reporting/revenue/?start_date=...&end_date=...&fields=tickets&fields=products
    Returns per-category revenue and total for the inclusive date range.
    """

    permission_classes = [permissions.IsAuthenticated, RolePermission]
    required_roles = ["owner", "manager"]

    def list(self, request):
        query_serializer = RevenueQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)

        data = query_serializer.validated_data
        result = RevenueRangeService.calculate(
            club=request.user.club,
            start_date=data["start_date"],
            end_date=data["end_date"],
            fields=data["fields"],
        )

        response_serializer = RevenueResponseSerializer(result)
        return Response(response_serializer.data)


class TransactionsViewSet(viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated, RolePermission]
    required_roles = ["owner", "manager"]
    serializer_class = TransactionRowSerializer

    def _get_rows(self, request):
        query_serializer = TransactionsQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        data = query_serializer.validated_data
        rows = UnifiedTransactionsService.list_transactions(
            club=request.user.club,
            start_date=data["start_date"],
            end_date=data["end_date"],
            source=data.get("source", "all"),
            status=data.get("status", ""),
            search=data.get("search", ""),
            ordering=data.get("ordering", "-activity_at"),
        )
        return data, rows

    def list(self, request):
        _, rows = self._get_rows(request)
        page = self.paginate_queryset(rows)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(rows, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="export/csv")
    def export_csv(self, request):
        data, rows = self._get_rows(request)
        csv_content = ReportExportService.build_transactions_csv(
            rows=rows,
            start_date=data["start_date"],
            end_date=data["end_date"],
            source=data.get("source", "all"),
        )
        filename = (
            f"transactions-{data['start_date'].isoformat()}-to-{data['end_date'].isoformat()}.csv"
        )
        response = HttpResponse(csv_content, content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
