// F1 CustomerApp (U3) — 단일 HTML + JS 뷰 전환 (Q1=A, Q3=A)
// consumes: U1 인증/메뉴 API, U2 주문 API. 모든 호출은 Authorization: Bearer.
import { createApiClient } from '../shared/api.js';
import { formatCurrency, formatDateTime, escapeHtml, statusLabel } from '../shared/format.js';

const AUTH_KEY = 'to_customer_auth';
const CART_KEY = 'to_cart';

const PLACEHOLDER = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(
  '<svg xmlns="http://www.w3.org/2000/svg" width="160" height="120">' +
  '<rect width="100%" height="100%" fill="#e5e7eb"/>' +
  '<text x="50%" y="50%" fill="#9ca3af" font-family="sans-serif" font-size="14" ' +
  'text-anchor="middle" dominant-baseline="middle">이미지 없음</text></svg>'
);

// ---- 상태 (모듈 스코프 plain 객체) ----
const state = {
  view: 'auth',            // 'auth' | 'menu' | 'orderSuccess' | 'orderHistory' (Q20=D 로 auth 추가)
  auth: null,              // { tablet_token, expires_at, config:{store_id, table_no} }
  menus: [],
  activeCategory: 'ALL',
  cart: { store_id: null, table_no: null, items: [] },  // items: {menu_id,name,unit_price,qty}
  cartExpanded: false,
  orders: [],
  lastOrderNo: null,
  submitting: false,
};

const root = document.getElementById('app');
const toastHost = document.getElementById('toast-host');

const api = createApiClient({
  getToken: () => state.auth?.tablet_token,
  onUnauthorized: handleUnauthorized,
});

// ---- 저장소 ----
function loadAuth() {
  try { return JSON.parse(localStorage.getItem(AUTH_KEY)); } catch { return null; }
}
function saveAuth(auth) {
  state.auth = auth;
  localStorage.setItem(AUTH_KEY, JSON.stringify(auth));
}
function discardToken() {
  // 만료 토큰만 폐기, config(store/table)는 입력 프리필용으로 유지 (Q20=D / BR-A3)
  if (state.auth) {
    const { config } = state.auth;
    state.auth = config ? { config } : null;
    if (state.auth) localStorage.setItem(AUTH_KEY, JSON.stringify(state.auth));
    else localStorage.removeItem(AUTH_KEY);
  }
}
function tokenValid(auth) {
  return !!(auth?.tablet_token && auth?.expires_at && new Date(auth.expires_at).getTime() > Date.now());
}

function loadCart() {
  let c;
  try { c = JSON.parse(localStorage.getItem(CART_KEY)); } catch { c = null; }
  const ctxStore = state.auth?.config?.store_id ?? null;
  const ctxTable = state.auth?.config?.table_no ?? null;
  // 저장된 store/table 이 현재 컨텍스트와 불일치하면 자동 초기화 (Q5=C / BR-C2)
  if (!c || (ctxStore != null && (c.store_id !== ctxStore || c.table_no !== ctxTable))) {
    state.cart = { store_id: ctxStore, table_no: ctxTable, items: [] };
  } else {
    state.cart = { store_id: c.store_id, table_no: c.table_no, items: Array.isArray(c.items) ? c.items : [] };
  }
}
function saveCart() {
  localStorage.setItem(CART_KEY, JSON.stringify(state.cart));
}

// ---- 401 처리: 토큰 폐기 + 재인증 화면 (자동 재발급 없음, Q20=D) ----
function handleUnauthorized() {
  discardToken();
  state.view = 'auth';
  render();
}

// ---- 부트스트랩 ----
function init() {
  state.auth = loadAuth();
  loadCart();
  if (tokenValid(state.auth)) {
    state.view = 'menu';
    render();
    loadMenu();
  } else {
    discardToken();
    state.view = 'auth';
    render();
  }
}

// ================= 렌더 =================
function render() {
  switch (state.view) {
    case 'auth': root.innerHTML = viewAuth(); break;
    case 'menu': root.innerHTML = viewMenu(); break;
    case 'orderSuccess': root.innerHTML = viewSuccess(); break;
    case 'orderHistory': root.innerHTML = viewHistory(); break;
    default: root.innerHTML = '';
  }
}

function viewAuth() {
  const cfg = state.auth?.config ?? {};
  return `
    <div class="auth-wrap">
      <h1>테이블 인증</h1>
      <p class="hint" style="color:#6b7280">태블릿 인증 정보를 입력해 주세요.</p>
      <div class="field">
        <label>매장 식별자(store_id)</label>
        <input id="in-store" type="number" inputmode="numeric" value="${cfg.store_id ?? ''}" />
      </div>
      <div class="field">
        <label>테이블 번호</label>
        <input id="in-table" type="number" inputmode="numeric" value="${cfg.table_no ?? ''}" />
      </div>
      <div class="field">
        <label>테이블 비밀번호</label>
        <input id="in-pw" type="password" autocomplete="off" />
      </div>
      <button class="btn" data-action="auth-submit">인증하고 시작하기</button>
    </div>`;
}

