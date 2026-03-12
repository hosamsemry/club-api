from celery import shared_task
from django.conf import settings

from clubs.models import Club
from reporting.services.daily_report_service import DailyReportService


@shared_task
def schedule_daily_report_generation():
    dispatched = 0
    clubs = Club.objects.filter(is_active=True).only("id", "timezone", "is_active")

    for club in clubs:
        report_date = DailyReportService.get_pending_report_date(
            club=club,
            cutoff_minutes=settings.CELERY_REPORT_GENERATION_CUTOFF_MINUTES,
        )
        if report_date is None:
            continue

        generate_daily_report_for_club.delay(club.id, report_date.isoformat())
        dispatched += 1

    return dispatched


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def generate_daily_report_for_club(self, club_id, report_date=None):
    club = Club.objects.filter(id=club_id, is_active=True).first()
    if club is None:
        return None

    return DailyReportService.generate_for_club(
        club=club,
        report_date=report_date,
    ).id


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def regenerate_daily_report_for_club(self, club_id, report_date):
    club = Club.objects.filter(id=club_id, is_active=True).first()
    if club is None:
        return None

    return DailyReportService.regenerate_for_club(
        club=club,
        report_date=report_date,
    ).id
