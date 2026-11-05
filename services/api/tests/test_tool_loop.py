"""The Anthropic tool loop, driven by a stand-in client (no network, no API key)."""

import copy
from types import SimpleNamespace

import pytest

from assistant.providers import AnthropicProvider, FinalReply, TextDelta, ToolActivity
from assistant.tools import ToolKit
from history.loader import load_all

pytestmark = pytest.mark.django_db(transaction=True)


class Block(SimpleNamespace):
    def model_dump(self, **kwargs):
        return {k: v for k, v in vars(self).items() if v is not None}


def text(t):
    return Block(type="text", text=t)


def tool_use(id_, name, args):
    return Block(type="tool_use", id=id_, name=name, input=args)


def message(content, stop_reason):
    return SimpleNamespace(
        content=content,
        stop_reason=stop_reason,
        model="claude-test",
        usage=SimpleNamespace(input_tokens=10, output_tokens=5),
        stop_details=None,
    )


class FakeStream:
    def __init__(self, msg):
        self.msg = msg

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    @property
    def text_stream(self):
        async def gen():
            for b in self.msg.content:
                if b.type == "text":
                    yield b.text

        return gen()

    async def get_final_message(self):
        return self.msg


class FakeMessages:
    def __init__(self, scripted):
        self.scripted = list(scripted)
        self.requests = []

    def stream(self, **kwargs):
        self.requests.append(copy.deepcopy(kwargs))  # the real SDK serialises at call time
        return FakeStream(self.scripted.pop(0))


def make_provider(scripted):
    provider = AnthropicProvider.__new__(AnthropicProvider)
    import anthropic

    provider.anthropic = anthropic
    messages = FakeMessages(scripted)
    provider.client = SimpleNamespace(beta=SimpleNamespace(messages=messages))
    return provider, messages


async def collect(provider, history, kit):
    return [e async for e in provider.stream_reply(history, kit)]


async def test_tool_round_trip_records_turns_and_citations(alice):
    from asgiref.sync import sync_to_async

    await sync_to_async(load_all)()
    provider, fake = make_provider(
        [
            message(
                [
                    text("Let me check the records."),
                    tool_use(
                        "t1", "compare_claims", {"subject": "Pigeons", "predicate": "address"}
                    ),
                ],
                "tool_use",
            ),
            message([text("Sources disagree: 5 Cheap Street [1] or 69 [4].")], "end_turn"),
        ]
    )
    kit = ToolKit(user=alice)
    history = [{"role": "user", "content": "Where was the Pigeons?"}]
    events = await collect(provider, history, kit)

    assert any(isinstance(e, ToolActivity) and "Pigeons" in e.label for e in events)
    final = events[-1]
    assert isinstance(final, FinalReply)
    assert final.text.startswith("Let me check the records.")
    assert "Sources disagree" in final.text
    assert [t["role"] for t in final.turns] == ["assistant", "user", "assistant"]
    (result,) = final.turns[1]["content"]
    assert result["type"] == "tool_result" and result["tool_use_id"] == "t1"
    assert final.input_tokens == 20

    # Second request carried the tool result, the same tools and the same system prompt.
    first, second = fake.requests
    assert second["messages"][-1]["content"][0]["tool_use_id"] == "t1"
    assert first["tools"] == second["tools"] and first["system"] == second["system"]
    assert history == [{"role": "user", "content": "Where was the Pigeons?"}]  # not mutated

    assert [s["n"] for s in kit.cited_in(final.text)] == [1, 4]


async def test_text_only_reply(alice):
    provider, _ = make_provider([message([text("Hello.")], "end_turn")])
    events = await collect(provider, [{"role": "user", "content": "hi"}], ToolKit(user=alice))
    assert [type(e) for e in events] == [TextDelta, FinalReply]


async def test_truncated_tool_call_is_not_run(alice):
    provider, fake = make_provider(
        [message([tool_use("t1", "search_records", {"query": "Pig"})], "max_tokens")]
    )
    kit = ToolKit(user=alice)
    events = await collect(provider, [{"role": "user", "content": "hi"}], kit)
    assert events[-1].stop_reason == "max_tokens"
    assert kit.checked == [] and len(fake.requests) == 1
