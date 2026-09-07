// F2 AdminApp (U3) — 단일 HTML + JS 뷰 전환 (Q1=A, Q3=A)
// consumes: U1 인증/메뉴 API, U2 주문/세션/이력 API + SSE(§7). 모든 호출 Authorization: Bearer.
import { createApiClient } from '../shared/api.js';
import { createSseClient } from '../shared/sse.js';
import { formatCurrency, formatDateTime, escapeHtml, statusLabel, ORDER_STATUSES } from '../shared/format.js';

const AUTH_KEY = 'to_admin_auth';
const HIGHLIGHT_MS = 4000;

const state = {
  view: 'login',           // 'login' | 'dashboard' | 'menuAdmin'
  auth: null,              // { access_token, expires_at, store_id, username }
  tables: [],              // GET /api/admin/tables
  tableFilter: new Set(),  // 선택된 table_no (비어있으면 전체) — 다중선택 (Q14=B)
  highlighted: new Set(),  // 신규주문 하이라이트 중인 table_no
  detail: null,            // { table_no, orders }
  history: null,           // { table_no, preset, from, to, entries }
  menus: [],               // 메뉴 관리
  menuForm: null,          // { id?, category, name, price, description, image_url }
  confirm: null,           // { text, okLabel, danger }
};
let confirmOnOk = null;
let sse = null;

const appEl = document.getElementById('app');
const modalHost = document.getElementById('modal-host');
const toastHost = document.getElementById('toast-host');

const api = createApiClient({
  getToken: () => state.auth?.access_token,
  onUnauthorized: logout,
});

// ---- 저장소 ----
function loadAuth() { try { return JSON.parse(localStorage.getItem(AUTH_KEY)); } catch { return null; } }
function saveAuth(auth) { state.auth = auth; localStorage.setItem(AUTH_KEY, JSON.stringify(auth)); }
function tokenValid(a) { return !!(a?.access_token && a?.expires_at && new Date(a.expires_at).getTime() > Date.now()); }

// 401/만료 → access_token 폐기 + 로그인 화면 (Q20=D / BR-A3)
function logout() {
  disconnectSse();
  state.auth = null;
  localStorage.removeItem(AUTH_KEY);
  state.view = 'login';
  state.detail = state.history = null;
  render();
}

// ================= 부트스트랩 =================
function init() {
  state.auth = loadAuth();
  if (tokenValid(state.auth)) { state.view = 'dashboard'; render(); initDashboard(); }
  else { state.auth = null; localStorage.removeItem(AUTH_KEY); state.view = 'login'; render(); }
}

// ================= 렌더 =================
function render() {
  if (state.view === 'login') appEl.innerHTML = viewLogin();
  else if (state.view === 'dashboard') appEl.innerHTML = viewDashboard();
  else if (state.view === 'menuAdmin') appEl.innerHTML = viewMenuAdmin();
  renderModals();
}

function viewLogin() {
  return `
    <div class="auth-wrap">
      <h1>관리자 로그인</h1>
      <div class="field"><label>매장 식별자(store_id)</label><input id="in-store" type="number" inputmode="numeric" /></div>
      <div class="field"><label>사용자명</label><input id="in-user" type="text" autocomplete="username" /></div>
      <div class="field"><label>비밀번호</label><input id="in-pw" type="password" autocomplete="current-password" /></div>
      <button class="btn" data-action="login">로그인</button>
    </div>`;
}

function viewDashboard() {
  const filterChips = state.tables.map((t) => `
    <button class="chip ${state.tableFilter.has(t.table_no) ? 'active' : ''}" data-action="filter" data-tno="${t.table_no}">
      ${t.table_no}번
    </button>`).join('');

  const visible = state.tables.filter((t) => state.tableFilter.size === 0 || state.tableFilter.has(t.table_no));
  const cards = visible.length ? visible.map(tableCard).join('') : '<div class="empty">표시할 테이블이 없습니다.</div>';

  return `
    <div class="topbar">
      <span class="title">실시간 주문 현황</span>
      <div class="right">
        <span class="who">${escapeHtml(state.auth?.username || '')} · 매장 ${escapeHtml(String(state.auth?.store_id ?? ''))}</span>
        <button class="btn secondary" data-action="go-menu-admin">메뉴 관리</button>
        <button class="btn ghost" data-action="logout">로그아웃</button>
      </div>
    </div>
    <div class="filters">
      <button class="chip ${state.tableFilter.size === 0 ? 'active' : ''}" data-action="filter-all">전체</button>
      ${filterChips}
    </div>
    <div class="grid">${cards}</div>`;
}

