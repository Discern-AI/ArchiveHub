from django.conf import settings
from django.db import models

from core.models import BaseModel


class OrderRoute(models.TextChoices):
    REFERRAL = "referral", "You order from the holder; we keep track"
    ORDER_FOR_USER = "order_for_user", "We order it for you"
    PARTNER = "partner", "Sold through a partner"
    AGENT = "agent", "A local researcher finds it"


class OrderStatus(models.TextChoices):
    PLANNED = "planned", "Not ordered yet"
    ORDERED = "ordered", "Ordered"
    RECEIVED = "received", "Received"
    CANCELLED = "cancelled", "Cancelled"


class RecordOrder(BaseModel):
    """A paid record someone wants: what it is, who holds it, what it should show, every
    fee shown separately, how long it takes, and the record once it arrives. Only routes
    the holder allows are offered; to start with, ArchiveHub refers people to the holder
    and keeps track (it doesn't take payment)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    project = models.ForeignKey(
        "projects.Project", null=True, blank=True, on_delete=models.CASCADE, related_name="+"
    )
    person = models.ForeignKey(
        "history.Person", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    offer_key = models.CharField(max_length=60)
    title = models.CharField(max_length=300, help_text="e.g. Birth certificate of Arthur Sample")
    holder = models.CharField(max_length=200)
    should_show = models.TextField(blank=True)
    route = models.CharField(max_length=20, choices=OrderRoute.choices)
    fees = models.JSONField(default=list, help_text='[{"label": "GRO fee", "pence": 1250}]')
    delivery = models.CharField(max_length=200, blank=True)
    url = models.URLField(blank=True)
    rights_label = models.CharField(max_length=300, blank=True)
    details = models.JSONField(default=dict, blank=True, help_text="e.g. GRO index reference")
    status = models.CharField(
        max_length=10, choices=OrderStatus.choices, default=OrderStatus.PLANNED
    )
    reference = models.CharField(max_length=100, blank=True, help_text="The holder's order ref")
    ordered_at = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    file = models.ForeignKey(
        "archive.FileAsset", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
