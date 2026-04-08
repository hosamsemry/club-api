from datetime import timedelta
from django.utils import timezone
from celery import shared_task
from django.db.models import Sum, Q
from django.core.cache import cache
from .models import Product

@shared_task
def update_best_sellers():
    last_30_days = timezone.now() - timedelta(days=30)

    products = Product.objects.annotate(
        total=Sum(
            "saleitem__quantity",
            filter=Q(saleitem__sale__created_at__gte=last_30_days)
        )
    )

    for p in products:
        total_sold = p.total or 0
        is_best = total_sold >= 10

        # update in DB efficiently
        Product.objects.filter(pk=p.pk).update(
            total_sold_30d=total_sold,
            is_best_seller=is_best,
        )

        # invalidate per-club product cache so frontend sees changes
        club_id = getattr(p, "club_id", None)
        if club_id:
            try:
                cache.delete_pattern(f"products:{club_id}:*")
                cache.delete(f"dashboard_summary:{club_id}")
            except Exception:
                # cache backend may not support delete_pattern; ignore failures
                pass