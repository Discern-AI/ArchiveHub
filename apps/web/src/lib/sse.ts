/** Server-sent events over a POST request (EventSource only supports GET). */

export interface SseEvent {
  event: string;
  data: unknown;
}

/** Splits a text buffer into complete SSE events, returning any unfinished remainder. */
export function parseSse(buffer: string): { events: SseEvent[]; rest: string } {
  const normalised = buffer.replace(/\r\n/g, "\n");
  const blocks = normalised.split("\n\n");
  const rest = blocks.pop() ?? "";
  const events: SseEvent[] = [];
  for (const block of blocks) {
    let event = "message";
    const dataLines: string[] = [];
    for (const line of block.split("\n")) {
      if (line.startsWith("event:")) event = line.slice(6).trim();
      else if (line.startsWith("data:")) dataLines.push(line.slice(5).trimStart());
    }
    if (!dataLines.length) continue;
    try {
      events.push({ event, data: JSON.parse(dataLines.join("\n")) });
    } catch {
      // Ignore malformed events rather than breaking the whole stream.
    }
  }
  return { events, rest };
}

export async function* readSse(response: Response): AsyncGenerator<SseEvent> {
  if (!response.body) return;
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const { events, rest } = parseSse(buffer);
      buffer = rest;
      yield* events;
    }
    buffer += decoder.decode();
    yield* parseSse(buffer + "\n\n").events;
  } finally {
    reader.releaseLock();
  }
}