function tableCard(t) {
  const hl = state.highlighted.has(t.table_no) ? 'hl' : '';
  // latest_orders 내부 필드는 계약상 미확정(§5.4 `[...]`)이라 개수만 안전하게 표기, 상세는 클릭 시 조회
  const n = Array.isArray(t.latest_orders) ? t.latest_orders.length : 0;
  const previewText = n ? `최근 주문 ${n}건` : '주문 없음';
  return `
    <div class="table-card ${hl}" data-action="open-detail" data-tno="${t.table_no}">
      <div class="card-head">
        <span class="tno">${t.table_no}번</span>
        <span class="total">${formatCurrency(t.current_total)}</span>
      </div>
      <div class="preview">${escapeHtml(previewText)}</div>
      <div class="status-dot ${t.has_active_session ? 'active' : 'idle'}">
        ${t.has_active_session ? '● 이용 중' : '○ 비어있음'}
      </div>
    </div>`;
}

function viewMenuAdmin() {
  const groups = {};
  for (const m of state.menus) (groups[m.category] ||= []).push(m);
  const sortedIds = state.menus.slice().sort((a, b) => (a.display_order ?? 0) - (b.display_order ?? 0));

  const body = Object.keys(groups).length ? Object.entries(groups).map(([cat, items]) => `
    <div class="menu-cat-group">
      <h3>${escapeHtml(cat)}</h3>
      ${items.map((m) => menuAdminRow(m, sortedIds)).join('')}
    </div>`).join('') : '<div class="empty">등록된 메뉴가 없습니다.</div>';

  return `
    <div class="topbar">
      <span class="title">메뉴 관리</span>
      <div class="right">
        <button class="btn" data-action="menu-new">+ 새 메뉴</button>
        <button class="btn secondary" data-action="go-dashboard">대시보드</button>
      </div>
    </div>
    <div class="menu-admin">${body}</div>`;
}

function menuAdminRow(m, sortedIds) {
  const idx = sortedIds.findIndex((x) => x.id === m.id);
  return `
    <div class="menu-admin-row">
      <span class="ma-name">${escapeHtml(m.name)}</span>
      <span class="ma-price">${formatCurrency(m.price)}</span>
      <div class="ma-actions">
        <button class="btn sm secondary" data-action="menu-up" data-id="${m.id}" ${idx <= 0 ? 'disabled' : ''}>▲</button>
        <button class="btn sm secondary" data-action="menu-down" data-id="${m.id}" ${idx >= sortedIds.length - 1 ? 'disabled' : ''}>▼</button>
        <button class="btn sm secondary" data-action="menu-edit" data-id="${m.id}">수정</button>
        <button class="btn sm danger" data-action="menu-delete" data-id="${m.id}">삭제</button>
      </div>
    </div>`;
}

// ---- 모달 ----
function renderModals() {
  let html = '';
  if (state.detail) html += modalDetail();
  if (state.history) html += modalHistory();
  if (state.menuForm) html += modalMenuForm();
  if (state.confirm) html += modalConfirm();
  modalHost.innerHTML = html;
}

