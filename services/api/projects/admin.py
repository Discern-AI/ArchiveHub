from django.contrib import admin

from .models import Chat, Message, Project, ProjectMember


class MemberInline(admin.TabularInline):
    model = ProjectMember
    extra = 0


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "visibility", "updated_at")
    inlines = [MemberInline]


@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ("__str__", "owner", "project", "updated_at")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("chat", "role", "status", "model", "created_at")
    list_filter = ("role", "status")
