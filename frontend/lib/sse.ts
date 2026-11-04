/** One Server-Sent Event: `event: delta` + `data: {"text": "…"}`. */
export interface ServerEvent {
  event: string;
  data: unknown;
}

/**
 * Reads the Server-Sent Events of a streamed reply as they arrive. An event can be split across
 * pieces of the stream, or several can come in one piece; each `data` is JSON. Lines end in "\n"
 * (as the backend writes them).
 */
export async function* readEvents(body: ReadableStream<Uint8Array>): AsyncGenerator<ServerEvent> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) return;
    buffer += decoder.decode(value, { stream: true }); // a letter can be split across pieces too
    let end: number;
    while ((end = buffer.indexOf("\n\n")) >= 0) {
      const block = buffer.slice(0, end);
      buffer = buffer.slice(end + 2);
      let event = "message";
      const data: string[] = [];
      for (const line of block.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) data.push(line.slice(5).trimStart());
      }
      if (data.length) yield { event, data: JSON.parse(data.join("\n")) };
    }
  }
}
