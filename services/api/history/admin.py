from django.contrib import admin

from .models import (
    Address,
    Assertion,
    AssertionEvidence,
    Decision,
    Event,
    Organisation,
    Person,
    Place,
    Source,
    SourceRecord,
)


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ("name", "access_type", "status_label", "tier", "review_status", "last_checked")
    list_filter = ("access_type", "status_label", "tier", "review_status", "cost")
    search_fields = ("name", "holder", "description", "coverage_area")
    prepopulated_fields = {"key": ("name",)}


@admin.register(SourceRecord)
class SourceRecordAdmin(admin.ModelAdmin):
    list_display = ("title", "source", "date_display", "checked_on", "is_synthetic")
    list_filter = ("source", "is_synthetic", "storage")
    search_fields = ("title", "summary")


class EvidenceInline(admin.TabularInline):
    model = AssertionEvidence
    extra = 0
    autocomplete_fields = ("record",)


@admin.register(Assertion)
class AssertionAdmin(admin.ModelAdmin):
    list_display = ("__str__", "subject", "status", "method", "project")
    list_filter = ("predicate", "status", "method")
    search_fields = ("value", "predicate")
    inlines = [EvidenceInline]


admin.site.register([Place, Organisation, Person, Address, Event, Decision])
