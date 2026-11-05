import json

import pytest
from django.test import AsyncClient

from assistant import providers
from assistant.providers import (
    FinalReply,
    ProviderError,
    TextDelta,
    ToolActivity,
    replayable_content,
)
from assistant.views import build_history
from projects.models import Chat, Message, MessageStatus, Project

pytestmark = pytest.mark.django_db(transaction=True)


async def read_events(response) -> list[tuple[str, dict]]:
    body = b"".join([chunk async for chunk in response.streaming_content]).decode()
    events = []
    for block in body.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        events.append((lines["event"], json.loads(lines["data"])))
    return events


async def post_message(client: AsyncClient, chat_id, content: str):
    return await client.post(
        f"/api/v1/chats/{chat_id}/stream", {"content": content}, content_type="application/json"
    )


async def test_stream_saves_both_messages_and_streams_text(alice, alice_async):
    chat = await Chat.objects.acreate(owner=alice)
    r = await post_message(alice_async, chat.id, "Where was the Pigeons?")
    assert r.status_code == 200
    assert r["Content-Type"] == "text/event-stream"

    events = await read_events(r)
    names = [name for name, _ in events]
    assert names[0] == "start" and names[-1] == "done"
    streamed = "".join(data["text"] for name, data in events if name == "delta")
    assert "Where was the Pigeons?" in streamed

    messages = [m async for m in Message.objects.filter(chat=chat).order_by("created_at")]
    assert [m.role for m in messages] == ["user", "assistant"]
    assert messages[1].status == MessageStatus.COMPLETE
    assert messages[1].content == streamed.strip()
    assert messages[1].raw_content == [{"type": "text", "text": streamed}]
    await chat.arefresh_from_db()
    assert chat.title == "Where was the Pigeons?"


async def test_history_is_append_only_across_turns(alice, alice_async):
    chat = await Chat.objects.acreate(owner=alice)
    await read_events(await post_message(alice_async, chat.id, "first"))
    first_history = await build_history(chat)
    await read_events(await post_message(alice_async, chat.id, "second"))
    second_history = await build_history(chat)
    assert second_history[: len(first_history)] == first_history
    assert [h["role"] for h in second_history] == ["user", "assistant", "user", "assistant"]


async def test_cannot_post_to_someone_elses_chat(alice, bob):
    chat = await Chat.objects.acreate(owner=alice)
    client = AsyncClient()
    await client.aforce_login(bob)
    r = await post_message(client, chat.id, "hello")
    assert r.status_code == 404
    assert not await Message.objects.filter(chat=chat).aexists()


async def test_viewer_cannot_post(alice, bob):
    from projects.models import ProjectMember, Role

    project = await Project.objects.acreate(owner=alice, title="Shared")
    await ProjectMember.objects.acreate(project=project, user=bob, role=Role.VIEWER)
    chat = await Chat.objects.acreate(owner=alice, project=project)
    client = AsyncClient()
    await client.aforce_login(bob)
    assert (await post_message(client, chat.id, "hi")).status_code == 404


async def test_requires_login(alice):
    chat = await Chat.objects.acreate(owner=alice)
    assert (await post_message(AsyncClient(), chat.id, "hi")).status_code == 401


async def test_empty_message_rejected(alice, alice_async):
    chat = await Chat.objects.acreate(owner=alice)
    assert (await post_message(alice_async, chat.id, "   ")).status_code == 422


async def test_provider_failure_saves_error_state(alice, alice_async, monkeypatch):
    class Broken:
        async def stream_reply(self, history, toolkit):
            yield TextDelta("Partial ")
            raise RuntimeError("upstream down")

    monkeypatch.setattr("assistant.views.get_provider", lambda: Broken())
    chat = await Chat.objects.acreate(owner=alice)
    events = await read_events(await post_message(alice_async, chat.id, "hi"))
    assert events[-1][0] == "error"
    reply = await Message.objects.filter(chat=chat, role="assistant").aget()
    assert reply.status == MessageStatus.ERROR
    assert reply.content == "Partial"


async def test_refusal_is_recorded(alice, alice_async, monkeypatch):
    class Refuses:
        async def stream_reply(self, history, toolkit):
            yield FinalReply(
                text="", raw_content=[], stop_reason="refusal", model="m", refusal_category="cyber"
            )

    monkeypatch.setattr("assistant.views.get_provider", lambda: Refuses())
    chat = await Chat.objects.acreate(owner=alice)
    await read_events(await post_message(alice_async, chat.id, "hi"))
    reply = await Message.objects.filter(chat=chat, role="assistant").aget()
    assert reply.status == MessageStatus.REFUSED


