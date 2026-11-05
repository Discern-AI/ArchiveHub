"""The shared historical data layer (SPEC §8).

Source records are evidence. Assertions are claims about the world, linked to evidence.
They are kept apart (ADR-005): conflicting claims coexist until a person decides, and an
AI summary is never a source.
"""

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from core.models import BaseModel, Visibility


class DatePrecision(models.TextChoices):
    EXACT = "exact", "Exact date"
    YEAR = "year", "Year"
    DECADE = "decade", "Decade"
    APPROXIMATE = "approximate", "Approximate"
    RANGE = "range", "Range"
    BEFORE = "before", "Before"
    AFTER = "after", "After"
    UNKNOWN = "unknown", "Unknown"


class DatedMixin(models.Model):
    """Dates as historians record them: original wording kept, years for searching."""

    date_text = models.CharField(max_length=100, blank=True, help_text="As written in the source")
    year_from = models.IntegerField(null=True, blank=True)
    year_to = models.IntegerField(null=True, blank=True)
    date_precision = models.CharField(
        max_length=12, choices=DatePrecision.choices, default=DatePrecision.UNKNOWN
    )

    class Meta:
        abstract = True

    @property
    def date_display(self) -> str:
        if self.date_text:
            return self.date_text
        if self.year_from and self.year_to and self.year_from != self.year_to:
            return f"{self.year_from}–{self.year_to}"
        return str(self.year_from or self.year_to or "")


# --- Sources and the source directory --------------------------------------------


class AccessType(models.TextChoices):
    HOSTED = "hosted", "Hosted here"
    LIVE_API = "live_api", "Searched live"
    METADATA = "metadata", "Metadata only"
    EXTERNAL_ONLY = "external_only", "Link-out only"


class StoragePolicy(models.TextChoices):
    FULL_COPY = "full_copy", "Full copy allowed"
    METADATA_ONLY = "metadata_only", "Metadata only"
    REFERENCE_ONLY = "reference_only", "Our own facts and a link"
    NONE = "none", "Nothing stored"


class StatusLabel(models.TextChoices):
    """Data status labels shown in the product (SPEC §8)."""

    CONFIRMED_LIVE_API = "confirmed_live_api", "Confirmed live API"
    VERIFIED_METADATA = "verified_metadata_service", "Verified metadata service"
    POTENTIAL = "potential_integration", "Potential integration"
    EXTERNAL_ONLY = "external_only", "Link-out only"
    DOWNLOADABLE = "downloadable_dataset", "Downloadable dataset"
    PARTNER = "partner_collection", "Partner collection"
    REFERENCE = "checked_reference", "Checked reference facts"
    FIXTURE = "prototype_fixture", "Synthetic test data"


class ReviewStatus(models.TextChoices):
    PAGE_READ = "page_read", "Terms page read"
    PARTLY = "partly_checked", "Partly checked"
    NOT_CHECKED = "not_checked", "Not yet checked"


class Cost(models.TextChoices):
    FREE = "free", "Free"
    PAID = "paid", "Paid"
    MIXED = "mixed", "Free and paid"
    UNKNOWN = "unknown", "Unknown"


