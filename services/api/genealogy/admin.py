from django.contrib import admin
from django.utils import timezone

from .models import Explanation, ExplanationStatus


@admin.register(Explanation)
class ExplanationAdmin(admin.ModelAdmin):
    """Editors review explanations people have offered before they're shown."""

    list_display = ("term", "credit", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("term", "meaning", "credit")
    actions = ["mark_reviewed", "mark_rejected"]

    @admin.action(description="Mark as reviewed (show in Explain this record)")
    def mark_reviewed(self, request, queryset):
        queryset.update(
            status=ExplanationStatus.REVIEWED, reviewed_by=request.user, reviewed_at=timezone.now()
        )

    @admin.action(description="Don't use")
    def mark_rejected(self, request, queryset):
        queryset.update(status=ExplanationStatus.REJECTED, reviewed_by=request.user)