function modalDetail() {
  const d = state.detail;
  const rows = (d.orders || []).length ? d.orders.map((o) => `
    <div class="detail-order">
      <div class="do-head">
        <strong>${escapeHtml(o.order_no)}</strong>
        <span>
          <span class="badge ${o.status}">${statusLabel(o.status)}</span>
          <button class="btn sm danger" data-action="delete-order" data-oid="${o.order_id}">삭제</button>
        </span>
      </div>
      <div class="items">${o.items.map((it) => `${escapeHtml(it.name)} x${it.qty} (${formatCurrency(it.unit_price * it.qty)})`).join(', ')}</div>
      <div class="do-head" style="margin-bottom:8px">
        <span class="who" style="color:#6b7280">${formatDateTime(o.created_at)}</span>
        <strong>${formatCurrency(o.total)}</strong>
      </div>
      <div class="status-btns">
        ${ORDER_STATUSES.map((s) => `
          <button class="btn sm ${o.status === s ? 'active' : ''}" data-action="set-status" data-oid="${o.order_id}" data-status="${s}">
            ${statusLabel(s)}
          </button>`).join('')}
      </div>
    </div>`).join('') : '<div class="empty">활성 세션의 주문이 없습니다.</div>';

  return `
    <div class="overlay" data-action="close-detail">
      <div class="modal" data-stop="1">
        <div class="modal-head">
          <h2>${d.table_no}번 테이블 주문</h2>
          <button class="btn ghost" data-action="close-detail">✕</button>
        </div>
        <div class="modal-body">${rows}</div>
        <div class="modal-foot">
          <button class="btn secondary" data-action="open-history" data-tno="${d.table_no}">과거 내역</button>
          <button class="btn danger" data-action="end-session" data-tno="${d.table_no}">이용 완료</button>
        </div>
      </div>
    </div>`;
}

function modalHistory() {
  const h = state.history;
  const rows = (h.entries || []).length ? h.entries.map((e) => `
    <div class="detail-order">
      <div class="do-head">
        <strong>${escapeHtml(e.order_no)}</strong>
        <strong>${formatCurrency(e.total)}</strong>
      </div>
      <div class="items">${(parseItems(e.items)).map((it) => `${escapeHtml(it.name)} x${it.qty}`).join(', ')}</div>
      <div class="who" style="color:#6b7280">주문 ${formatDateTime(e.ordered_at)} · 완료 ${formatDateTime(e.completed_at)}</div>
    </div>`).join('') : '<div class="empty">해당 기간의 이력이 없습니다.</div>';

  const presets = [['today', '오늘'], ['yesterday', '어제'], ['7days', '최근 7일']];
  return `
    <div class="overlay" data-action="close-history">
      <div class="modal" data-stop="1">
        <div class="modal-head">
          <h2>${h.table_no}번 과거 이력</h2>
          <button class="btn ghost" data-action="close-history">✕</button>
        </div>
        <div class="modal-body">
          <div class="presets">
            ${presets.map(([k, label]) => `<button class="chip ${h.preset === k ? 'active' : ''}" data-action="hist-preset" data-preset="${k}">${label}</button>`).join('')}
            <button class="chip ${h.preset === 'custom' ? 'active' : ''}" data-action="hist-preset" data-preset="custom">직접 선택</button>
          </div>
          ${h.preset === 'custom' ? `
          <div class="date-range">
            <div class="field"><label>From</label><input id="hist-from" type="date" value="${h.from || ''}" /></div>
            <div class="field"><label>To</label><input id="hist-to" type="date" value="${h.to || ''}" /></div>
            <button class="btn sm" data-action="hist-apply">조회</button>
          </div>` : ''}
          ${rows}
        </div>
        <div class="modal-foot"><button class="btn secondary" data-action="close-history">닫기</button></div>
      </div>
    </div>`;
}

function modalMenuForm() {
  const f = state.menuForm;
  const isEdit = f.id != null;
  return `
    <div class="overlay" data-action="close-menu-form">
      <div class="modal small" data-stop="1">
        <div class="modal-head"><h2>${isEdit ? '메뉴 수정' : '새 메뉴'}</h2><button class="btn ghost" data-action="close-menu-form">✕</button></div>
        <div class="modal-body">
          <div class="form-grid">
            <div class="field"><label>카테고리 *</label><input id="mf-cat" value="${escapeHtml(f.category || '')}" /></div>
            <div class="field"><label>가격(원) *</label><input id="mf-price" type="number" inputmode="numeric" value="${f.price ?? ''}" /></div>
            <div class="field full"><label>메뉴명 *</label><input id="mf-name" value="${escapeHtml(f.name || '')}" /></div>
            <div class="field full"><label>설명</label><textarea id="mf-desc" rows="2">${escapeHtml(f.description || '')}</textarea></div>
            <div class="field full"><label>이미지 URL</label><input id="mf-img" value="${escapeHtml(f.image_url || '')}" /></div>
          </div>
        </div>
        <div class="modal-foot">
          <button class="btn secondary" data-action="close-menu-form">취소</button>
          <button class="btn" data-action="menu-save">${isEdit ? '수정' : '등록'}</button>
        </div>
      </div>
    </div>`;
}

