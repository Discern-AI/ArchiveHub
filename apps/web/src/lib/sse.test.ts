import { describe, expect, it } from "vitest";
import { parseSse } from "./sse";

describe("parseSse", () => {
  it("parses complete events and keeps the unfinished remainder", () => {
    const { events, rest } = parseSse(
      'event: delta\ndata: {"text":"Hel"}\n\nevent: delta\ndata: {"text":"lo"}\n\nevent: do',
    );
    expect(events).toEqual([
      { event: "delta", data: { text: "Hel" } },
      { event: "delta", data: { text: "lo" } },
    ]);
    expect(rest).toBe("event: do");
  });

  it("handles CRLF line endings and skips malformed data", () => {
    const { events } = parseSse('event: a\r\ndata: {"x":1}\r\n\r\nevent: b\r\ndata: {bad\r\n\r\n');
    expect(events).toEqual([{ event: "a", data: { x: 1 } }]);
  });
});
