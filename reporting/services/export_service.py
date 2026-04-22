import csv
import os
from decimal import Decimal
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
        writer.writerow(["revenue_breakdown", "amount"])
        for label, amount in report.revenue_breakdown.items():
            writer.writerow([label, amount])
        writer.writerow([])
        writer.writerow(["activity_metric", "value"])
        for label, value in report.activity_summary.items():
            writer.writerow([label, value])
        writer.writerow([])
        writer.writerow(["top_products"])
        writer.writerow(["product_id", "product_name", "product_sku", "total_quantity_sold", "total_revenue"])
        for row in report.top_products:
            writer.writerow(
                [
                    row.get("product_id"),
                    row.get("product_name"),
                    row.get("product_sku"),
                    row.get("total_quantity_sold"),
                    row.get("total_revenue"),
                ]
            )
        writer.writerow([])
        writer.writerow(["audit_action", "count"])

        for action, count in sorted(report.audit_action_counts.items()):
            writer.writerow([action, count])

        ReportExportService.clear_csv_export(report=report)

        content = ContentFile(buffer.getvalue().encode("utf-8"))
        file_name = os.path.basename(f"daily-report-{report.report_date}.csv")
        report.csv_file.save(file_name, content, save=True)
        return report

    @staticmethod
    def build_transactions_csv(*, rows, start_date, end_date, source="all"):
        buffer = StringIO()
        writer = csv.writer(buffer)

        writer.writerow(["report_type", "transactions"])
        writer.writerow(["start_date", start_date.isoformat()])
        writer.writerow(["end_date", end_date.isoformat()])
        writer.writerow(["source", source])
        writer.writerow([])
        writer.writerow(
            [
                "reference",
                "source",
                "status",
                "customer_name",
                "customer_phone",
                "summary",
                "gross_amount",
                "refund_amount",
                "net_amount",
                "activity_at",
                "created_by_email",
            ]
        )

        gross_total = Decimal("0.00")
        refund_total = Decimal("0.00")
        net_total = Decimal("0.00")

        for row in rows:
            gross_amount = row.get("gross_amount") or Decimal("0.00")
            refund_amount = row.get("refund_amount") or Decimal("0.00")
            net_amount = row.get("net_amount") or Decimal("0.00")
            gross_total += gross_amount
            refund_total += refund_amount
            net_total += net_amount
            writer.writerow(
                [
                    row.get("reference"),
                    row.get("source"),
                    row.get("status"),
                    row.get("customer_name"),
                    row.get("customer_phone"),
                    row.get("summary"),
                    gross_amount,
                    refund_amount,
                    net_amount,
                    row.get("activity_at").isoformat() if row.get("activity_at") else "",
                    row.get("created_by_email"),
                ]
            )

        writer.writerow(
            [
                "",
                "",
                "",
                "",
                "",
                "TOTALS",
                gross_total,
                refund_total,
                net_total,
                "",
                "",
            ]
        )

        return buffer.getvalue().encode("utf-8")