function modalConfirm() {
  const c = state.confirm;
  return `
    <div class="overlay">
      <div class="modal small" data-stop="1">
        <div class="modal-head"><h2>확인</h2></div>
        <div class="modal-body">${escapeHtml(c.text)}</div>
        <div class="modal-foot">
          <button class="btn secondary" data-action="confirm-cancel">취소</button>
          <button class="btn ${c.danger ? 'danger' : ''}" data-action="confirm-ok">${escapeHtml(c.okLabel || '확인')}</button>
        </div>
      </div>
    </div>`;
}

// ================= API 흐름 =================
async function login() {
  const store_id = Number(document.getElementById('in-store').value);
  const username = document.getElementById('in-user').value.trim();
  const password = document.getElementById('in-pw').value;
  if (!store_id || !username || !password) { toast('모든 항목을 입력해 주세요.', 'error'); return; }
  try {
    const res = await api.post('/api/admin/login', { store_id, username, password });
    saveAuth({ access_token: res.access_token, expires_at: res.expires_at, store_id, username });
    state.view = 'dashboard';
    render();
    initDashboard();
  } catch (e) {
    if (e.status === 429) toast('로그인 시도가 제한되었습니다. 잠시 후 다시 시도해 주세요.', 'error');
    else if (e.status === 401) toast('자격 정보가 올바르지 않습니다.', 'error');
    else toast(e.message, 'error');
  }
}

async function initDashboard() {
  await refreshTables();
  connectSse();
}

async function refreshTables() {
  try {
    const tables = await api.get('/api/admin/tables');
    state.tables = tables || [];
    if (state.view === 'dashboard') render();
  } catch (e) {
    if (e.status !== 401) toast(e.message, 'error');
  }
}

function connectSse() {
  disconnectSse();
  sse = createSseClient({
    url: '/api/admin/orders/stream',
    getToken: () => state.auth?.access_token,
    onEvent: onSseEvent,
    onError: (err) => { if (err?.status === 401) logout(); },
  });
}
function disconnectSse() { sse?.close(); sse = null; }

// SSE 반영은 서버 값 신뢰: 이벤트 수신 시 목록/상세 재조회 (BR-D6). 신규주문은 하이라이트 (Q12=A).
function onSseEvent(type, data) {
  const tno = data?.table_no;
  switch (type) {
    case 'order.created':
      if (tno != null) highlightTable(tno);
      refreshTables();
      if (state.detail?.table_no === tno) refreshDetail();
      break;
    case 'order.status_changed':
    case 'order.deleted':
      refreshTables();
      if (state.detail?.table_no === tno) refreshDetail();
      break;
    case 'table_session.ended':
      refreshTables();
      if (state.detail?.table_no === tno) { state.detail = null; renderModals(); }
      break;
  }
}

function highlightTable(tno) {
  state.highlighted.add(tno);
  if (state.view === 'dashboard') render();
  setTimeout(() => {
    state.highlighted.delete(tno);
    if (state.view === 'dashboard') render();
  }, HIGHLIGHT_MS);
}

async function openDetail(table_no) {
  try {
    const orders = await api.get(`/api/admin/tables/${table_no}/orders`);
    state.detail = { table_no, orders: orders || [] };
    renderModals();
  } catch (e) {
    if (e.status === 404) { toast('활성 세션이 없습니다.', 'info'); }
    else if (e.status !== 401) toast(e.message, 'error');
  }
}
async function refreshDetail() {
  if (!state.detail) return;
  try {
    const orders = await api.get(`/api/admin/tables/${state.detail.table_no}/orders`);
    state.detail.orders = orders || [];
    renderModals();
  } catch (e) {
    if (e.status === 404) { state.detail = null; renderModals(); }
  }
}

async function setStatus(order_id, status) {
  try {
    await api.patch(`/api/admin/orders/${order_id}/status`, { status });
    toast('상태를 변경했습니다.', 'success');
    refreshDetail(); refreshTables();
  } catch (e) { if (e.status !== 401) toast(e.message, 'error'); }
}

