from django.conf import settings
from django.db import models

from core.models import BaseModel


class RelationKind(models.TextChoices):
    PARENT = "parent", "Parent of"
    SPOUSE = "spouse", "Partner of"


class Relationship(BaseModel):
    """A link between two people in a project, with where it came from.
    Like any claim it can be wrong, so it records its source and method."""

    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="+")
    person = models.ForeignKey(
        "history.Person", on_delete=models.CASCADE, related_name="links_from"
    )
    relative = models.ForeignKey(
        "history.Person", on_delete=models.CASCADE, related_name="links_to"
    )
    kind = models.CharField(max_length=10, choices=RelationKind.choices)
    method = models.CharField(max_length=10, default="import")
    source_file = models.ForeignKey(
        "archive.FileAsset", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    external_id = models.CharField(max_length=40, blank=True, help_text="e.g. GEDCOM @F3@")
    fields = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "person", "relative", "kind"], name="unique_relationship"
            )
        ]


class Residence(BaseModel):
    """Where a person was recorded living, with its date as written. From a GEDCOM RESI
    record or added by hand; it says where they were, not when or how they moved."""

    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="+")
    person = models.ForeignKey(
        "history.Person", on_delete=models.CASCADE, related_name="residences"
    )
    place_text = models.CharField(max_length=300, help_text="As written in the source")
    address = models.CharField(max_length=300, blank=True)
    date_text = models.CharField(max_length=100, blank=True)
    year_from = models.IntegerField(null=True, blank=True)
    year_to = models.IntegerField(null=True, blank=True)
    date_precision = models.CharField(max_length=12, default="unknown")
    method = models.CharField(max_length=10, default="import")
    source_file = models.ForeignKey(
        "archive.FileAsset", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    external_id = models.CharField(max_length=60, blank=True, help_text="e.g. GEDCOM @I3@ RESI 2")
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["year_from", "created_at"]


class OverlayKind(models.TextChoices):
    WAR = "war", "Wars"
    LAW = "law", "Laws"
    RECORDS = "records", "Records and censuses"
    CALENDAR = "calendar", "Calendar"
    LOCAL = "local", "Local events"
    CUSTOM = "custom", "Your markers"


class OverlayEvent(BaseModel):
    """Something to see against lives on the Lifeline: a war, a law, a census night, or a
    marker of the user's own. Built-in ones have no project and carry a checked source."""

    project = models.ForeignKey(
        "projects.Project", null=True, blank=True, on_delete=models.CASCADE, related_name="+"
    )
    key = models.SlugField(max_length=80, blank=True)
    kind = models.CharField(max_length=10, choices=OverlayKind.choices)
    title = models.CharField(max_length=200)
    year_from = models.IntegerField()
    year_to = models.IntegerField(null=True, blank=True)
    date_text = models.CharField(max_length=100, blank=True)
    area = models.CharField(
        max_length=100, blank=True, help_text="Where it applied, if not everywhere"
    )
    note = models.TextField(blank=True)
    source_title = models.CharField(max_length=300, blank=True)
    source_url = models.URLField(blank=True)
    checked_on = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["year_from", "title"]
        constraints = [
            models.UniqueConstraint(
                fields=["key"],
                condition=models.Q(project__isnull=True),
                name="unique_builtin_overlay",
            )
        ]


class OverlayPreset(BaseModel):
    """A person's chosen Lifeline layers for a project."""

    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="+")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    kinds = models.JSONField(default=list, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["project", "user"], name="unique_overlay_preset")
        ]


class ExternalId(BaseModel):
    """A person's ID in another system, such as their @I12@ in one family tree. "system"
    names the tree, so a new export of the same tree updates its people instead of adding
    them again, and two trees that both use @I1@ never collide."""

    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="+")
    person = models.ForeignKey(
        "history.Person", on_delete=models.CASCADE, related_name="external_ids"
    )
    system = models.CharField(max_length=80, help_text="e.g. gedcom:<first file's id>")
    external_id = models.CharField(max_length=60)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "system", "external_id"], name="unique_external_id"
            )
        ]


class ChangeKind(models.TextChoices):
    IMPORT = "import", "Import"
    UPDATE = "update", "Update from a new export"
    MERGE = "merge", "Merge"
    DELETE = "delete", "Delete"


class ChangeSet(BaseModel):
    """One bulk change to a tree that can be undone in one step: everything it created,
    changed (with what was there before) and removed (with a full copy)."""

    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="+")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    kind = models.CharField(max_length=10, choices=ChangeKind.choices)
    summary = models.CharField(max_length=300)
    details = models.JSONField(default=dict, blank=True)
    items = models.JSONField(default=list, blank=True)
    undone_at = models.DateTimeField(null=True, blank=True)
    undone_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["-created_at"]


class GalleryItem(BaseModel):
    """A picture from the project's Archive placed in family galleries: a photo, or an
    image of a document. One picture can be tagged to several people."""

    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="+")
    file = models.ForeignKey("archive.FileAsset", on_delete=models.CASCADE, related_name="+")
    caption = models.CharField(max_length=500, blank=True)
    date_text = models.CharField(
        max_length=100, blank=True, help_text="As known, e.g. 'about 1920'"
    )
    year = models.IntegerField(null=True, blank=True, help_text="For ordering by decade")
    place_text = models.CharField(max_length=300, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["project", "file"], name="unique_gallery_file")
        ]


class TagRelation(models.TextChoices):
    SHOWS = "shows", "Shows them"
    ABOUT = "about", "About them (a document or record)"
    CONTEXT = "context", "Their world (not them)"


class GalleryTag(BaseModel):
    """Who a picture is linked to, how, and where it sits in their gallery."""

    item = models.ForeignKey(GalleryItem, on_delete=models.CASCADE, related_name="tags")
    person = models.ForeignKey("history.Person", on_delete=models.CASCADE, related_name="+")
    relation = models.CharField(
        max_length=10, choices=TagRelation.choices, default=TagRelation.SHOWS
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "created_at"]
        constraints = [
            models.UniqueConstraint(fields=["item", "person"], name="unique_gallery_tag")
        ]


class ExplanationStatus(models.TextChoices):
    PROPOSED = "proposed", "Waiting for review"
    REVIEWED = "reviewed", "Reviewed"
    REJECTED = "rejected", "Not used"


class Explanation(BaseModel):
    """An explanation of a term, institution or record type written by a user, archivist
    or historian, with credit. It's shown in "Explain this record" only once reviewed,
    and says who wrote it."""

    term = models.CharField(max_length=200)
    also = models.JSONField(default=list, blank=True, help_text="Other words that mean it")
    meaning = models.TextField()
    may_mean = models.TextField(blank=True)
    where_to_look = models.TextField(blank=True)
    area = models.CharField(max_length=200, blank=True)
    period_from = models.IntegerField(null=True, blank=True)
    period_to = models.IntegerField(null=True, blank=True)
    sources = models.JSONField(default=list, blank=True, help_text='[{"title": "", "url": ""}]')
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    credit = models.CharField(max_length=200, help_text="How they'd like to be credited")
    status = models.CharField(
        max_length=10, choices=ExplanationStatus.choices, default=ExplanationStatus.PROPOSED
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["term"]
