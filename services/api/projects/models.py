from django.conf import settings
from django.db import models

from core.models import BaseModel, Visibility


class Project(BaseModel):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="owned_projects"
    )
    title = models.CharField(max_length=200)
    summary = models.TextField(blank=True)
    visibility = models.CharField(
        max_length=20, choices=Visibility.choices, default=Visibility.PRIVATE
    )

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return self.title


class Role(models.TextChoices):
    OWNER = "owner", "Owner"
    EDITOR = "editor", "Editor"
    VIEWER = "viewer", "Viewer"


class ProjectMember(BaseModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.VIEWER)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["project", "user"], name="unique_project_member")
        ]


class Chat(BaseModel):
    """A conversation. Belongs to a project, or stands alone (project is null)."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chats"
    )
    project = models.ForeignKey(
        Project, null=True, blank=True, on_delete=models.CASCADE, related_name="chats"
    )
    title = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return self.title or f"Chat {self.pk}"


class MessageRole(models.TextChoices):
    USER = "user", "User"
    ASSISTANT = "assistant", "Assistant"


class MessageStatus(models.TextChoices):
    STREAMING = "streaming", "Streaming"
    COMPLETE = "complete", "Complete"
    INCOMPLETE = "incomplete", "Incomplete"  # stream interrupted; partial text kept
    REFUSED = "refused", "Refused"
    ERROR = "error", "Error"


class Message(BaseModel):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=10, choices=MessageRole.choices)
    content = models.TextField(blank=True)
    # Full assistant content blocks as returned by the API, replayed unchanged on later turns.
    raw_content = models.JSONField(null=True, blank=True)
    # Every API message in this reply, including tool calls and results (append-only replay).
    turns = models.JSONField(null=True, blank=True)
    # Built by the server from tool calls, never from the model's text (ADR-020).
    checked = models.JSONField(default=list, blank=True)
    sources = models.JSONField(default=list, blank=True)
    status = models.CharField(
        max_length=12, choices=MessageStatus.choices, default=MessageStatus.COMPLETE
    )
    model = models.CharField(max_length=100, blank=True)
    input_tokens = models.PositiveIntegerField(null=True, blank=True)
    output_tokens = models.PositiveIntegerField(null=True, blank=True)
    error = models.TextField(blank=True)

    class Meta:
        ordering = ["created_at"]
