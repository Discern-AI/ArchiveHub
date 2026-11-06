"""Things a project has placed on the time map: memories, photos, documents and
interview passages. They belong to a project and are private to it, like the Archive.

An item's date says what kind of date it is (SPEC §5, Time map): when something
happened is not the same as when a photo was taken or a document was written.
"""

from django.conf import settings
from django.db import models

from core.models import BaseModel
from history.models import DatedMixin, GeocodePrecision


class ItemKind(models.TextChoices):
    MEMORY = "memory", "Memory"
    PHOTO = "photo", "Photo"
    DOCUMENT = "document", "Document"
    INTERVIEW = "interview", "Interview passage"


class DateRole(models.TextChoices):
    EVENT = "event", "When it happened"
    MADE = "made", "When it was made, taken or written"


class MapItem(DatedMixin, BaseModel):
    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="map_items"
    )
    kind = models.CharField(max_length=10, choices=ItemKind.choices)
    title = models.CharField(max_length=200)
    text = models.TextField(blank=True, help_text="The person's own words")
    file = models.ForeignKey(
        "archive.FileAsset", null=True, blank=True, on_delete=models.CASCADE, related_name="+"
    )
    interview = models.ForeignKey(
        "interviews.InterviewSession",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="+",
    )
    lines = models.JSONField(default=list, blank=True, help_text="Transcript line numbers")
    place = models.ForeignKey(
        "history.Place", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    latitude = models.FloatField()
    longitude = models.FloatField()
    geocode_precision = models.CharField(
        max_length=10, choices=GeocodePrecision.choices, default=GeocodePrecision.INFERRED
    )
    location_note = models.CharField(max_length=300, blank=True)
    date_role = models.CharField(max_length=10, choices=DateRole.choices, default=DateRole.EVENT)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["year_from", "title"]
        indexes = [
            models.Index(fields=["latitude", "longitude"]),
            models.Index(fields=["project", "year_from"]),
        ]

    def __str__(self) -> str:
        return self.title