function deleteOrder(order_id) {
  askConfirm('이 주문을 삭제할까요?', { danger: true, okLabel: '삭제' }, async () => {
    try {
      await api.del(`/api/admin/orders/${order_id}`);
      toast('주문을 삭제했습니다.', 'success');
      refreshDetail(); refreshTables();
    } catch (e) { if (e.status !== 401) toast(e.message, 'error'); }
  });
}

function endSession(table_no) {
  askConfirm('이용 완료 처리할까요? 현재 주문이 과거 이력으로 이동합니다.', { danger: true, okLabel: '이용 완료' }, async () => {
    try {
      await api.post(`/api/admin/tables/${table_no}/end-session`);
      toast('이용 완료 처리했습니다.', 'success');
      state.detail = null;
      renderModals();
      refreshTables();
    } catch (e) {
      if (e.status === 404) toast('활성 세션이 없습니다.', 'info');
      else if (e.status !== 401) toast(e.message, 'error');
    }
  });
}

// ---- 과거 이력 ----
async function openHistory(table_no) {
  state.history = { table_no, preset: 'today', from: '', to: '', entries: [] };
  renderModals();
  await loadHistory();
}
function presetRange(preset) {
  const d = new Date();
  const iso = (x) => x.toISOString().slice(0, 10);
  if (preset === 'today') return { from: iso(d), to: iso(d) };
  if (preset === 'yesterday') { const y = new Date(d); y.setDate(d.getDate() - 1); return { from: iso(y), to: iso(y) }; }
  if (preset === '7days') { const s = new Date(d); s.setDate(d.getDate() - 6); return { from: iso(s), to: iso(d) }; }
  return { from: '', to: '' };
}
async function loadHistory() {
  const h = state.history;
  let from = h.from, to = h.to;
  if (h.preset !== 'custom') { const r = presetRange(h.preset); from = r.from; to = r.to; h.from = from; h.to = to; }
  const qs = new URLSearchParams();
  if (from) qs.set('date_from', from);
  if (to) qs.set('date_to', to);
  try {
    const entries = await api.get(`/api/admin/tables/${h.table_no}/history?${qs.toString()}`);
    h.entries = entries || [];
    renderModals();
  } catch (e) { if (e.status !== 401) toast(e.message, 'error'); }
}

// ---- 메뉴 관리 ----
async function loadMenus() {
  try {
    const menus = await api.get('/api/admin/menus');
    state.menus = (menus || []).slice().sort((a, b) => (a.display_order ?? 0) - (b.display_order ?? 0));
    if (state.view === 'menuAdmin') render();
  } catch (e) { if (e.status !== 401) toast(e.message, 'error'); }
}
function openMenuForm(menu) {
  state.menuForm = menu ? { ...menu } : { category: '', name: '', price: '', description: '', image_url: '' };
  renderModals();
}
async function saveMenu() {
  const f = state.menuForm;
  const category = document.getElementById('mf-cat').value.trim();
  const name = document.getElementById('mf-name').value.trim();
  const price = Number(document.getElementById('mf-price').value);
  const description = document.getElementById('mf-desc').value.trim();
  const image_url = document.getElementById('mf-img').value.trim();
  if (!category || !name || !Number.isFinite(price) || price < 0) { toast('카테고리·이름·가격(0 이상)을 확인해 주세요.', 'error'); return; }
  const payload = { category, name, price, description: description || null, image_url: image_url || null };
  try {
    if (f.id != null) await api.patch(`/api/admin/menus/${f.id}`, payload);
    else await api.post('/api/admin/menus', payload);
    toast(f.id != null ? '메뉴를 수정했습니다.' : '메뉴를 등록했습니다.', 'success');
    state.menuForm = null;
    renderModals();
    loadMenus();
  } catch (e) { if (e.status !== 401) toast(e.message, 'error'); }
}
function deleteMenu(id) {
  askConfirm('이 메뉴를 삭제할까요?', { danger: true, okLabel: '삭제' }, async () => {
    try {
      await api.del(`/api/admin/menus/${id}`);
      toast('메뉴를 삭제했습니다.', 'success');
      loadMenus();
    } catch (e) { if (e.status !== 401) toast(e.message, 'error'); }
  });
}
async function reorderMenu(id, dir) {
  const sorted = state.menus.slice().sort((a, b) => (a.display_order ?? 0) - (b.display_order ?? 0));
  const i = sorted.findIndex((m) => m.id === id);
  const j = i + dir;
  if (i < 0 || j < 0 || j >= sorted.length) return;
  [sorted[i], sorted[j]] = [sorted[j], sorted[i]];
  const ordered_ids = sorted.map((m) => m.id);
  try {
    await api.post('/api/admin/menus/reorder', { ordered_ids });
    loadMenus();
  } catch (e) { if (e.status !== 401) toast(e.message, 'error'); }
}

