import csv
import os
from io import StringIO

from django.core.files.base import ContentFile


class ReportExportService:
    @staticmethod
    def clear_csv_export(*, report):
        if not report.csv_file:
            return

        storage = report.csv_file.storage
        file_name = report.csv_file.name
        report.csv_file.delete(save=False)
        if file_name and storage.exists(file_name):
            storage.delete(file_name)
        report.csv_file = None
        report.save(update_fields=["csv_file"])

    @staticmethod
    def generate_csv(*, report):
        buffer = StringIO()
        writer = csv.writer(buffer)

        writer.writerow(["club", report.club.name])
        writer.writerow(["report_date", report.report_date.isoformat()])
        writer.writerow(["timezone", report.timezone])
        writer.writerow(["source_window_start", report.source_window_start.isoformat()])
        writer.writerow(["source_window_end", report.source_window_end.isoformat()])
        writer.writerow(["sales_count", report.sales_count])
        writer.writerow(["total_revenue", str(report.total_revenue)])
        writer.writerow([])
        writer.writerow(["audit_action", "count"])

        for action, count in sorted(report.audit_action_counts.items()):
            writer.writerow([action, count])

        ReportExportService.clear_csv_export(report=report)

        content = ContentFile(buffer.getvalue().encode("utf-8"))
        file_name = os.path.basename(f"daily-report-{report.report_date}.csv")
        report.csv_file.save(file_name, content, save=True)
        return report
