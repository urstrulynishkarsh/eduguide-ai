// @vitest-environment node
import { describe, expect, it } from "vitest";

import { readEvents } from "@/lib/sse";

/** A response body that arrives in the given pieces. */
function streamOf(...pieces: (string | Uint8Array)[]) {
  const encoder = new TextEncoder();
  return new ReadableStream<Uint8Array>({
    start(controller) {
      for (const piece of pieces)
        controller.enqueue(typeof piece === "string" ? encoder.encode(piece) : piece);
      controller.close();
    },
  });
}

async function readAll(stream: ReadableStream<Uint8Array>) {
  const events = [];
  for await (const event of readEvents(stream)) events.push(event);
  return events;
}

describe("readEvents", () => {
  it("reads an event split across pieces, and several events in one piece", async () => {
    const events = await readAll(
      streamOf(
        'event: delta\ndata: {"te',
        'xt": "Equation "}\n\nevent: delta\ndata: {"text": "ek balance hai"}\n\nevent: done\n',
        'data: {"saved": true}\n\n',
      ),
    );
    expect(events).toEqual([
      { event: "delta", data: { text: "Equation " } },
      { event: "delta", data: { text: "ek balance hai" } },
      { event: "done", data: { saved: true } },
    ]);
  });

  it("keeps a letter whole when its bytes arrive in two pieces", async () => {
    const bytes = new TextEncoder().encode('event: delta\ndata: {"text": "समीकरण"}\n\n');
    const cut = bytes.indexOf(0xe0) + 1; // inside the first Devanagari letter
    expect(await readAll(streamOf(bytes.slice(0, cut), bytes.slice(cut)))).toEqual([
      { event: "delta", data: { text: "समीकरण" } },
    ]);
  });

  it("drops an event the stream never finished", async () => {
    expect(await readAll(streamOf('event: delta\ndata: {"text": "half'))).toEqual([]);
  });
});
