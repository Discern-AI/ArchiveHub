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


class LocationStatus(models.TextChoices):
    SUGGESTED = "suggested", "Suggested"
    CONFIRMED = "confirmed", "Confirmed"
    REJECTED = "rejected", "Wrong place"
    NOT_FOUND = "not_found", "Not found"


class PlaceLocation(BaseModel):
    """Where a place written in a family tree is, as suggested by a source or set by a person.

    A suggestion is never treated as certain: it says where it came from and how precise
    it is, and a person can confirm it, reject it or put it somewhere else.
    """

    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="place_locations"
    )
    text = models.CharField(max_length=300, help_text="The place as written in the tree")
    text_key = models.CharField(max_length=300)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    precision = models.CharField(
        max_length=10, choices=GeocodePrecision.choices, default=GeocodePrecision.UNKNOWN
    )
    source = models.CharField(max_length=300, blank=True)
    method = models.CharField(max_length=20, blank=True)  # place | old-map-names | geonames | user
    candidates = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=10, choices=LocationStatus.choices, default=LocationStatus.SUGGESTED
    )
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["text"]
        constraints = [
            models.UniqueConstraint(fields=["project", "text_key"], name="unique_place_text")
        ]

    def __str__(self) -> str:
        return self.text