function viewMenu() {
  const cats = ['ALL', ...distinctCategories()];
  const tabs = cats.map((c) => `
    <button class="cat-tab ${state.activeCategory === c ? 'active' : ''}" data-action="cat" data-cat="${escapeHtml(c)}">
      ${c === 'ALL' ? '전체' : escapeHtml(c)}
    </button>`).join('');

  const visible = state.menus.filter((m) => state.activeCategory === 'ALL' || m.category === state.activeCategory);
  const cards = visible.length ? visible.map(menuCard).join('') :
    `<div class="empty">표시할 메뉴가 없습니다.</div>`;

  return `
    <div class="topbar">
      <span class="title">메뉴</span>
      <button class="btn secondary" data-action="go-history">주문내역</button>
    </div>
    <div class="cat-tabs">${tabs}</div>
    <div class="menu-grid">${cards}</div>
    ${cartBar()}`;
}

function menuCard(m) {
  return `
    <div class="menu-card">
      <img class="menu-img" src="${escapeHtml(m.image_url || PLACEHOLDER)}" alt="${escapeHtml(m.name)}" />
      <div class="body">
        <div class="name">${escapeHtml(m.name)}</div>
        <div class="price">${formatCurrency(m.price)}</div>
        <div class="desc">${escapeHtml(m.description || '')}</div>
        <button class="btn" data-action="add" data-id="${m.id}">담기</button>
      </div>
    </div>`;
}

function cartBar() {
  const count = state.cart.items.reduce((s, it) => s + it.qty, 0);
  const total = cartTotal();
  const detail = state.cartExpanded ? `
    <div class="cart-detail">
      ${state.cart.items.length ? state.cart.items.map(cartItemRow).join('') : '<div class="empty">장바구니가 비어있습니다.</div>'}
      <div class="cart-actions">
        <button class="btn secondary" data-action="clear-cart" ${count ? '' : 'disabled'}>비우기</button>
        <button class="btn" data-action="submit-order" ${count && !state.submitting ? '' : 'disabled'}>
          ${state.submitting ? '주문 중…' : '주문하기'}
        </button>
      </div>
    </div>` : '';
  return `
    <div class="cart-bar">
      <div class="cart-summary" data-action="toggle-cart">
        <span class="info">🛒 ${count}개</span>
        <span class="info">${formatCurrency(total)} ${state.cartExpanded ? '▾' : '▴'}</span>
      </div>
      ${detail}
    </div>`;
}

function cartItemRow(it) {
  return `
    <div class="cart-item">
      <span class="ci-name">${escapeHtml(it.name)}</span>
      <span>${formatCurrency(it.unit_price * it.qty)}</span>
      <div class="qty-ctl">
        <button data-action="dec" data-id="${it.menu_id}">−</button>
        <span>${it.qty}</span>
        <button data-action="inc" data-id="${it.menu_id}">＋</button>
      </div>
    </div>`;
}

function viewSuccess() {
  return `
    <div class="success-wrap">
      <div style="font-size:48px">✅</div>
      <h1>주문 완료</h1>
      <div class="order-no">${escapeHtml(state.lastOrderNo || '')}</div>
      <p class="hint">5초 후 메뉴 화면으로 돌아갑니다.</p>
      <button class="btn ghost" data-action="back-to-menu">지금 메뉴로</button>
    </div>`;
}

function viewHistory() {
  const rows = state.orders.length ? state.orders.map((o) => `
    <div class="order-row">
      <div class="row-head">
        <strong>${escapeHtml(o.order_no)}</strong>
        <span class="badge ${o.status}">${statusLabel(o.status)}</span>
      </div>
      <div class="items">${o.items.map((it) => `${escapeHtml(it.name)} x${it.qty}`).join(', ')}</div>
      <div class="row-head" style="margin-top:8px;margin-bottom:0">
        <span class="hint" style="color:#6b7280">${formatDateTime(o.created_at)}</span>
        <strong>${formatCurrency(o.total)}</strong>
      </div>
    </div>`).join('') : '<div class="empty">현재 세션의 주문 내역이 없습니다.</div>';
  return `
    <div class="topbar">
      <span class="title">주문 내역</span>
      <button class="btn secondary" data-action="back-to-menu">메뉴로</button>
    </div>
    <div class="history-wrap">${rows}</div>`;
}

// ================= 파생값 =================
function distinctCategories() {
  return [...new Set(state.menus.map((m) => m.category))];
}
function cartTotal() {
  return state.cart.items.reduce((s, it) => s + it.unit_price * it.qty, 0);
}

