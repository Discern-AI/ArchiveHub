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
