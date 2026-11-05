import { csrfToken, type Message } from "./api";
import { readSse } from "./sse";

export type StreamEvent =
  | { type: "start"; userMessage: Message; replyId: string }
  | { type: "delta"; text: string }
  | { type: "tool"; label: string }
  | { type: "done"; message: Message }
  | { type: "error"; detail: string; message?: Message };

/** Send a message and yield the assistant's reply as it streams. */
/** A record chosen in the Explorer, sent with the message as marked data. */
export interface AttachedRecord {
  connector: string;
  id: string;
  title: string;
}

export async function* streamReply(
  chatId: string,
  content: string,
  signal?: AbortSignal,
  record?: AttachedRecord | null,
): AsyncGenerator<StreamEvent> {
  const res = await fetch(`/api/v1/chats/${chatId}/stream`, {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
      "X-CSRFToken": await csrfToken(),
    },
    body: JSON.stringify(
      record ? { content, record: { connector: record.connector, id: record.id } } : { content },
    ),
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
    } else if (event === "tool") {
      yield { type: "tool", label: d.label as string };
    } else if (event === "done") {
      yield { type: "done", message: d.message as Message };
    } else if (event === "error") {
      yield { type: "error", detail: d.detail as string, message: d.message as Message };
    }
  }
}
