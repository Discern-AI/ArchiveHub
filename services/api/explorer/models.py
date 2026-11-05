from django.conf import settings
from django.db import models

from core.models import BaseModel


class BasketItem(BaseModel):
    """A record saved to a project. A full copy is kept only if the source allows it;
    otherwise just the reference and link (SPEC §5)."""

    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="basket")
    connector = models.CharField(max_length=40)
    external_id = models.CharField(max_length=100)
    title = models.CharField(max_length=400)
    url = models.URLField(max_length=500, blank=True)
    storage = models.CharField(max_length=20)
    snapshot = models.JSONField(null=True, blank=True)
    note = models.TextField(blank=True)
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "connector", "external_id"], name="unique_basket_item"
            )
        ]

    def __str__(self) -> str:
        return self.title
