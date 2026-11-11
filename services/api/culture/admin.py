from django.contrib import admin

from .models import CultureItem, FictionalPlace, ItemStatus


@admin.register(CultureItem)
class CultureItemAdmin(admin.ModelAdmin):
    """The curator's review queue: only approved items are used in Life Reports."""

    list_display = ("title", "creator", "kind", "rights", "status", "rights_checked_on")
    list_filter = ("status", "rights", "kind")
    search_fields = ("title", "creator", "subjects")
    actions = ["approve", "reject"]

    @admin.action(description="Approve (use in Life Reports)")
    def approve(self, request, queryset):
        queryset.update(status=ItemStatus.APPROVED)

    @admin.action(description="Don't use")
    def reject(self, request, queryset):
        queryset.update(status=ItemStatus.REJECTED)


@admin.register(FictionalPlace)
class FictionalPlaceAdmin(admin.ModelAdmin):
    list_display = ("name", "work", "real_place", "checked")
    list_filter = ("checked",)
