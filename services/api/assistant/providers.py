"""AI provider adapter (ADR-014).

Views call `stream_reply(history, toolkit)`, which yields `TextDelta` and `ToolActivity`
events and finally exactly one `FinalReply`. Tool calls are run through the toolkit, which
applies the user's permissions. `FakeProvider` is deterministic, for tests and offline work.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Protocol

from django.conf import settings

from .prompts import SYSTEM_PROMPT
from .tools import ToolKit, tool_definitions

MAX_TOOL_ROUNDS = 8


@dataclass
class TextDelta:
    text: str


@dataclass
class ToolActivity:
    label: str


@dataclass
class FinalReply:
    text: str
    raw_content: list[dict[str, Any]]
    stop_reason: str | None
    model: str
    turns: list[dict[str, Any]] = field(default_factory=list)
    input_tokens: int | None = None
    output_tokens: int | None = None
    refusal_category: str | None = None


Event = TextDelta | ToolActivity | FinalReply


class ProviderError(Exception):
    """A failure we can explain to the user. `kind` picks the message (see USER_MESSAGES)."""

    def __init__(self, kind: str, detail: str = ""):
        super().__init__(detail or kind)
        self.kind = kind


USER_MESSAGES = {
    "config": "The assistant isn't set up correctly. An administrator needs to check its API key.",
    "billing": "The assistant is unavailable because its API account has run out of credit.",
    "busy": "The assistant is busy right now. Please try again in a minute.",
    "unreachable": "Couldn't reach the assistant service. Please try again shortly.",
    "tool_limit": "The assistant needed too many steps for this question and stopped. Try "
    "asking something narrower.",
    "unknown": "The assistant couldn't finish this reply.",
}


class Provider(Protocol):
    def stream_reply(
        self, history: list[dict[str, Any]], toolkit: ToolKit
    ) -> AsyncIterator[Event]: ...


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


def classify_error(exc: Exception) -> ProviderError:
    """Map an Anthropic SDK error onto a ProviderError the user can understand."""
    import anthropic as a

    if isinstance(exc, a.AuthenticationError | a.PermissionDeniedError):
        return ProviderError("config", str(exc))
    if isinstance(exc, a.RateLimitError):
        return ProviderError("busy", str(exc))
    if isinstance(exc, a.APIConnectionError):
        return ProviderError("unreachable", str(exc))
    if isinstance(exc, a.APIStatusError):
        if "credit balance" in str(exc).lower():
            return ProviderError("billing", str(exc))
        if exc.status_code in (429, 503, 529):
            return ProviderError("busy", str(exc))
    return ProviderError("unknown", str(exc))


class AnthropicProvider:
    """Claude via the official SDK, streamed, with a manual tool loop."""

    BETAS = ["server-side-fallback-2026-07-01", "thinking-binding-controls-2026-08-01"]

    def __init__(self) -> None:
        import anthropic

        self.anthropic = anthropic
        self.client = anthropic.AsyncAnthropic()

    def _classify(self, exc: Exception) -> ProviderError:
        return classify_error(exc)

    async def stream_reply(
        self, history: list[dict[str, Any]], toolkit: ToolKit
    ) -> AsyncIterator[Event]:
        messages = list(history)
        turns: list[dict[str, Any]] = []
        text_parts: list[str] = []
        input_tokens = output_tokens = 0
        json_retries = 0
        rounds = 0

        while True:
            try:
                async with self.client.beta.messages.stream(
                    model=settings.ANTHROPIC_MODEL,
                    max_tokens=settings.ANTHROPIC_MAX_TOKENS,
                    system=SYSTEM_PROMPT,
                    tools=tool_definitions(),
                    messages=messages,
                    # A stored thinking block that no longer matches is dropped, not fatal.
                    thinking={
                        "type": "adaptive",
                        "block_binding": {"prefix_mismatch_behavior": "drop_block"},
                    },
                    output_config={"effort": settings.ANTHROPIC_EFFORT},
                    cache_control={"type": "ephemeral"},
                    # On a safety decline, the API retries on a suitable model in the same call.
                    fallbacks="default",
                    betas=self.BETAS,
                ) as stream:
                    async for text in stream.text_stream:
                        text_parts.append(text)
                        yield TextDelta(text)
                    final = await stream.get_final_message()
                json_retries = 0
            except ValueError:
                # Tool input JSON the SDK couldn't parse at all: re-issue the turn (bounded).
                json_retries += 1
                if json_retries > 2:
                    raise ProviderError("unknown", "unparseable tool input") from None
                continue
            except self.anthropic.APIError as exc:
                raise self._classify(exc) from exc

            input_tokens += final.usage.input_tokens or 0
            output_tokens += final.usage.output_tokens or 0
            blocks = [b.model_dump(mode="json", exclude_none=True) for b in final.content]
            turns.append({"role": "assistant", "content": blocks})
            messages.append({"role": "assistant", "content": replayable_content(blocks)})

            tool_uses = [b for b in final.content if b.type == "tool_use"]
            if final.stop_reason != "tool_use" or not tool_uses:
                break
            rounds += 1
            if rounds > MAX_TOOL_ROUNDS:
                raise ProviderError("tool_limit")

            results = []
            for block in tool_uses:
                tool_input = block.input if isinstance(block.input, dict) else {}
                yield ToolActivity(toolkit.label(block.name, tool_input))
                content, is_error = await toolkit.arun(block.name, block.input)
                result = {"type": "tool_result", "tool_use_id": block.id, "content": content}
                if is_error:
                    result["is_error"] = True
                results.append(result)
            # All results for one turn go back in a single user message.
            turns.append({"role": "user", "content": results})
            messages.append({"role": "user", "content": results})
            # Keep paragraphs apart when the model writes again after using tools.
            if text_parts and not text_parts[-1].endswith("\n"):
                text_parts.append("\n\n")
                yield TextDelta("\n\n")

        category = None
        if final.stop_reason == "refusal" and getattr(final, "stop_details", None):
            category = final.stop_details.category
        yield FinalReply(
            text="".join(text_parts).strip(),
            raw_content=blocks,
            stop_reason=final.stop_reason,
            model=final.model,
            turns=turns,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            refusal_category=category,
        )


class FakeProvider:
    """Deterministic provider for tests and offline development. Echoes the last message."""

    async def stream_reply(
        self, history: list[dict[str, Any]], toolkit: ToolKit
    ) -> AsyncIterator[Event]:
        last = history[-1]["content"] if history else ""
        if isinstance(last, list):
            last = " ".join(b.get("text", "") for b in last if isinstance(b, dict))
        reply = f"(Test assistant) You said: {last}"
        for word in reply.split(" "):
            await asyncio.sleep(settings.ASSISTANT_FAKE_DELAY)
            yield TextDelta(word + " ")
        text = reply + " "
        content = [{"type": "text", "text": text}]
        yield FinalReply(
            text=text.strip(),
            raw_content=content,
            stop_reason="end_turn",
            model="fake",
            turns=[{"role": "assistant", "content": content}],
        )


def get_provider() -> Provider:
    name = settings.ASSISTANT_PROVIDER
    if name == "fake":
        return FakeProvider()
    if name == "anthropic":
        return AnthropicProvider()
    raise ValueError(f"Unknown ASSISTANT_PROVIDER: {name!r}")
