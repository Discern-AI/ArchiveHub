"""Streaming chat endpoint: POST a message, receive the reply as server-sent events.

Events: `start` (message ids), `delta` (text chunks), `done` (final message) or `error`.
Both messages are saved before streaming starts, and the assistant message is saved
again however the stream ends, so an interrupted reply keeps its partial text.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

from django.http import HttpRequest, HttpResponse, JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_POST

from projects.models import Chat, Message, MessageRole, MessageStatus
from projects.permissions import writable_chats

from .providers import FinalReply, TextDelta, get_provider, replayable_content

logger = logging.getLogger(__name__)
MAX_MESSAGE_CHARS = 20_000


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _message_json(m: Message) -> dict[str, Any]:
    return {
        "id": str(m.id),
        "role": m.role,
        "content": m.content,
        "status": m.status,
        "created_at": m.created_at.isoformat(),
    }


async def build_history(chat: Chat) -> list[dict[str, Any]]:
    """The full conversation, append-only, in API format.

    Turns are never trimmed or rewritten: editing earlier turns would invalidate the
    model's earlier reasoning and the prompt cache. Assistant turns that produced
    nothing (errors) are skipped; they never had content to replay.
    """
    history: list[dict[str, Any]] = []
    async for m in Message.objects.filter(chat=chat).order_by("created_at"):
        if m.role == MessageRole.USER:
            history.append({"role": "user", "content": m.content})
        elif m.raw_content:
            history.append({"role": "assistant", "content": replayable_content(m.raw_content)})
        elif m.content:
            history.append({"role": "assistant", "content": m.content})
    return history


@require_POST
async def stream_chat_reply(request: HttpRequest, chat_id: UUID) -> HttpResponse:
    user = await request.auser()
    if not user.is_authenticated:
        return JsonResponse({"detail": "Unauthorized"}, status=401)

    chat = await writable_chats(user).filter(pk=chat_id).afirst()
    if chat is None:
        return JsonResponse({"detail": "Not Found"}, status=404)

    try:
        body = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"detail": "Invalid JSON."}, status=400)
    content = str(body.get("content", "")).strip()
    if not content:
        return JsonResponse({"detail": "Message can't be empty."}, status=422)
    if len(content) > MAX_MESSAGE_CHARS:
        return JsonResponse({"detail": "Message is too long."}, status=422)

    user_message = await Message.objects.acreate(chat=chat, role=MessageRole.USER, content=content)
    if not chat.title:
        chat.title = content[:80]
    await chat.asave()  # bumps updated_at so the chat list stays in recent order
    history = await build_history(chat)
    reply = await Message.objects.acreate(
        chat=chat, role=MessageRole.ASSISTANT, status=MessageStatus.STREAMING
    )

    async def events():
        parts: list[str] = []
        finished = False
        yield _sse(
            "start", {"user_message": _message_json(user_message), "reply_id": str(reply.id)}
        )
        try:
            async for event in get_provider().stream_reply(history):
                if isinstance(event, TextDelta):
                    parts.append(event.text)
                    yield _sse("delta", {"text": event.text})
                elif isinstance(event, FinalReply):
                    reply.content = event.text
                    reply.raw_content = event.raw_content
                    reply.model = event.model
                    reply.input_tokens = event.input_tokens
                    reply.output_tokens = event.output_tokens
                    if event.stop_reason == "refusal":
                        reply.status = MessageStatus.REFUSED
                        reply.error = event.refusal_category or ""
                    elif event.stop_reason == "max_tokens":
                        reply.status = MessageStatus.INCOMPLETE
                    else:
                        reply.status = MessageStatus.COMPLETE
            finished = True
        except Exception:
            logger.exception("Assistant stream failed for chat %s", chat.id)
            reply.status = MessageStatus.ERROR
            reply.content = "".join(parts)
            reply.error = "The assistant couldn't finish this reply."
            yield _sse("error", {"detail": reply.error, "message": _message_json(reply)})
        finally:
            if reply.status == MessageStatus.STREAMING:
                # Client disconnected or the provider ended without a final reply.
                reply.status = MessageStatus.INCOMPLETE
                reply.content = "".join(parts)
            await reply.asave()
        if finished:
            yield _sse("done", {"message": _message_json(reply)})

    response = StreamingHttpResponse(events(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response
