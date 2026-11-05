"""Datasets hosted by ArchiveHub (access type "hosted"). Rows keep their provider ID."""

from django.db import models

from core.models import BaseModel


class Dataset(BaseModel):
    key = models.SlugField(max_length=80, unique=True)
    name = models.CharField(max_length=200)
    source = models.ForeignKey("history.Source", on_delete=models.PROTECT, related_name="datasets")
    description = models.TextField(blank=True)
    licence = models.CharField(max_length=200)
    citation = models.CharField(max_length=500, help_text="How to cite the original data")
    original_file = models.CharField(max_length=300, blank=True)
    original_sha256 = models.CharField(max_length=64, blank=True)
    import_scope = models.CharField(max_length=300, blank=True)
    row_count = models.PositiveIntegerField(default=0)
    imported_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return self.name


class DatasetRow(models.Model):
    """One record in a hosted dataset. Lean on purpose: millions of rows are possible."""

    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name="rows")
    external_id = models.CharField(max_length=64)
    title = models.CharField(max_length=400)
    title_lower = models.CharField(max_length=400, db_index=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    fields = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["dataset", "external_id"], name="unique_dataset_row")
        ]
        indexes = [
            models.Index(fields=["dataset", "title_lower", "id"]),
            models.Index(fields=["dataset", "latitude", "longitude"]),
        ]

    def __str__(self) -> str:
        return self.title
