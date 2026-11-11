from django.conf import settings
from django.db import models

from core.models import BaseModel


class PageStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PUBLISHED = "published", "Published"
    UNPUBLISHED = "unpublished", "Taken down"


class Homepage(BaseModel):
    """Someone's public home on ArchiveHub: an about page, posts and collections. Nothing
    on it is public until it's switched on and each post is approved."""

    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="homepage"
    )
    slug = models.SlugField(max_length=60, unique=True)
    title = models.CharField(max_length=200)
    tagline = models.CharField(max_length=300, blank=True)
    about = models.TextField(blank=True)
    live = models.BooleanField(default=False)


class Source(models.TextChoices):
    WRITTEN = "written", "Written here"
    CHAT = "chat", "Drafted in chat"
    WORDPRESS = "wordpress", "Imported from WordPress"


class Post(BaseModel):
    homepage = models.ForeignKey(Homepage, on_delete=models.CASCADE, related_name="posts")
    title = models.CharField(max_length=300)
    slug = models.SlugField(max_length=120)
    summary = models.CharField(max_length=500, blank=True)
    body = models.TextField(blank=True, help_text="A small Markdown subset; see render.py")
    status = models.CharField(max_length=12, choices=PageStatus.choices, default=PageStatus.DRAFT)
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.WRITTEN)
    published_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    approved_check = models.JSONField(default=dict, blank=True, help_text="The check at approval")
    # When the same post appears in two places, one is the original.
    original_url = models.URLField(blank=True, help_text="Where the original is, if elsewhere")
    first_published = models.DateTimeField(null=True, blank=True, help_text="As on the original")

    class Meta:
        ordering = ["-published_at", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["homepage", "slug"], name="unique_post_slug")
        ]


class ImageRights(models.TextChoices):
    OWN = "own", "I took or made it"
    PERMISSION = "permission", "I have permission"
    PUBLIC_DOMAIN = "public_domain", "Public domain or openly licensed"
    UNCLEAR = "unclear", "Not sure"


class PostImage(BaseModel):
    """A picture from the Archive used in a post, with its rights stated before publishing."""

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="images")
    file = models.ForeignKey("archive.FileAsset", on_delete=models.CASCADE, related_name="+")
    caption = models.CharField(max_length=500, blank=True)
    rights = models.CharField(
        max_length=15, choices=ImageRights.choices, default=ImageRights.UNCLEAR
    )
    credit = models.CharField(max_length=300, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["post", "file"], name="unique_post_image")]


class Redirect(BaseModel):
    """An old address (e.g. from a WordPress blog) that now points at a post here."""

    homepage = models.ForeignKey(Homepage, on_delete=models.CASCADE, related_name="redirects")
    old_path = models.CharField(max_length=500)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="+")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["homepage", "old_path"], name="unique_redirect")
        ]
