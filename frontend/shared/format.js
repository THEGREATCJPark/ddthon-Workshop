// F3 Shared — format/display utilities (U3)
// 계약: OrderStatus 값은 PENDING/IN_PROGRESS/DONE, 표시 라벨은 프론트가 매핑(§6).

export const ORDER_STATUSES = ['PENDING', 'IN_PROGRESS', 'DONE'];

const STATUS_LABEL = {
  PENDING: '대기중',
  IN_PROGRESS: '준비중',
  DONE: '완료',
};

export function statusLabel(status) {
  return STATUS_LABEL[status] ?? status;
}

// 금액은 정수(원). 부동소수 금지(§3).
export function formatCurrency(value) {
  const n = Number.isFinite(value) ? value : 0;
  return n.toLocaleString('ko-KR') + '원';
}

// ISO 8601(UTC) → 로컬 표시 문자열.
export function formatDateTime(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString('ko-KR', {
    month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  });
}

// innerHTML 렌더 전 사용자/서버 유래 문자열 이스케이프 (BR-X1).
export function escapeHtml(str) {
  if (str == null) return '';
  return String(str)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

// 주문 항목 요약(축약 표시용): "아메리카노 x2, 라떼 x1"
export function itemSummary(items, max = 3) {
  if (!Array.isArray(items) || items.length === 0) return '-';
  const parts = items.slice(0, max).map((it) => `${it.name} x${it.qty}`);
  if (items.length > max) parts.push(`외 ${items.length - max}건`);
  return parts.join(', ');
}
