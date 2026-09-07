// F3 Shared — apiClient (U3)
// 저장된 토큰을 Authorization: Bearer 로 자동 첨부, JSON 직렬화/역직렬화.
// 비2xx 응답은 {status, code, message} 를 담은 Error 로 throw.
// 401 은 역할별 onUnauthorized 핸들러로 위임 — 자동 재발급 없음 (Q20=D / BR-A3·A4).

export function createApiClient({ baseUrl = '', getToken, onUnauthorized } = {}) {
  async function request(method, path, body) {
    const headers = { Accept: 'application/json' };
    const token = getToken?.();
    if (token) headers.Authorization = `Bearer ${token}`;

    const opts = { method, headers };
    if (body !== undefined) {
      headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    }

    let res;
    try {
      res = await fetch(baseUrl + path, opts);
    } catch (networkErr) {
      throw makeError(0, 'NETWORK_ERROR', '서버에 연결할 수 없습니다.');
    }

    if (res.status === 401) {
      // 토큰 만료/무효 → 역할별 처리에 위임. 여기서 조용한 재로그인을 시도하지 않는다.
      onUnauthorized?.();
      throw makeError(401, 'UNAUTHORIZED', '인증이 만료되었습니다. 다시 로그인해 주세요.');
    }
    if (res.status === 204) return null;

    const text = await res.text();
    const data = text ? safeJson(text) : null;

    if (!res.ok) {
      const err = data?.error ?? {};
      throw makeError(res.status, err.code ?? 'ERROR', err.message ?? '요청을 처리하지 못했습니다.');
    }
    return data;
  }

  return {
    request,
    get: (p) => request('GET', p),
    post: (p, b) => request('POST', p, b),
    patch: (p, b) => request('PATCH', p, b),
    del: (p) => request('DELETE', p),
  };
}

function makeError(status, code, message) {
  const e = new Error(message);
  e.status = status;
  e.code = code;
  return e;
}

function safeJson(text) {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}