async def test_sources_and_checked_come_from_tools_not_text(alice, alice_async, monkeypatch):
    from asgiref.sync import sync_to_async

    from history.loader import load_all

    await sync_to_async(load_all)()

    class UsesTools:
        async def stream_reply(self, history, toolkit):
            yield ToolActivity("Comparing what the sources say")
            await toolkit.arun("compare_claims", {"subject": "Pigeons", "predicate": "address"})
            text = "5 Cheap Street [1], or 69 [4]. Also see [42] and https://made-up.example."
            yield TextDelta(text)
            yield FinalReply(text=text, raw_content=[], stop_reason="end_turn", model="m")

    monkeypatch.setattr("assistant.views.get_provider", lambda: UsesTools())
    chat = await Chat.objects.acreate(owner=alice)
    events = await read_events(await post_message(alice_async, chat.id, "Where was it?"))
    assert ("tool", {"label": "Comparing what the sources say"}) in events
    done = events[-1][1]["message"]
    assert [s["n"] for s in done["sources"]] == [1, 4]  # [42] was never returned by a tool
    assert all("made-up" not in s["url"] for s in done["sources"])
    assert any("sources disagree on address" in c["text"] for c in done["checked"])
    assert [(d["subject"], d["predicate"]) for d in done["disputes"]] == [
        ("The Pigeons", "address")
    ]

    r = await alice_async.get(f"/api/v1/chats/{chat.id}/messages")
    assert r.json()[1]["sources"] == done["sources"]


async def test_selected_record_is_sent_as_marked_data(alice, alice_async, monkeypatch):
    from asgiref.sync import sync_to_async

    from history.loader import load_all

    await sync_to_async(load_all)()
    seen = {}

    class Captures:
        async def stream_reply(self, history, toolkit):
            seen["history"] = history
            text = "This record [1] gives 69 Cheap Street."
            yield TextDelta(text)
            yield FinalReply(text=text, raw_content=[], stop_reason="end_turn", model="m")

    monkeypatch.setattr("assistant.views.get_provider", lambda: Captures())
    chat = await Chat.objects.acreate(owner=alice)
    r = await alice_async.post(
        f"/api/v1/chats/{chat.id}/stream",
        {
            "content": "What does this say?",
            "record": {"connector": "checked-reference", "id": "closedpubs-pigeons"},
        },
        content_type="application/json",
    )
    events = await read_events(r)
    blocks = seen["history"][-1]["content"]
    assert blocks[0] == {"type": "text", "text": "What does this say?"}
    assert "<selected_record>" in blocks[1]["text"] and "not instructions" in blocks[1]["text"]
    start = events[0][1]["user_message"]
    assert start["content"] == "What does this say?"
    assert (
        start["sources"][0]["url"] == "https://www.closedpubs.co.uk/berkshire/newbury_pigeons.html"
    )
    assert events[-1][1]["message"]["sources"][0]["n"] == 1
    # The same blocks are replayed next turn (append-only history).
    assert (await build_history(chat))[0]["content"] == blocks

    bad = await alice_async.post(
        f"/api/v1/chats/{chat.id}/stream",
        {"content": "And this?", "record": {"connector": "checked-reference", "id": "nope"}},
        content_type="application/json",
    )
    assert bad.status_code == 422


async def test_billing_problem_gets_a_clear_message(alice, alice_async, monkeypatch):
    class NoCredit:
        async def stream_reply(self, history, toolkit):
            raise ProviderError("billing", "credit balance is too low")
            yield  # pragma: no cover

    monkeypatch.setattr("assistant.views.get_provider", lambda: NoCredit())
    chat = await Chat.objects.acreate(owner=alice)
    events = await read_events(await post_message(alice_async, chat.id, "hi"))
    assert events[-1][0] == "error"
    assert "run out of credit" in events[-1][1]["detail"]


async def test_history_replays_tool_turns(alice):
    chat = await Chat.objects.acreate(owner=alice)
    await Message.objects.acreate(chat=chat, role="user", content="Where?")
    turns = [
        {
            "role": "assistant",
            "content": [{"type": "tool_use", "id": "t1", "name": "x", "input": {}}],
        },
        {
            "role": "user",
            "content": [{"type": "tool_result", "tool_use_id": "t1", "content": "{}"}],
        },
        {"role": "assistant", "content": [{"type": "text", "text": "Here."}]},
    ]
    await Message.objects.acreate(chat=chat, role="assistant", content="Here.", turns=turns)
    history = await build_history(chat)
    assert history == [{"role": "user", "content": "Where?"}, *turns]


def test_replayable_content_keeps_blocks_without_fallback():
    blocks = [{"type": "thinking", "thinking": "", "signature": "s"}, {"type": "text", "text": "a"}]
    assert replayable_content(blocks) == blocks


def test_replayable_content_trims_before_fallback_marker():
    blocks = [
        {"type": "thinking", "thinking": "", "signature": "s1"},
        {"type": "text", "text": "partial"},
        {"type": "fallback"},
        {"type": "thinking", "thinking": "", "signature": "s2"},
        {"type": "text", "text": "rest"},
    ]
    assert replayable_content(blocks) == [
        {"type": "text", "text": "partial"},
        {"type": "thinking", "thinking": "", "signature": "s2"},
        {"type": "text", "text": "rest"},
    ]


def test_get_provider_rejects_unknown(settings):
    settings.ASSISTANT_PROVIDER = "nope"
    with pytest.raises(ValueError):
        providers.get_provider()