class Source(BaseModel):
    """A database, website, archive, book or other source. Also the source directory entry."""

    key = models.SlugField(max_length=80, unique=True)
    name = models.CharField(max_length=200)
    kind = models.CharField(max_length=30, default="database")
    holder = models.CharField(max_length=200, blank=True)
    url = models.URLField(max_length=500, blank=True)
    description = models.TextField(blank=True)
    coverage_area = models.CharField(max_length=200, blank=True)
    period_from = models.IntegerField(null=True, blank=True)
    period_to = models.IntegerField(null=True, blank=True)
    record_types = models.JSONField(default=list, blank=True)
    tags = models.JSONField(default=list, blank=True)
    access_type = models.CharField(
        max_length=20, choices=AccessType.choices, default=AccessType.EXTERNAL_ONLY
    )
    cost = models.CharField(max_length=10, choices=Cost.choices, default=Cost.UNKNOWN)
    api_status = models.CharField(max_length=200, blank=True)
    licence = models.CharField(max_length=200, blank=True)
    conditions = models.TextField(blank=True, help_text="Reuse conditions found")
    storage_policy = models.CharField(
        max_length=20, choices=StoragePolicy.choices, default=StoragePolicy.NONE
    )
    attribution = models.CharField(max_length=300, blank=True)
    contact = models.CharField(max_length=200, blank=True)
    status_label = models.CharField(
        max_length=30, choices=StatusLabel.choices, default=StatusLabel.EXTERNAL_ONLY
    )
    tier = models.CharField(max_length=5, blank=True, help_text="A–D from the Blueprint")
    review_status = models.CharField(
        max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.NOT_CHECKED
    )
    plan = models.CharField(max_length=300, blank=True)
    last_checked = models.DateField(null=True, blank=True)
    next_action_owner = models.CharField(max_length=100, blank=True)
    scores = models.JSONField(default=dict, blank=True, help_text="Acceptance scorecard, 0–5")

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class SourceRecord(DatedMixin, BaseModel):
    """One entry in a source. For reference-only sources, `summary` is our own wording."""

    key = models.SlugField(max_length=100, unique=True)
    source = models.ForeignKey(Source, on_delete=models.PROTECT, related_name="records")
    external_id = models.CharField(max_length=200, blank=True)
    title = models.CharField(max_length=300)
    url = models.URLField(max_length=500, blank=True)
    record_type = models.CharField(max_length=60, blank=True)
    summary = models.TextField(blank=True)
    place = models.ForeignKey(
        "Place", null=True, blank=True, on_delete=models.SET_NULL, related_name="records"
    )
    fields = models.JSONField(default=dict, blank=True)
    storage = models.CharField(
        max_length=20, choices=StoragePolicy.choices, default=StoragePolicy.REFERENCE_ONLY
    )
    checked_on = models.DateField(null=True, blank=True)
    checked_note = models.CharField(max_length=300, blank=True)
    is_synthetic = models.BooleanField(default=False)

    class Meta:
        ordering = ["source__name", "title"]

    def __str__(self) -> str:
        return self.title


# --- Things in the world ----------------------------------------------------------


class GeocodePrecision(models.TextChoices):
    EXACT = "exact", "Exact"
    STREET = "street", "Street"
    PARISH = "parish", "Parish"
    TOWN = "town", "Town"
    INFERRED = "inferred", "Inferred"
    UNKNOWN = "unknown", "Unknown"


