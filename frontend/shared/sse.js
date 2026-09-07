// F3 Shared — sseClient (U3)
// native EventSource 는 헤더 설정이 불가하므로(§7) fetch + ReadableStream 으로
// text/event-stream 프레임(event:/data:/빈 줄)을 파싱한다.
// 끊김 시 3초 고정 간격 재연결 (Q17=A / BR-X4). 단, 401(인증 실패)은 재연결하지 않고
// onError 로 위임한다 — 자동 재발급 없음 (Q20=D).

export function createSseClient({ url, getToken, onEvent, onOpen, onError, retryMs = 3000 }) {
  let closed = false;
  let controller = null;
  let retryTimer = null;

  async function connect() {
    if (closed) return;
    controller = new AbortController();
    try {
      const res = await fetch(url, {
        headers: { Authorization: `Bearer ${getToken?.() ?? ''}` },
        signal: controller.signal,
      });

      if (res.status === 401) {
        onError?.(makeErr('UNAUTHORIZED', 401));
        return; // 인증 실패 → 재연결 금지 (loop 방지)
      }
      if (!res.ok || !res.body) {
        throw makeErr(`SSE connect failed (${res.status})`, res.status);
      }

      onOpen?.();
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        let sep;
        while ((sep = buffer.indexOf('\n\n')) >= 0) {
          const rawFrame = buffer.slice(0, sep);
          buffer = buffer.slice(sep + 2);
          const frame = parseFrame(rawFrame);
          if (frame) onEvent?.(frame.event, frame.data);
        }
      }
      throw makeErr('SSE stream ended', 0); // 스트림 종료 → 재연결
    } catch (err) {
      if (closed || controller?.signal.aborted) return;
      onError?.(err);
      scheduleReconnect();
    }
  }

  function scheduleReconnect() {
    if (closed) return;
    clearTimeout(retryTimer);
    retryTimer = setTimeout(connect, retryMs); // 고정 간격
  }

  function parseFrame(raw) {
    let event = null;
    const dataLines = [];
    for (const line of raw.split('\n')) {
      if (line.startsWith('event:')) event = line.slice(6).trim();
      else if (line.startsWith('data:')) dataLines.push(line.slice(5).trimStart());
    }
    if (event === null && dataLines.length === 0) return null;
    const joined = dataLines.join('\n');
    let data = null;
    if (joined) {
      try {
        data = JSON.parse(joined);
      } catch {
        data = joined;
      }
    }
    return { event: event ?? 'message', data };
  }

  function close() {
    closed = true;
    clearTimeout(retryTimer);
    controller?.abort();
  }

  connect();
  return { close };
}

function makeErr(message, status) {
  const e = new Error(message);
  e.status = status;
  return e;
}
