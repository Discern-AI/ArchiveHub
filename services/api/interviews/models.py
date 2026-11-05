"""Live guided interviews (SPEC §4). The original audio and the full transcript are the
evidence; notes and questions picked up by the assistant are interpretation, stored
separately and always linked back to transcript lines."""

import uuid

from django.conf import settings
from django.db import models

from core.models import BaseModel

# Shown before recording starts and stored with the consent record, word for word.
RECORDING_NOTICE = (
    "This interview will be recorded and transcribed. Before you start, tell anyone else "
    "who will be speaking that they're being recorded, and check they're happy to be. "
    "The recording stays private to this chat and its project."
)


def audio_path(instance: "InterviewSession", filename: str) -> str:
    return f"interviews/{instance.chat_id}/{uuid.uuid4().hex}.wav"


class SessionStatus(models.TextChoices):
    READY = "ready", "Ready to record"
    RECORDING = "recording", "Recording"
    PAUSED = "paused", "Paused"
    INTERRUPTED = "interrupted", "Connection lost (recording kept)"
    ENDED = "ended", "Ended"


class InterviewSession(BaseModel):
    chat = models.ForeignKey("projects.Chat", on_delete=models.CASCADE, related_name="interviews")
    started_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    narrator = models.CharField(max_length=120)
    interviewer = models.CharField(max_length=120, blank=True)
    # Consent: who confirmed, when, and the exact notice they saw.
    consent_confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    consent_confirmed_at = models.DateTimeField()
    consent_notice = models.TextField()
    status = models.CharField(
        max_length=12, choices=SessionStatus.choices, default=SessionStatus.READY
    )
    ended_at = models.DateTimeField(null=True, blank=True)
    duration_ms = models.PositiveIntegerField(default=0)
    # The original recording: 16 kHz mono 16-bit PCM WAV, never altered after it's saved.
    audio = models.FileField(upload_to=audio_path, blank=True)
    audio_size = models.PositiveBigIntegerField(default=0)
    audio_sha256 = models.CharField(max_length=64, blank=True)
    speech_engine = models.CharField(max_length=100, blank=True)
    analysis_model = models.CharField(max_length=100, blank=True)
    analysis_input_tokens = models.PositiveIntegerField(default=0)
    analysis_output_tokens = models.PositiveIntegerField(default=0)
    # The chat messages written by "End and send".
    transcript_message = models.ForeignKey(
        "projects.Message", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    response_message = models.ForeignKey(
        "projects.Message", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Interview with {self.narrator}"


class Segment(BaseModel):
    """One finished line of transcript, with where it sits in the recording."""

    session = models.ForeignKey(InterviewSession, on_delete=models.CASCADE, related_name="segments")
    line = models.PositiveIntegerField()
    start_ms = models.PositiveIntegerField()
    end_ms = models.PositiveIntegerField()
    text = models.TextField()
    speaker = models.CharField(max_length=120)
    engine = models.CharField(max_length=100)

    class Meta:
        ordering = ["line"]
        constraints = [
            models.UniqueConstraint(fields=["session", "line"], name="unique_segment_line")
        ]


class NoteKind(models.TextChoices):
    PERSON = "person", "Person"
    PLACE = "place", "Place"
    DATE = "date", "Date"
    QUESTION = "question", "Question"


class NoteStatus(models.TextChoices):
    OPEN = "open", "Open"
    ANSWERED = "answered", "Answered"
    DISMISSED = "dismissed", "Dismissed"


class Note(BaseModel):
    """Something the assistant picked up (a person, place or date) or a follow-up question.
    Interpretation only: it points at the transcript lines it came from."""

    session = models.ForeignKey(InterviewSession, on_delete=models.CASCADE, related_name="notes")
    kind = models.CharField(max_length=10, choices=NoteKind.choices)
    text = models.CharField(max_length=300)
    detail = models.CharField(max_length=300, blank=True)
    lines = models.JSONField(default=list)
    status = models.CharField(max_length=10, choices=NoteStatus.choices, default=NoteStatus.OPEN)

    class Meta:
        ordering = ["created_at"]