class Place(BaseModel):
    """A location that changes over time. Coordinates until WP6 (ADR-019)."""

    key = models.SlugField(max_length=80, unique=True)
    name = models.CharField(max_length=200)
    kind = models.CharField(max_length=30, default="place")
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children"
    )
    alt_names = models.JSONField(default=list, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    geocode_precision = models.CharField(
        max_length=10, choices=GeocodePrecision.choices, default=GeocodePrecision.UNKNOWN
    )
    valid_from = models.IntegerField(null=True, blank=True)
    valid_to = models.IntegerField(null=True, blank=True)
    note = models.TextField(blank=True)

    def __str__(self) -> str:
        return f"{self.name}, {self.parent.name}" if self.parent else self.name


class Organisation(BaseModel):
    """A pub, business, society, regiment or similar."""

    key = models.SlugField(max_length=80, unique=True)
    name = models.CharField(max_length=200)
    kind = models.CharField(max_length=30, default="organisation")
    alt_names = models.JSONField(default=list, blank=True)
    place = models.ForeignKey(
        Place, null=True, blank=True, on_delete=models.SET_NULL, related_name="organisations"
    )
    note = models.TextField(blank=True)

    def __str__(self) -> str:
        return self.name


class LivingStatus(models.TextChoices):
    UNKNOWN = "unknown", "Unknown"
    LIVING = "living", "Living"
    DECEASED = "deceased", "Deceased"


class Person(BaseModel):
    """A person across records. Living people are private by default (ADR-015)."""

    key = models.SlugField(max_length=80, unique=True, null=True, blank=True)
    name = models.CharField(max_length=200)
    alt_names = models.JSONField(default=list, blank=True)
    birth_text = models.CharField(max_length=100, blank=True)
    death_text = models.CharField(max_length=100, blank=True)
    living_status = models.CharField(
        max_length=10, choices=LivingStatus.choices, default=LivingStatus.UNKNOWN
    )
    visibility = models.CharField(
        max_length=20, choices=Visibility.choices, default=Visibility.PRIVATE
    )

    class Meta:
        verbose_name_plural = "people"

    def __str__(self) -> str:
        return self.name


class Address(DatedMixin, BaseModel):
    """A street address at a point in time; modern numbering may not match."""

    street = models.ForeignKey(Place, on_delete=models.CASCADE, related_name="addresses")
    number = models.CharField(max_length=20, blank=True)
    note = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "addresses"

    def __str__(self) -> str:
        return f"{self.number} {self.street.name}".strip()


class Event(DatedMixin, BaseModel):
    """Anything dated: a birth, a move, a closure, a talk."""

    kind = models.CharField(max_length=40)
    title = models.CharField(max_length=300, blank=True)
    place = models.ForeignKey(Place, null=True, blank=True, on_delete=models.SET_NULL)
    organisation = models.ForeignKey(Organisation, null=True, blank=True, on_delete=models.SET_NULL)
    people = models.ManyToManyField(Person, blank=True, related_name="events")

    def __str__(self) -> str:
        return self.title or self.kind


# --- Claims and evidence ----------------------------------------------------------


class ClaimStatus(models.TextChoices):
    DOCUMENTED = "documented", "Documented"
    REMEMBERED = "remembered", "Remembered"
    INFERRED = "inferred", "Inferred"
    DISPUTED = "disputed", "Disputed"


class Method(models.TextChoices):
    IMPORT = "import", "Imported / curated"
    USER = "user", "Entered by a person"
    AI = "ai", "Suggested by AI"


class Assertion(DatedMixin, BaseModel):
    """A claim about a person, place, organisation or event.

    Shared reference claims have no project. Project claims are private to that project.
    """

    key = models.SlugField(max_length=100, unique=True, null=True, blank=True)
    subject_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    subject_id = models.UUIDField()
    subject = GenericForeignKey("subject_type", "subject_id")
    predicate = models.CharField(max_length=60)
    value = models.TextField()
    status = models.CharField(
        max_length=12, choices=ClaimStatus.choices, default=ClaimStatus.DOCUMENTED
    )
    confidence = models.CharField(max_length=10, default="unknown")
    method = models.CharField(max_length=10, choices=Method.choices, default=Method.IMPORT)
    project = models.ForeignKey("projects.Project", null=True, blank=True, on_delete=models.CASCADE)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    note = models.TextField(blank=True)

    class Meta:
        indexes = [models.Index(fields=["subject_type", "subject_id", "predicate"])]

    def __str__(self) -> str:
        return f"{self.predicate}: {self.value}"


class Stance(models.TextChoices):
    SUPPORTS = "supports", "Supports"
    DISPUTES = "disputes", "Disputes"
    MENTIONS = "mentions", "Mentions"


class AssertionEvidence(BaseModel):
    assertion = models.ForeignKey(Assertion, on_delete=models.CASCADE, related_name="evidence")
    record = models.ForeignKey(SourceRecord, on_delete=models.PROTECT, related_name="evidence")
    stance = models.CharField(max_length=10, choices=Stance.choices, default=Stance.SUPPORTS)
    note = models.TextField(blank=True, help_text="What the record says, in our words")
    suggested_weight = models.CharField(max_length=12, blank=True)
    weight_by = models.CharField(max_length=10, blank=True, help_text="ai, editor or user")
    weight_note = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "assertion evidence"
        constraints = [
            models.UniqueConstraint(fields=["assertion", "record"], name="unique_evidence")
        ]


class Decision(BaseModel):
    """What a project uses for a question. 'Use' doesn't mean 'true'; nothing is deleted."""

    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE)
    subject_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    subject_id = models.UUIDField()
    subject = GenericForeignKey("subject_type", "subject_id")
    predicate = models.CharField(max_length=60)
    chosen = models.ForeignKey(
        Assertion, null=True, blank=True, on_delete=models.SET_NULL, related_name="decisions"
    )
    keep_disputed = models.BooleanField(default=False)
    reason = models.TextField(blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "subject_type", "subject_id", "predicate"],
                name="one_decision_per_question",
            )
        ]