// ================= API 흐름 =================
async function loadMenu() {
  try {
    const menus = await api.get('/api/menus');
    state.menus = (menus || []).slice().sort((a, b) => (a.display_order ?? 0) - (b.display_order ?? 0));
    if (state.view === 'menu') render();
  } catch (e) {
    if (e.status !== 401) toast(e.message, 'error');
  }
}

async function authSubmit() {
  const store_id = Number(document.getElementById('in-store').value);
  const table_no = Number(document.getElementById('in-table').value);
  const table_password = document.getElementById('in-pw').value;
  if (!store_id || !table_no || !table_password) {
    toast('모든 항목을 입력해 주세요.', 'error');
    return;
  }
  try {
    // POST /api/tablet/login → {tablet_token, expires_at}
    const res = await api.post('/api/tablet/login', { store_id, table_no, table_password });
    // table_password 는 저장하지 않는다 (Q20=D / BR-A4)
    saveAuth({ tablet_token: res.tablet_token, expires_at: res.expires_at, config: { store_id, table_no } });
    loadCart();
    state.view = 'menu';
    render();
    loadMenu();
  } catch (e) {
    if (e.status === 401) toast('인증 정보가 올바르지 않습니다.', 'error');
    else toast(e.message, 'error');
  }
}

async function submitOrder() {
  if (!state.cart.items.length) { toast('장바구니가 비어있습니다.', 'error'); return; }
  if (state.submitting) return;
  state.submitting = true;
  render();
  try {
    // 계약 §5.3: body 는 items 만. store/table 은 서버가 TabletContext 로 채움.
    const body = { items: state.cart.items.map((it) => ({ menu_id: it.menu_id, qty: it.qty })) };
    const res = await api.post('/api/orders', body);
    state.lastOrderNo = res.order_no;
    state.cart.items = [];
    saveCart();
    state.submitting = false;
    state.cartExpanded = false;
    state.view = 'orderSuccess';
    render();
    setTimeout(() => {
      if (state.view === 'orderSuccess') { state.view = 'menu'; render(); }
    }, 5000); // Q9=A / BR-O2
  } catch (e) {
    state.submitting = false;
    render();
    if (e.status !== 401) toast(e.message || '주문에 실패했습니다.', 'error'); // 실패 시 장바구니 유지 (BR-O3)
  }
}

async function openHistory() {
  state.view = 'orderHistory';
  render();
  try {
    const orders = await api.get('/api/orders/current');
    state.orders = orders || [];
    if (state.view === 'orderHistory') render();
  } catch (e) {
    if (e.status !== 401) toast(e.message, 'error');
  }
}

// ================= 장바구니 조작 =================
function addToCart(menuId) {
  const menu = state.menus.find((m) => m.id === menuId);
  if (!menu) return;
  const found = state.cart.items.find((it) => it.menu_id === menuId);
  if (found) found.qty += 1;
  else state.cart.items.push({ menu_id: menu.id, name: menu.name, unit_price: menu.price, qty: 1 });
  saveCart();
  render();
}
function changeQty(menuId, delta) {
  const it = state.cart.items.find((i) => i.menu_id === menuId);
  if (!it) return;
  it.qty += delta;
  if (it.qty <= 0) state.cart.items = state.cart.items.filter((i) => i.menu_id !== menuId);
  saveCart();
  render();
}
function clearCart() {
  state.cart.items = [];
  saveCart();
  render();
}

// ================= 토스트 =================
function toast(text, type = 'info', ttl = 2600) {
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = text;
  toastHost.appendChild(el);
  setTimeout(() => el.remove(), ttl);
}

// ================= 이벤트 위임 =================
root.addEventListener('click', (ev) => {
  const target = ev.target.closest('[data-action]');
  if (!target) return;
  const action = target.dataset.action;
  const id = target.dataset.id ? Number(target.dataset.id) : null;
  switch (action) {
    case 'auth-submit': authSubmit(); break;
    case 'cat': state.activeCategory = target.dataset.cat; render(); break;
    case 'add': addToCart(id); toast('담았습니다.', 'success', 1200); break;
    case 'toggle-cart': state.cartExpanded = !state.cartExpanded; render(); break;
    case 'inc': changeQty(id, +1); break;
    case 'dec': changeQty(id, -1); break;
    case 'clear-cart': clearCart(); break;
    case 'submit-order': submitOrder(); break;
    case 'go-history': openHistory(); break;
    case 'back-to-menu': state.view = 'menu'; render(); break;
  }
});

// 이미지 로드 실패 → 공통 플레이스홀더 (Q10=A / BR-X3). error 는 버블 안 하므로 capture.
root.addEventListener('error', (ev) => {
  const img = ev.target;
  if (img?.classList?.contains('menu-img') && img.src !== PLACEHOLDER) {
    img.src = PLACEHOLDER;
  }
}, true);

init();
