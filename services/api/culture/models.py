from django.conf import settings
from django.db import models

from core.models import BaseModel


class Rights(models.TextChoices):
    OPEN = "open", "Open: can be shown"
    LINK_ONLY = "link_only", "Link only"
    PERMISSION = "permission", "Permission needed"


class ItemStatus(models.TextChoices):
    PROPOSED = "proposed", "Waiting for a curator"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Not used"


class CultureItem(BaseModel):
    """An artwork, photograph, poem, rhyme, ballad or story from a person's world. It shows
    their world, never them. Rights decide whether it's shown, linked or quoted; only
    items a curator has approved are used."""

    key = models.SlugField(max_length=80, unique=True)
    kind = models.CharField(max_length=20)  # print, painting, photograph, rhyme, ballad...
    title = models.CharField(max_length=300)
    creator = models.CharField(max_length=300, blank=True)
    made_text = models.CharField(max_length=100, blank=True, help_text="As the holder gives it")
    made_from = models.IntegerField(null=True, blank=True)
    made_to = models.IntegerField(null=True, blank=True)
    country = models.CharField(max_length=100, blank=True, help_text="Where it was made")
    places = models.JSONField(default=list, blank=True, help_text="Places it shows or names")
    subjects = models.JSONField(default=list, blank=True, help_text="What it shows")
    description = models.TextField(blank=True, help_text="In our words, from the holder")
    text = models.TextField(blank=True, help_text="For public domain texts: the words")
    image_url = models.URLField(blank=True)
    source_name = models.CharField(max_length=200)
    source_url = models.URLField()
    licence = models.CharField(max_length=200)
    rights = models.CharField(max_length=12, choices=Rights.choices)
    credit = models.CharField(max_length=500)
    rights_checked_on = models.DateField()
    status = models.CharField(
        max_length=10, choices=ItemStatus.choices, default=ItemStatus.PROPOSED
    )

    class Meta:
        ordering = ["made_from", "title"]


class FictionalPlace(BaseModel):
    """A place in fiction linked to a real one (e.g. one of Hardy's Wessex names). Only
    used once checked against a reliable source."""

    name = models.CharField(max_length=200)
    work = models.CharField(max_length=300)
    author = models.CharField(max_length=200)
    real_place = models.CharField(max_length=200)
    confidence = models.CharField(max_length=100, blank=True, help_text="e.g. 'or possibly X'")
    sources = models.JSONField(default=list, blank=True)
    checked = models.BooleanField(default=False)


class LifeReport(BaseModel):
    """A saved Life Report: the blocks as the user edited them, and the culture items used."""

    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="+")
    person = models.ForeignKey("history.Person", on_delete=models.CASCADE, related_name="+")
    length = models.CharField(max_length=10, default="short")
    blocks = models.JSONField(default=list)
    items = models.JSONField(default=list, help_text="Keys of culture items used")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["-created_at"]
