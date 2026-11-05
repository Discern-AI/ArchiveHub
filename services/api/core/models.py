import uuid

from django.conf import settings
from django.db import models


class BaseModel(models.Model):
    """UUID primary key and timestamps for every ArchiveHub model."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Visibility(models.TextChoices):
    PRIVATE = "private", "Private"
    SHARED = "shared", "Shared with specified users"
    ORGANISATION = "organisation", "Organisation"
    PUBLIC = "public", "Public"
    RESTRICTED = "restricted", "Restricted"


class AuditLog(models.Model):
    """Who changed what. Never store private content here, only references."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    action = models.CharField(max_length=64)
    object_type = models.CharField(max_length=64)
    object_id = models.CharField(max_length=64)
    data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.action} {self.object_type}:{self.object_id}"


def audit(actor, action: str, obj: models.Model, **data) -> AuditLog:
    return AuditLog.objects.create(
        actor=actor,
        action=action,
        object_type=obj._meta.label_lower,
        object_id=str(obj.pk),
        data=data,
    )