// ================= 확인 모달 / 토스트 =================
function askConfirm(text, opts, onOk) {
  state.confirm = { text, danger: !!opts.danger, okLabel: opts.okLabel };
  confirmOnOk = onOk;
  renderModals();
}
function toast(text, type = 'info', ttl = 2800) {
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = text;
  toastHost.appendChild(el);
  setTimeout(() => el.remove(), ttl);
}

// ================= 헬퍼 =================
function parseItems(items) {
  if (Array.isArray(items)) return items;
  if (typeof items === 'string') { try { return JSON.parse(items) || []; } catch { return []; } }
  return [];
}

// ================= 이벤트 위임 =================
document.body.addEventListener('click', (ev) => {
  const el = ev.target.closest('[data-action]');
  if (!el) return;
  const a = el.dataset.action;
  const tno = el.dataset.tno != null ? Number(el.dataset.tno) : null;
  const oid = el.dataset.oid != null ? Number(el.dataset.oid) : null;
  const id = el.dataset.id != null ? Number(el.dataset.id) : null;

  // 오버레이 배경 클릭으로 닫힐 때, 모달 본문 클릭은 무시
  if ((a === 'close-detail' || a === 'close-history' || a === 'close-menu-form') && ev.target.closest('[data-stop]') && !ev.target.closest('.btn')) return;

  switch (a) {
    case 'login': login(); break;
    case 'logout': logout(); break;
    case 'go-menu-admin': state.view = 'menuAdmin'; render(); loadMenus(); break;
    case 'go-dashboard': state.view = 'dashboard'; render(); refreshTables(); break;

    case 'filter-all': state.tableFilter.clear(); render(); break;
    case 'filter':
      if (state.tableFilter.has(tno)) state.tableFilter.delete(tno); else state.tableFilter.add(tno);
      render(); break;

    case 'open-detail': openDetail(tno); break;
    case 'close-detail': state.detail = null; renderModals(); break;
    case 'set-status': setStatus(oid, el.dataset.status); break;
    case 'delete-order': deleteOrder(oid); break;
    case 'end-session': endSession(tno); break;

    case 'open-history': openHistory(tno); break;
    case 'close-history': state.history = null; renderModals(); break;
    case 'hist-preset': state.history.preset = el.dataset.preset; loadHistoryIfNotCustom(); break;
    case 'hist-apply': applyCustomHistory(); break;

    case 'menu-new': openMenuForm(null); break;
    case 'menu-edit': openMenuForm(state.menus.find((m) => m.id === id)); break;
    case 'menu-save': saveMenu(); break;
    case 'close-menu-form': state.menuForm = null; renderModals(); break;
    case 'menu-delete': deleteMenu(id); break;
    case 'menu-up': reorderMenu(id, -1); break;
    case 'menu-down': reorderMenu(id, +1); break;

    case 'confirm-cancel': state.confirm = null; confirmOnOk = null; renderModals(); break;
    case 'confirm-ok': { const fn = confirmOnOk; state.confirm = null; confirmOnOk = null; renderModals(); fn?.(); break; }
  }
});

function loadHistoryIfNotCustom() {
  if (state.history.preset === 'custom') { renderModals(); }
  else loadHistory();
}
function applyCustomHistory() {
  state.history.from = document.getElementById('hist-from').value;
  state.history.to = document.getElementById('hist-to').value;
  loadHistory();
}

init();
