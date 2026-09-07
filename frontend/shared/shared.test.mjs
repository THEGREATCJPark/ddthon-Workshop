// F3 Shared — 무의존성 단위 테스트 (U3)
// 실행: node frontend/shared/shared.test.mjs   (Node 18+; 브라우저/백엔드 불필요)
// format.js 표시 유틸 + api/sse 팩토리 계약을 검증한다.
import { ORDER_STATUSES, statusLabel, formatCurrency, formatDateTime, escapeHtml, itemSummary } from './format.js';
import { createApiClient } from './api.js';
import { createSseClient } from './sse.js';

let pass = 0, fail = 0;
const eq = (name, got, want) => {
  const ok = JSON.stringify(got) === JSON.stringify(want);
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}` + (ok ? '' : `  got=${JSON.stringify(got)} want=${JSON.stringify(want)}`));
  ok ? pass++ : fail++;
};
const truthy = (name, got) => { const ok = !!got; console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}`); ok ? pass++ : fail++; };

// OrderStatus 계약값 + 한국어 라벨 매핑
eq('ORDER_STATUSES', ORDER_STATUSES, ['PENDING', 'IN_PROGRESS', 'DONE']);
eq('statusLabel PENDING', statusLabel('PENDING'), '대기중');
eq('statusLabel IN_PROGRESS', statusLabel('IN_PROGRESS'), '준비중');
eq('statusLabel DONE', statusLabel('DONE'), '완료');

// 금액(정수 원) 포맷
eq('formatCurrency 12000', formatCurrency(12000), '12,000원');
eq('formatCurrency 0', formatCurrency(0), '0원');

// XSS 방지 escape
truthy('escapeHtml escapes <', !escapeHtml('<b>').includes('<'));
truthy('escapeHtml escapes &', escapeHtml('a&b').includes('&amp;'));
truthy('escapeHtml escapes quote', escapeHtml('a"b').includes('&quot;') || escapeHtml('a"b').includes('&#34;'));

// 형태만 확인 (로케일/타임존 의존 값은 문자열 여부만)
truthy('formatDateTime returns string', typeof formatDateTime('2026-09-07T05:40:00Z') === 'string');
truthy('itemSummary returns string', typeof itemSummary([{ name: '김치', qty: 2 }], 3) === 'string');

// 팩토리 계약
truthy('createApiClient is fn', typeof createApiClient === 'function');
truthy('createSseClient is fn', typeof createSseClient === 'function');
const api = createApiClient({ getToken: () => 'tok', onUnauthorized: () => {} });
['request', 'get', 'post', 'patch', 'del'].forEach((m) => truthy(`api.${m} exists`, typeof api[m] === 'function'));

console.log(`\n== ${pass} passed, ${fail} failed ==`);
process.exit(fail ? 1 : 0);
