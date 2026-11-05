"""The single place that decides who can see or change projects and chats.

Every query for projects, chats or messages goes through these helpers, so a
permission bug can't hide in one endpoint.
"""

from django.db.models import Q, QuerySet

from .models import Chat, Project, Role

EDIT_ROLES = (Role.OWNER, Role.EDITOR)


def visible_projects(user) -> QuerySet[Project]:
    return Project.objects.filter(Q(owner=user) | Q(members__user=user)).distinct()


def editable_projects(user) -> QuerySet[Project]:
    return Project.objects.filter(
        Q(owner=user) | Q(members__user=user, members__role__in=EDIT_ROLES)
    ).distinct()


def visible_chats(user) -> QuerySet[Chat]:
    return Chat.objects.filter(
        Q(owner=user, project__isnull=True)
        | Q(project__owner=user)
        | Q(project__members__user=user)
    ).distinct()


def writable_chats(user) -> QuerySet[Chat]:
    """Chats the user may post to: their own loose chats, or chats in projects they can edit."""
    return Chat.objects.filter(
        Q(owner=user, project__isnull=True)
        | Q(project__owner=user)
        | Q(project__members__user=user, project__members__role__in=EDIT_ROLES)
    ).distinct()
