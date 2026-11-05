import { csrfToken, type Message } from "./api";
import { readSse } from "./sse";

export type StreamEvent =
  | { type: "start"; userMessage: Message; replyId: string }
  | { type: "delta"; text: string }
  | { type: "done"; message: Message }
  | { type: "error"; detail: string; message?: Message };

/** Send a message and yield the assistant's reply as it streams. */
export async function* streamReply(
  chatId: string,
  content: string,
  signal?: AbortSignal,
): AsyncGenerator<StreamEvent> {
  const res = await fetch(`/api/v1/chats/${chatId}/stream`, {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
      "X-CSRFToken": await csrfToken(),
    },
    body: JSON.stringify({ content }),
    signal,
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    yield { type: "error", detail: data?.detail ?? `Request failed (${res.status})` };
    return;
  }
  for await (const { event, data } of readSse(res)) {
    const d = data as Record<string, unknown>;
    if (event === "start") {
      yield {
        type: "start",
        userMessage: d.user_message as Message,
        replyId: d.reply_id as string,
      };
    } else if (event === "delta") {
      yield { type: "delta", text: d.text as string };
    } else if (event === "done") {
      yield { type: "done", message: d.message as Message };
    } else if (event === "error") {
      yield { type: "error", detail: d.detail as string, message: d.message as Message };
    }
  }
}
