"""AI provider adapter (ADR-014).

Views talk to a provider through `stream_reply`, which yields `TextDelta` events and
then exactly one `FinalReply`. Swapping models or vendors means adding a provider here,
not touching views. `FakeProvider` is deterministic and used in tests.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Protocol

from django.conf import settings

from .prompts import SYSTEM_PROMPT


@dataclass
class TextDelta:
    text: str


@dataclass
class FinalReply:
    text: str
    raw_content: list[dict[str, Any]]
    stop_reason: str | None
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    refusal_category: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


Event = TextDelta | FinalReply


class Provider(Protocol):
    def stream_reply(self, history: list[dict[str, Any]]) -> AsyncIterator[Event]: ...


def replayable_content(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Prepare an assistant turn's stored content for replay on the next request.

    Blocks are replayed unchanged (including thinking blocks) so the history stays
    append-only. The one exception is a turn that switched to a fallback model mid-output:
    before the last `fallback` marker only text survives, per the fallback rules.
    """
    last_fallback = max(
        (i for i, b in enumerate(blocks) if b.get("type") == "fallback"), default=None
    )
    if last_fallback is None:
        return blocks
    before = [b for b in blocks[:last_fallback] if b.get("type") == "text"]
    return before + blocks[last_fallback + 1 :]


class AnthropicProvider:
    """Claude via the official SDK, streamed. Model, effort and limits come from settings."""

    BETAS = ["server-side-fallback-2026-07-01", "thinking-binding-controls-2026-08-01"]

    def __init__(self) -> None:
        import anthropic

        self._anthropic = anthropic
        self.client = anthropic.AsyncAnthropic()

    async def stream_reply(self, history: list[dict[str, Any]]) -> AsyncIterator[Event]:
        async with self.client.beta.messages.stream(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=settings.ANTHROPIC_MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=history,
            # If a stored thinking block no longer matches, drop it rather than fail the turn.
            thinking={
                "type": "adaptive",
                "block_binding": {"prefix_mismatch_behavior": "drop_block"},
            },
            output_config={"effort": settings.ANTHROPIC_EFFORT},
            cache_control={"type": "ephemeral"},
            # On a safety decline, the API retries on a suitable model within the same call.
            fallbacks="default",
            betas=self.BETAS,
        ) as stream:
            async for text in stream.text_stream:
                yield TextDelta(text)
            final = await stream.get_final_message()

        blocks = [b.model_dump(mode="json", exclude_none=True) for b in final.content]
        text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        category = None
        if final.stop_reason == "refusal" and getattr(final, "stop_details", None):
            category = final.stop_details.category
        yield FinalReply(
            text=text,
            raw_content=blocks,
            stop_reason=final.stop_reason,
            model=final.model,
            input_tokens=final.usage.input_tokens,
            output_tokens=final.usage.output_tokens,
            refusal_category=category,
        )


class FakeProvider:
    """Deterministic provider for tests and offline development. Echoes the last message."""

    async def stream_reply(self, history: list[dict[str, Any]]) -> AsyncIterator[Event]:
        last = history[-1]["content"] if history else ""
        if isinstance(last, list):
            last = " ".join(b.get("text", "") for b in last if isinstance(b, dict))
        reply = f"(Test assistant) You said: {last}"
        for word in reply.split(" "):
            await asyncio.sleep(settings.ASSISTANT_FAKE_DELAY)
            yield TextDelta(word + " ")
        text = reply + " "
        yield FinalReply(
            text=text,
            raw_content=[{"type": "text", "text": text}],
            stop_reason="end_turn",
            model="fake",
        )


def get_provider() -> Provider:
    name = settings.ASSISTANT_PROVIDER
    if name == "fake":
        return FakeProvider()
    if name == "anthropic":
        return AnthropicProvider()
    raise ValueError(f"Unknown ASSISTANT_PROVIDER: {name!r}")
