/* ============================================================================
   SENTINEL — Biometric Identification Console
   Vanilla SPA talking to the FastAPI face-recognition backend.
   ========================================================================== */
'use strict';

// ---------- state ----------
const ROLE_LEVEL = { viewer: 1, operator: 2, admin: 3 };
const S = {
  api: localStorage.getItem('fr_api') || (location.origin + '/api/v1'),
  token: localStorage.getItem('fr_token') || null,
  user: localStorage.getItem('fr_user') || null,
  role: localStorage.getItem('fr_role') || 'viewer',
  view: 'overview',
};
const can = (need) => (ROLE_LEVEL[S.role] || 0) >= ROLE_LEVEL[need];

// ---------- tiny dom helpers ----------
const $  = (s, r = document) => r.querySelector(s);
const el = (html) => { const t = document.createElement('template'); t.innerHTML = html.trim(); return t.content.firstElementChild; };
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const shortId = (id) => (id ? String(id).slice(0, 8) : '—');
const pct = (x) => (x == null ? '—' : (x * 100).toFixed(1) + '%');

// ---------- icons ----------
const I = {
  grid:   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>',
  enroll: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 4-6 8-6 1.5 0 3 .3 4 .8"/><path d="M18 14v6M15 17h6"/></svg>',
  verify: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><circle cx="11" cy="11" r="7"/><path d="m8 11 2 2 4-4"/></svg>',
  search: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><circle cx="11" cy="11" r="7"/><path d="m21 21-4-4"/></svg>',
  people: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><circle cx="9" cy="8" r="3.2"/><path d="M3 20c0-3.3 2.7-5 6-5s6 1.7 6 5"/><path d="M16 6.5a3 3 0 0 1 0 5.8M17 20c0-2.5-1-4-2.5-4.6"/></svg>',
  import: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M4 7V5a2 2 0 0 1 2-2h4l2 2h6a2 2 0 0 1 2 2v3"/><path d="M3 9h18l-1.5 10a2 2 0 0 1-2 1.8H6.5a2 2 0 0 1-2-1.8z"/><path d="M12 12v5M9.5 14.5 12 17l2.5-2.5"/></svg>',
  log:    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M5 3h10l4 4v14H5z"/><path d="M14 3v4h4M8 13h8M8 17h5"/></svg>',
  face:   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M6 9V6h3M18 9V6h-3M6 15v3h3M18 15v3h-3"/><circle cx="12" cy="12" r="3.5"/></svg>',
  inbox:  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 13h5l2 3h4l2-3h5M5 19h14a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2z"/></svg>',
  check:  '<svg viewBox="0 0 36 36" fill="none" stroke="currentColor" stroke-width="2.4"><circle cx="18" cy="18" r="14"/><path d="m12 18 4 4 8-8"/></svg>',
  cross:  '<svg viewBox="0 0 36 36" fill="none" stroke="currentColor" stroke-width="2.4"><circle cx="18" cy="18" r="14"/><path d="m13 13 10 10M23 13 13 23"/></svg>',
  cam:    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M3 8a2 2 0 0 1 2-2h2l1.5-2h7L17 6h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><circle cx="12" cy="12.5" r="3.4"/></svg>',
  key:    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><circle cx="8" cy="8" r="4.5"/><path d="M11 11l8 8M16 16l2-2M19 19l2-2"/></svg>',
  edit:   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M4 20h4L18.5 9.5a2.1 2.1 0 0 0-3-3L5 17v3z"/><path d="M13.5 6.5l3 3"/></svg>',
  trash:  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M4 7h16M9 7V5h6v2M6 7l1 13h10l1-13"/></svg>',
  swap:   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M4 9h13l-3-3M20 15H7l3 3"/></svg>',
};

// ---------- nav config ----------
const NAV = [
  { group: 'Operations', items: [
    { id: 'overview', label: 'Overview', icon: 'grid',   role: 'viewer' },
    { id: 'enroll',   label: 'Enroll',   icon: 'enroll', role: 'operator' },
    { id: 'verify',   label: 'Verify 1:1', icon: 'verify', role: 'viewer' },
    { id: 'search',   label: 'Identify 1:N', icon: 'search', role: 'viewer' },
  ]},
  { group: 'Data', items: [
    { id: 'persons', label: 'Persons',     icon: 'people', role: 'viewer' },
    { id: 'gallery', label: 'Face Gallery', icon: 'face',  role: 'viewer' },
    { id: 'import',  label: 'Bulk Import', icon: 'import', role: 'admin' },
    { id: 'logs',    label: 'Audit Log',   icon: 'log',    role: 'viewer' },
  ]},
  { group: 'Access', items: [
    { id: 'apikeys', label: 'API Keys', icon: 'key', role: 'admin' },
  ]},
];

// ============================================================================
// API
// ============================================================================
async function api(path, { method = 'GET', body = null, form = null } = {}) {
  const headers = {};
  if (S.token) headers.Authorization = 'Bearer ' + S.token;
  let payload = null;
  if (form) { payload = form; }                          // FormData / URLSearchParams
  else if (body != null) { headers['Content-Type'] = 'application/json'; payload = JSON.stringify(body); }

  let res;
  try {
    res = await fetch(S.api + path, { method, headers, body: payload });
  } catch (e) {
    throw new Error('Network error — is the API reachable at ' + S.api + '?');
  }
  if (res.status === 401 && S.token) { logout(); throw new Error('Session expired'); }

  let data = null;
  const ct = res.headers.get('content-type') || '';
  if (ct.includes('application/json')) data = await res.json().catch(() => null);

  if (!res.ok) {
    let msg = res.statusText;
    if (data) {
      if (data.error?.message) msg = data.error.message;
      else if (typeof data.detail === 'string') msg = data.detail;
      else if (Array.isArray(data.detail)) msg = data.detail.map((d) => d.msg).join('; ');
    }
    throw new Error(msg);
  }
  return data;
}

// ============================================================================
// TOASTS
// ============================================================================
function toast(title, msg, kind = 'ok') {
  const t = el(`<div class="toast ${kind}"><b>${esc(title)}</b>${esc(msg)}</div>`);
  $('#toasts').appendChild(t);
  setTimeout(() => { t.style.opacity = '0'; t.style.transition = 'opacity .3s'; setTimeout(() => t.remove(), 300); }, 4200);
}

// ============================================================================
// MODAL — generic overlay; resolves with a value or null (cancel)
// ============================================================================
function modal(title, bodyHTML, { okText = 'Save', onMount } = {}) {
  return new Promise((resolve) => {
    const ov = el(`
      <div class="modal-ov">
        <div class="modal">
          <div class="brackets"><span></span><span></span><span></span><span></span></div>
          <div class="modal-head"><h3>${esc(title)}</h3><button class="modal-x" data-x>✕</button></div>
          <div class="modal-body">${bodyHTML}</div>
          <div class="modal-foot">
            <button class="btn ghost" data-cancel>Cancel</button>
            <button class="btn primary" data-ok>${esc(okText)}</button>
          </div>
        </div>
      </div>`);
    const close = (val) => { ov.remove(); document.removeEventListener('keydown', onKey); resolve(val); };
    const onKey = (e) => { if (e.key === 'Escape') close(null); };
    ov.querySelector('[data-x]').onclick = () => close(null);
    ov.querySelector('[data-cancel]').onclick = () => close(null);
    ov.addEventListener('click', (e) => { if (e.target === ov) close(null); });
    ov.querySelector('[data-ok]').onclick = () => close(ov.querySelector('.modal-body'));
    document.addEventListener('keydown', onKey);
    document.body.appendChild(ov);
    if (onMount) onMount(ov.querySelector('.modal-body'), close);
  });
}

function confirmDanger(message) {
  return modal('Confirm', `<p style="font-family:var(--mono);font-size:13px;line-height:1.6">${esc(message)}</p>`,
    { okText: 'Delete' }).then((b) => !!b);
}

// ============================================================================
// AUTH
// ============================================================================
$('#authForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const err = $('#authError'); err.classList.remove('show');
  const btn = $('#loginBtn'); btn.disabled = true; btn.innerHTML = '<span class="spin"></span> Authenticating';
  S.api = ($('#loginApi').value.trim() || S.api).replace(/\/$/, '');
  try {
    const body = new URLSearchParams({ username: $('#loginUser').value, password: $('#loginPass').value });
    const data = await api('/auth/token', { method: 'POST', form: body });
    S.token = data.access_token;
    // decode role from JWT payload (no verification needed client-side)
    try {
      const p = JSON.parse(atob(data.access_token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')));
      S.role = p.role || 'viewer'; S.user = p.sub || $('#loginUser').value;
    } catch { S.user = $('#loginUser').value; }
    localStorage.setItem('fr_token', S.token);
    localStorage.setItem('fr_api', S.api);
    localStorage.setItem('fr_user', S.user);
    localStorage.setItem('fr_role', S.role);
    enterApp();
  } catch (ex) {
    err.textContent = '⚠ ' + ex.message; err.classList.add('show');
  } finally {
    btn.disabled = false; btn.innerHTML = 'Authenticate ▸';
  }
});

$('#logoutBtn').addEventListener('click', logout);
function logout() {
  S.token = null; localStorage.removeItem('fr_token');
  $('#app').classList.remove('show');
  $('#auth').classList.remove('hidden');
}

function enterApp() {
  $('#auth').classList.add('hidden');
  $('#app').classList.add('show');
  $('#userName').textContent = S.user || 'operator';
  $('#userRole').textContent = S.role;
  $('#userAv').textContent = (S.user || 'A')[0].toUpperCase();
  renderNav();
  go(location.hash.slice(1) || 'overview');   // restore the view from the URL on refresh
  checkSystem();
}

async function checkSystem() {
  try {
    const r = await api('/ready');
    const dot = $('#sysDot'), txt = $('#sysText');
    if (r.status === 'ok') { dot.className = 'dot'; txt.textContent = 'SYSTEM NOMINAL'; }
    else { dot.className = 'dot warn'; txt.textContent = r.models_loaded ? 'DB DEGRADED' : 'MODELS OFFLINE'; }
  } catch { $('#sysDot').className = 'dot off'; $('#sysText').textContent = 'API UNREACHABLE'; }
}

// ============================================================================
// NAV + ROUTER
// ============================================================================
function renderNav() {
  const nav = $('#nav'); nav.innerHTML = '';
  for (const g of NAV) {
    const items = g.items.filter((it) => can(it.role));
    if (!items.length) continue;
    nav.appendChild(el(`<div class="nav-label">${esc(g.group)}</div>`));
    for (const it of items) {
      const node = el(`<div class="nav-item" data-view="${it.id}">${I[it.icon]}<span>${esc(it.label)}</span></div>`);
      node.addEventListener('click', () => go(it.id));
      nav.appendChild(node);
    }
  }
}

const VIEWS = {}; // id -> { title, render }

// Active webcam teardown callbacks — released whenever we leave a view so the
// camera light never lingers after navigation.
const CAMERA_STOPPERS = [];
function releaseCameras() {
  while (CAMERA_STOPPERS.length) {
    try { CAMERA_STOPPERS.pop()(); } catch { /* ignore */ }
  }
}

function viewRole(id) {
  for (const g of NAV) for (const it of g.items) if (it.id === id) return it.role;
  return 'viewer';
}

function go(id) {
  if (!VIEWS[id] || !can(viewRole(id))) id = 'overview';
  releaseCameras();
  S.view = id;
  if (location.hash.slice(1) !== id) location.hash = id;   // reflect in URL → survives refresh
  document.querySelectorAll('.nav-item').forEach((n) => n.classList.toggle('active', n.dataset.view === id));
  const v = VIEWS[id];
  $('#viewTitle').textContent = v.title;
  $('#crumb').textContent = 'CONSOLE / ' + v.title.toUpperCase();
  const root = $('#view'); root.innerHTML = '';
  v.render(root);
}

// Back/forward + manual hash edits.
window.addEventListener('hashchange', () => {
  const id = location.hash.slice(1);
  if (S.token && id && id !== S.view && VIEWS[id]) go(id);
});

// ============================================================================
// VIEWFINDER component (signature element)
// ============================================================================
function Viewfinder() {
  const wrap = el(`
    <div class="viewfinder">
      <span class="vf-corner tl"></span><span class="vf-corner tr"></span>
      <span class="vf-corner bl"></span><span class="vf-corner br"></span>
      <div class="scanline"></div>
      <video class="vf-video" playsinline muted></video>
      <div class="placeholder">
        ${I.face}
        <p>Drop image, <b>click to browse</b>, or use the <b>camera</b><br>JPG · PNG · WEBP · max 15 MB</p>
      </div>
      <canvas></canvas>
      <div class="vf-tools">
        <button class="vf-btn" data-act="cam" title="Use camera">${I.cam}</button>
      </div>
      <div class="vf-capture">
        <button class="vf-stop" data-act="stopcam" title="Stop camera">✕</button>
        <button class="vf-shutter" data-act="shoot" title="Capture frame"></button>
      </div>
    </div>`);
  const input = el('<input type="file" accept="image/*" style="display:none">');
  wrap.appendChild(input);
  const canvas = $('canvas', wrap), ph = $('.placeholder', wrap), video = $('video', wrap);
  let file = null, img = null, stream = null;

  const open = () => input.click();
  wrap.addEventListener('click', (e) => {
    if (e.target.closest('.vf-btn, .vf-capture, video, canvas, input')) return;  // controls self-handle
    if (stream) return;                                                          // ignore while live
    open();
  });
  input.addEventListener('change', () => input.files[0] && load(input.files[0]));
  ['dragenter', 'dragover'].forEach((ev) => wrap.addEventListener(ev, (e) => { e.preventDefault(); wrap.classList.add('dragover'); }));
  ['dragleave', 'drop'].forEach((ev) => wrap.addEventListener(ev, (e) => { e.preventDefault(); wrap.classList.remove('dragover'); }));
  wrap.addEventListener('drop', (e) => { const f = e.dataTransfer.files[0]; if (f) load(f); });

  // ---- camera ----
  $('[data-act=cam]', wrap).addEventListener('click', (e) => { e.stopPropagation(); startCamera(); });
  $('[data-act=stopcam]', wrap).addEventListener('click', (e) => { e.stopPropagation(); stopCamera(); });
  $('[data-act=shoot]', wrap).addEventListener('click', (e) => { e.stopPropagation(); shoot(); });

  async function startCamera() {
    if (!navigator.mediaDevices?.getUserMedia) {
      return toast('Camera unavailable', 'Needs HTTPS or a localhost origin', 'err');
    }
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 960 }, facingMode: 'user' },
        audio: false,
      });
    } catch (err) {
      stream = null;
      const msg = err.name === 'NotAllowedError' ? 'Permission denied'
        : err.name === 'NotFoundError' ? 'No camera found' : (err.message || err.name);
      return toast('Camera blocked', msg, 'err');
    }
    CAMERA_STOPPERS.push(stopCamera);
    file = null;
    ph.style.display = 'none';
    const im = $('img', wrap); if (im) im.style.display = 'none';
    clearBox();
    video.srcObject = stream;
    await video.play().catch(() => {});
    wrap.classList.add('live');
  }

  function shoot() {
    if (!stream || !video.videoWidth) return;
    const off = document.createElement('canvas');
    off.width = video.videoWidth; off.height = video.videoHeight;
    off.getContext('2d').drawImage(video, 0, 0, off.width, off.height);
    off.toBlob((blob) => {
      if (!blob) return;
      stopCamera();
      load(new File([blob], 'camera.jpg', { type: 'image/jpeg' }));  // treat capture like an upload
    }, 'image/jpeg', 0.95);
  }

  function stopCamera() {
    wrap.classList.remove('live');
    if (stream) { stream.getTracks().forEach((t) => t.stop()); stream = null; }
    video.srcObject = null;
  }

  function load(f) {
    stopCamera();
    file = f; ph.style.display = 'none';
    let im = $('img', wrap);
    if (!im) { im = el('<img>'); wrap.insertBefore(im, canvas); }
    im.style.display = 'block';
    im.src = URL.createObjectURL(f);
    im.onload = () => { img = im; clearBox(); };
  }
  function clearBox() {
    const r = wrap.getBoundingClientRect();
    canvas.width = r.width; canvas.height = r.height;
    canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height);
  }
  function scanning(on) { wrap.classList.toggle('scanning', on); }

  // draw a targeting reticle from a bbox in natural-image coordinates
  function reticle(bbox, label, ok = true) {
    if (!img) return;
    clearBox();
    const ctx = canvas.getContext('2d');
    const cw = canvas.width, ch = canvas.height;
    const nW = img.naturalWidth, nH = img.naturalHeight;
    const scale = Math.min(cw / nW, ch / nH);
    const dW = nW * scale, dH = nH * scale;
    const ox = (cw - dW) / 2, oy = (ch - dH) / 2;
    const x = ox + bbox.x1 * scale, y = oy + bbox.y1 * scale;
    const w = (bbox.x2 - bbox.x1) * scale, h = (bbox.y2 - bbox.y1) * scale;
    const col = ok ? '#b6ff3a' : '#ff5747';
    ctx.strokeStyle = col; ctx.lineWidth = 1.5; ctx.shadowColor = col; ctx.shadowBlur = 8;
    const c = Math.min(w, h) * 0.28;
    const seg = [[x, y, 1, 0], [x, y, 0, 1], [x + w, y, -1, 0], [x + w, y, 0, 1],
                 [x, y + h, 1, 0], [x, y + h, 0, -1], [x + w, y + h, -1, 0], [x + w, y + h, 0, -1]];
    ctx.beginPath();
    for (const [sx, sy, dx, dy] of seg) { ctx.moveTo(sx, sy); ctx.lineTo(sx + dx * c, sy + dy * c); }
    ctx.stroke();
    // crosshair
    ctx.shadowBlur = 0; ctx.globalAlpha = .5;
    ctx.beginPath();
    ctx.moveTo(x + w / 2, y + h / 2 - 7); ctx.lineTo(x + w / 2, y + h / 2 + 7);
    ctx.moveTo(x + w / 2 - 7, y + h / 2); ctx.lineTo(x + w / 2 + 7, y + h / 2);
    ctx.stroke(); ctx.globalAlpha = 1;
    // label
    if (label) {
      ctx.font = '600 11px IBM Plex Mono, monospace';
      const tw = ctx.measureText(label).width + 12;
      ctx.fillStyle = col; ctx.fillRect(x, y - 18, tw, 16);
      ctx.fillStyle = '#0a0f02'; ctx.fillText(label, x + 6, y - 6);
    }
  }

  function reset() {
    stopCamera();
    file = null; img = null;
    const im = $('img', wrap); if (im) im.remove();
    ph.style.display = '';
    clearBox();
  }

  return { el: wrap, getFile: () => file, scanning, reticle, reset, hasFile: () => !!file };
}

// A passive display box (same HUD styling) for reference/comparison images.
function ThumbBox(title) {
  const wrap = el(`
    <div class="viewfinder thumbbox">
      <span class="vf-corner tl"></span><span class="vf-corner tr"></span>
      <span class="vf-corner bl"></span><span class="vf-corner br"></span>
      <div class="scanline"></div>
      <div class="placeholder">${I.face}<p>${esc(title)}</p></div>
    </div>`);
  let timer = null;
  const imgEl = () => { let im = $('img', wrap); if (!im) { im = el('<img>'); wrap.insertBefore(im, $('.placeholder', wrap)); } return im; };

  function setImage(src) {
    stop();
    if (!src) return placeholder(title);
    imgEl().src = src; $('.placeholder', wrap).style.display = 'none';
  }
  function placeholder(text) {
    stop();
    const im = $('img', wrap); if (im) im.remove();
    $('.placeholder p', wrap).textContent = text; $('.placeholder', wrap).style.display = '';
  }
  function startCycle(srcs) {
    stop();
    if (!srcs || !srcs.length) return;
    wrap.classList.add('scanning');
    const im = imgEl(); $('.placeholder', wrap).style.display = 'none';
    let i = 0;
    timer = setInterval(() => { im.src = srcs[i % srcs.length]; i++; }, 85);
  }
  function stop() { if (timer) { clearInterval(timer); timer = null; } wrap.classList.remove('scanning'); }
  return { el: wrap, setImage, placeholder, startCycle, stop };
}

function meter(score, threshold) {
  const ok = score >= threshold;
  const node = el(`
    <div class="meter">
      <div class="meter-track">
        <div class="meter-fill ${ok ? '' : 'bad'}"></div>
        <div class="meter-ticks"></div>
        <div class="meter-thresh" style="left:${(threshold * 100).toFixed(1)}%"></div>
        <div class="meter-val">${pct(score)}</div>
      </div>
      <div class="meter-scale"><span>0.0</span><span>0.5</span><span>1.0</span></div>
    </div>`);
  requestAnimationFrame(() => { $('.meter-fill', node).style.width = Math.max(2, Math.min(100, score * 100)) + '%'; });
  return node;
}

// Render a 512-D embedding as a signed heatmap "fingerprint" onto a canvas.
// Positive dims -> lime, negative -> cyan; intensity scaled by |value| / max.
function fingerprint(canvas, emb, cols = 32) {
  if (!canvas || !emb || !emb.length) return;
  const ctx = canvas.getContext('2d');
  const n = emb.length;
  const rows = Math.ceil(n / cols);
  const cw = canvas.width / cols;
  const ch = canvas.height / rows;
  let max = 0;
  for (const v of emb) { const a = Math.abs(v); if (a > max) max = a; }
  max = max || 1;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  for (let i = 0; i < n; i++) {
    const v = emb[i] / max;
    const c = i % cols, r = (i / cols) | 0;
    const a = Math.min(1, Math.abs(v) * 1.25 + 0.05);
    ctx.fillStyle = v >= 0 ? `rgba(182,255,58,${a})` : `rgba(56,214,207,${a})`;
    ctx.fillRect(c * cw, r * ch, Math.ceil(cw), Math.ceil(ch));
  }
}

// shared: load person <option>s
async function personOptions() {
  const ppl = await api('/persons?limit=500');
  return ppl.map((p) => `<option value="${p.id}">${esc(p.full_name)} · ${shortId(p.id)}</option>`).join('');
}

// ============================================================================
// VIEW: OVERVIEW
// ============================================================================
VIEWS.overview = { title: 'Overview', render: async (root) => {
  root.innerHTML = `
    <div class="view-grid stagger">
      <div class="stats" id="ovStats">${[0,1,2,3].map(() => `
        <div class="stat"><div class="k">loading</div><div class="v">··</div></div>`).join('')}</div>
      <div class="panel">
        <div class="brackets"><span></span><span></span><span></span><span></span></div>
        <div class="panel-head"><h3>Recent Activity</h3><button class="btn sm ghost" id="ovRefresh">↻ Refresh</button></div>
        <div class="panel-body" id="ovFeed"><div class="empty"><span class="spin"></span></div></div>
      </div>
    </div>`;
  $('#ovRefresh', root).addEventListener('click', loadOverview);
  loadOverview();

  async function loadOverview() {
    try {
      const s = await api('/stats');
      const stats = $('#ovStats', root); if (!stats) return;   // navigated away
      stats.innerHTML = [
        ['Registered Persons', s.total_persons, 'identities in gallery', ''],
        ['Enrolled Faces', s.total_faces, 'embedding vectors', 'lime'],
        ['Recognition Events', s.total_events, 'lifetime queries', ''],
        ['Match Rate', pct(s.match_rate), `${s.successful_events} successful`, 'lime'],
      ].map(([k, v, sub, cls]) => `
        <div class="stat"><div class="k">${k}</div><div class="v ${cls}">${v}</div><div class="sub">${sub}</div></div>`).join('');

      const logs = await api('/logs?limit=12');
      const feed = $('#ovFeed', root); if (!feed) return;
      feed.innerHTML = logs.length ? logsTable(logs) : emptyState('No recognition events yet');
    } catch (e) { toast('Load failed', e.message, 'err'); const f = $('#ovFeed', root); if (f) f.innerHTML = emptyState(e.message); }
  }
}};

// ============================================================================
// VIEW: ENROLL
// ============================================================================
VIEWS.enroll = { title: 'Enroll', render: async (root) => {
  const vf = Viewfinder();
  const queue = [];  // File[] staged for this person
  root.innerHTML = `<div class="scan-cols stagger"></div>`;
  const cols = $('.scan-cols', root);

  const left = el(`<div class="panel"><div class="brackets"><span></span><span></span><span></span><span></span></div>
    <div class="panel-head"><h3>Capture Subject</h3><span class="kicker">SCRFD · ALIGN · ARCFACE</span></div>
    <div class="panel-body"></div></div>`);
  const body = $('.panel-body', left);
  body.appendChild(vf.el);
  const tools = el(`<div>
      <div class="inline" style="margin-top:12px">
        <button class="btn sm" id="enAdd">+ Add to batch</button>
        <button class="btn sm ghost" id="enPick">⇪ Add files…</button>
      </div>
      <div class="queue" id="enQueue"></div>
    </div>`);
  body.appendChild(tools);
  const multi = el('<input type="file" accept="image/*" multiple style="display:none">');
  body.appendChild(multi);
  cols.appendChild(left);

  const right = el(`<div class="panel pad">
    <div class="brackets"><span></span><span></span><span></span><span></span></div>
    <div class="form-row"><label>Assign to Person</label>
      <div class="inline"><select id="enPerson"><option>loading…</option></select></div></div>
    <div class="form-row"><label>Or register a new identity</label>
      <div class="inline"><input id="enNew" placeholder="Full name (e.g. Jane Doe)"><button class="btn sm" id="enCreate">+ Add</button></div></div>
    <button class="btn primary block" id="enSubmit" style="margin-top:6px">▸ Enroll batch</button>
    <p class="kicker" style="margin-top:10px">Multiple images of one person improve recall — all are enrolled under that identity.</p>
    <div id="enResult" style="margin-top:18px"></div>
  </div>`);
  cols.appendChild(right);

  function renderQueue() {
    const q = $('#enQueue', body);
    q.innerHTML = queue.map((f, i) => `
      <div class="qitem"><img src="${URL.createObjectURL(f)}"><button data-i="${i}" title="remove">✕</button></div>`).join('');
    q.querySelectorAll('button').forEach((b) => b.onclick = () => { queue.splice(+b.dataset.i, 1); renderQueue(); });
    $('#enSubmit', right).textContent = queue.length ? `▸ Enroll batch (${queue.length})` : '▸ Enroll';
  }
  $('#enAdd', body).onclick = () => {
    if (!vf.hasFile()) return toast('No image', 'Capture or choose an image first', 'err');
    queue.push(vf.getFile()); vf.reset(); renderQueue();
  };
  $('#enPick', body).onclick = () => multi.click();
  multi.onchange = () => { for (const f of multi.files) queue.push(f); multi.value = ''; renderQueue(); };

  const sel = $('#enPerson', right);
  try { sel.innerHTML = `<option value="">— select person —</option>` + await personOptions(); }
  catch (e) { sel.innerHTML = `<option value="">${esc(e.message)}</option>`; }

  $('#enCreate', right).addEventListener('click', async () => {
    const name = $('#enNew', right).value.trim();
    if (!name) return toast('Missing name', 'Enter a full name first', 'err');
    try {
      const p = await api('/persons', { method: 'POST', body: { full_name: name } });
      sel.innerHTML = `<option value="">— select person —</option>` + await personOptions();
      sel.value = p.id; $('#enNew', right).value = '';
      toast('Person created', `${name} · ${shortId(p.id)}`);
    } catch (e) { toast('Create failed', e.message, 'err'); }
  });

  $('#enSubmit', right).addEventListener('click', async () => {
    const batch = [...queue];
    if (vf.hasFile()) batch.push(vf.getFile());
    if (!batch.length) return toast('No image', 'Add at least one image', 'err');
    if (!sel.value) return toast('No person', 'Select or create a person', 'err');
    const btn = $('#enSubmit', right); btn.disabled = true;
    let ok = 0, fail = 0; const errs = [];
    for (let i = 0; i < batch.length; i++) {
      btn.innerHTML = `<span class="spin"></span> ${i + 1}/${batch.length}`;
      try {
        const fd = new FormData(); fd.append('person_id', sel.value); fd.append('image', batch[i]);
        await api('/faces/register', { method: 'POST', form: fd });
        ok++;
      } catch (e) { fail++; errs.push(e.message); }
    }
    queue.length = 0; vf.reset(); renderQueue();
    $('#enResult', right).innerHTML = `
      <div class="verdict ${fail && !ok ? 'nomatch' : 'match'}">${fail && !ok ? I.cross : I.check}
        <div>Enrolled ${ok}/${batch.length}<small>${fail ? fail + ' failed' : '512-D vectors committed'}</small></div></div>
      ${errs.length ? `<div class="readout">${errs.slice(0, 5).map((e, i) => rdRow('Error ' + (i + 1), esc(e))).join('')}</div>` : ''}`;
    toast('Enroll done', `${ok} ok · ${fail} failed`, fail && !ok ? 'err' : 'ok');
    btn.disabled = false; renderQueue();
  });
  renderQueue();
}};

// ============================================================================
// VIEW: VERIFY (1:1)
// ============================================================================
VIEWS.verify = { title: 'Verify 1:1', render: async (root) => {
  const vf = Viewfinder();
  const ref = ThumbBox('Selected identity');
  root.innerHTML = `<div class="scan-cols stagger"></div>`;
  const cols = $('.scan-cols', root);
  const left = el(`<div class="panel"><div class="brackets"><span></span><span></span><span></span><span></span></div>
    <div class="panel-head"><h3>1:1 Verification</h3><span class="kicker">PROBE vs ENROLLED</span></div>
    <div class="panel-body"><div class="dual">
      <div class="boxwrap"><span class="boxlbl">Probe image</span></div>
      <div class="boxwrap"><span class="boxlbl">Enrolled reference</span></div>
    </div></div></div>`);
  const wraps = left.querySelectorAll('.boxwrap');
  wraps[0].appendChild(vf.el); wraps[1].appendChild(ref.el);
  cols.appendChild(left);

  const right = el(`<div class="panel pad"><div class="brackets"><span></span><span></span><span></span><span></span></div>
    <div class="form-row"><label>Claimed Identity</label><select id="vPerson"><option>loading…</option></select></div>
    <button class="btn primary block" id="vSubmit">▸ Verify Identity</button>
    <div id="vResult" style="margin-top:20px"></div>
  </div>`);
  cols.appendChild(right);

  const sel = $('#vPerson', right);
  try { sel.innerHTML = `<option value="">— select person —</option>` + await personOptions(); }
  catch (e) { sel.innerHTML = `<option value="">${esc(e.message)}</option>`; }

  sel.addEventListener('change', async () => {
    if (!sel.value) return ref.placeholder('Selected identity');
    ref.placeholder('loading…');
    try {
      const faces = await api(`/faces?person_id=${sel.value}&limit=1`);
      if (faces.length && faces[0].thumbnail) ref.setImage(faces[0].thumbnail);
      else ref.placeholder('No enrolled image');
    } catch { ref.placeholder('—'); }
  });

  $('#vSubmit', right).addEventListener('click', async () => {
    if (!vf.hasFile()) return toast('No image', 'Provide a probe image', 'err');
    if (!sel.value) return toast('No person', 'Select the claimed identity', 'err');
    const btn = $('#vSubmit', right); btn.disabled = true; btn.innerHTML = '<span class="spin"></span> Matching';
    vf.scanning(true); $('#vResult', right).innerHTML = '';
    try {
      const fd = new FormData(); fd.append('person_id', sel.value); fd.append('image', vf.getFile());
      const r = await api('/faces/verify', { method: 'POST', form: fd });
      const box = el('<div></div>');
      box.appendChild(el(`<div class="verdict ${r.matched ? 'match' : 'nomatch'}">${r.matched ? I.check : I.cross}
        <div>${r.matched ? 'Identity Confirmed' : 'No Match'}<small>cosine ${r.similarity_score.toFixed(4)} vs threshold ${r.threshold}</small></div></div>`));
      box.appendChild(meter(r.similarity_score, r.threshold));
      box.appendChild(el(`<div class="readout" style="margin-top:14px">
        ${rdRow('Person ID', shortId(r.person_id))}
        ${rdRow('Matched face', r.matched_face_id ? shortId(r.matched_face_id) : '—')}
        ${rdRow('Similarity', r.similarity_score.toFixed(6))}
        ${rdRow('Threshold', String(r.threshold))}</div>`));
      $('#vResult', right).innerHTML = ''; $('#vResult', right).appendChild(box);
      toast(r.matched ? 'Match' : 'No match', pct(r.similarity_score), r.matched ? 'ok' : 'err');
    } catch (e) {
      $('#vResult', right).innerHTML = `<div class="verdict nomatch">${I.cross}<div>Error<small>${esc(e.message)}</small></div></div>`;
      toast('Verify failed', e.message, 'err');
    } finally { vf.scanning(false); btn.disabled = false; btn.innerHTML = '▸ Verify Identity'; }
  });
}};

// ============================================================================
// VIEW: SEARCH (1:N)
// ============================================================================
VIEWS.search = { title: 'Identify 1:N', render: async (root) => {
  const vf = Viewfinder();
  const scan = ThumbBox('Gallery');
  root.innerHTML = `<div class="scan-cols stagger"></div>`;
  const cols = $('.scan-cols', root);
  const left = el(`<div class="panel"><div class="brackets"><span></span><span></span><span></span><span></span></div>
    <div class="panel-head"><h3>1:N Identification</h3><span class="kicker">HNSW · COSINE</span></div>
    <div class="panel-body"><div class="dual">
      <div class="boxwrap"><span class="boxlbl">Query image</span></div>
      <div class="boxwrap"><span class="boxlbl">Gallery scan</span></div>
    </div></div></div>`);
  const wraps = left.querySelectorAll('.boxwrap');
  wraps[0].appendChild(vf.el); wraps[1].appendChild(scan.el);
  cols.appendChild(left);

  const right = el(`<div class="panel pad"><div class="brackets"><span></span><span></span><span></span><span></span></div>
    <div class="form-row"><label>Candidates (top K)</label><input id="sK" type="number" min="1" max="100" value="10"></div>
    <button class="btn primary block" id="sSubmit">▸ Search Gallery</button>
    <div id="sResult" style="margin-top:20px"></div>
  </div>`);
  cols.appendChild(right);

  // Preload gallery thumbnails for the "flip-through-the-database" animation.
  let gallery = [];
  try { gallery = await api('/faces?limit=60'); } catch { /* ignore */ }
  const thumbs = gallery.map((f) => f.thumbnail).filter(Boolean);
  scan.placeholder(thumbs.length ? `${thumbs.length} faces in gallery` : 'Gallery empty');

  $('#sSubmit', right).addEventListener('click', async () => {
    if (!vf.hasFile()) return toast('No image', 'Provide a query image', 'err');
    const btn = $('#sSubmit', right); btn.disabled = true; btn.innerHTML = '<span class="spin"></span> Searching';
    vf.scanning(true); $('#sResult', right).innerHTML = '';
    scan.startCycle(thumbs);                                   // rapid one-by-one comparison animation
    const minAnim = new Promise((res) => setTimeout(res, 1100));  // let the scan be visible
    try {
      const k = Math.max(1, Math.min(100, +$('#sK', right).value || 10));
      const fd = new FormData(); fd.append('image', vf.getFile());
      const [r] = await Promise.all([api('/faces/search?top_k=' + k, { method: 'POST', form: fd }), minAnim]);
      scan.stop();
      if (!r.matches.length) {
        scan.placeholder('No match');
        $('#sResult', right).innerHTML = `<div class="verdict nomatch">${I.cross}<div>No Candidates<small>above threshold ${r.threshold}</small></div></div>`;
      } else {
        const best = r.matches[0];
        // settle the scan box on the matched face's thumbnail
        const hit = gallery.find((f) => f.id === best.face_id) || gallery.find((f) => f.person_id === best.person_id);
        if (hit && hit.thumbnail) scan.setImage(hit.thumbnail); else scan.placeholder(best.full_name);
        const list = r.matches.map((m, i) => `
          <div class="match ${i === 0 ? 'top' : ''}">
            <div class="rank">${String(i + 1).padStart(2, '0')}</div>
            <div class="info"><b>${esc(m.full_name)}</b><span>person ${shortId(m.person_id)} · face ${shortId(m.face_id)}</span></div>
            <div class="bar"><div class="t"><div class="f" style="width:0"></div></div></div>
            <div class="pct">${pct(m.similarity_score)}</div>
          </div>`).join('');
        $('#sResult', right).innerHTML = `
          <div class="verdict match">${I.check}<div>${esc(best.full_name)}<small>best match · ${pct(best.similarity_score)} confidence</small></div></div>
          <div class="match-list" style="margin-top:6px">${list}</div>`;
        requestAnimationFrame(() => $('#sResult', right).querySelectorAll('.match-list .match').forEach((m, i) => {
          const f = m.querySelector('.f');
          if (f) f.style.width = Math.min(100, r.matches[i].similarity_score * 100) + '%';
        }));
      }
      toast('Search complete', `${r.matches.length} candidate(s)`, r.matches.length ? 'ok' : 'err');
    } catch (e) {
      scan.stop(); scan.placeholder('Error');
      $('#sResult', right).innerHTML = `<div class="verdict nomatch">${I.cross}<div>Error<small>${esc(e.message)}</small></div></div>`;
      toast('Search failed', e.message, 'err');
    } finally { vf.scanning(false); btn.disabled = false; btn.innerHTML = '▸ Search Gallery'; }
  });
}};

// ============================================================================
// VIEW: PERSONS
// ============================================================================
VIEWS.persons = { title: 'Persons', render: async (root) => {
  root.innerHTML = `
    <div class="view-grid stagger">
      ${can('operator') ? `<div class="panel pad"><div class="brackets"><span></span><span></span><span></span><span></span></div>
        <div class="inline">
          <input id="pName" placeholder="Full name">
          <input id="pExt" placeholder="External ID (optional)">
          <button class="btn primary" id="pAdd">+ Register Person</button>
        </div></div>` : ''}
      <div class="panel"><div class="brackets"><span></span><span></span><span></span><span></span></div>
        <div class="panel-head"><h3>Identity Gallery</h3><button class="btn sm ghost" id="pRefresh">↻</button></div>
        <div class="panel-body" id="pList"><div class="empty"><span class="spin"></span></div></div>
      </div>
    </div>`;
  if (can('operator')) $('#pAdd').addEventListener('click', addPerson);
  $('#pRefresh').addEventListener('click', loadPersons);
  loadPersons();

  async function addPerson() {
    const full_name = $('#pName', root).value.trim();
    if (!full_name) return toast('Missing name', 'Enter a full name', 'err');
    const external_id = $('#pExt', root).value.trim() || null;
    try {
      await api('/persons', { method: 'POST', body: { full_name, external_id } });
      $('#pName', root).value = ''; $('#pExt', root).value = '';
      toast('Registered', full_name); loadPersons();
    } catch (e) { toast('Failed', e.message, 'err'); }
  }
  const canEdit = can('operator');
  async function loadPersons() {
    try {
      const ppl = await api('/persons?limit=200');
      const list = $('#pList', root); if (!list) return;   // navigated away
      if (!ppl.length) { list.innerHTML = emptyState('No persons registered'); return; }
      list.innerHTML = `
        <table class="table"><thead><tr><th>Name</th><th>External ID</th><th>ID</th><th>Status</th><th>Created</th>${canEdit ? '<th></th>' : ''}</tr></thead>
        <tbody>${ppl.map((p) => `<tr data-id="${p.id}">
          <td style="font-family:var(--sans);font-weight:600">${esc(p.full_name)}</td>
          <td class="idcell">${esc(p.external_id || '—')}</td>
          <td class="idcell">${shortId(p.id)}</td>
          <td><span class="tag ${p.is_active ? 'ok' : 'fail'}">${p.is_active ? 'active' : 'inactive'}</span></td>
          <td class="idcell">${fmtDate(p.created_at)}</td>
          ${canEdit ? `<td class="rowact">
            <button class="iconbtn" data-edit title="Edit">${I.edit}</button>
            <button class="iconbtn danger" data-del title="Delete">${I.trash}</button></td>` : ''}
        </tr>`).join('')}</tbody></table>`;
      if (canEdit) ppl.forEach((p) => {
        const tr = $(`tr[data-id="${p.id}"]`, list);
        if (!tr) return;
        tr.querySelector('[data-edit]').onclick = () => editPerson(p);
        tr.querySelector('[data-del]').onclick = () => delPerson(p);
      });
    } catch (e) { const l = $('#pList', root); if (l) l.innerHTML = emptyState(e.message); }
  }

  async function editPerson(p) {
    const body = await modal('Edit Person', `
      <div class="form-row"><label>Full name</label><input id="mName" value="${esc(p.full_name)}"></div>
      <div class="form-row"><label>External ID</label><input id="mExt" value="${esc(p.external_id || '')}"></div>
      <div class="form-row"><label>Status</label>
        <select id="mActive"><option value="true"${p.is_active ? ' selected' : ''}>active</option>
          <option value="false"${!p.is_active ? ' selected' : ''}>inactive</option></select></div>`);
    if (!body) return;
    try {
      await api(`/persons/${p.id}`, { method: 'PATCH', body: {
        full_name: $('#mName', body).value.trim(),
        external_id: $('#mExt', body).value.trim() || null,
        is_active: $('#mActive', body).value === 'true',
      }});
      toast('Saved', p.full_name); loadPersons();
    } catch (e) { toast('Update failed', e.message, 'err'); }
  }

  async function delPerson(p) {
    if (!await confirmDanger(`Delete "${p.full_name}" and ALL their enrolled faces? This cannot be undone.`)) return;
    try { await api(`/persons/${p.id}`, { method: 'DELETE' }); toast('Deleted', p.full_name); loadPersons(); }
    catch (e) { toast('Delete failed', e.message, 'err'); }
  }
}};

// ============================================================================
// VIEW: FACE GALLERY (thumbnails + embedding fingerprints)
// ============================================================================
VIEWS.gallery = { title: 'Face Gallery', render: async (root) => {
  root.innerHTML = `
    <div class="gallery-cols stagger">
      <div class="panel">
        <div class="brackets"><span></span><span></span><span></span><span></span></div>
        <div class="panel-head"><h3>Enrolled Faces</h3><button class="btn sm ghost" id="gRefresh">↻ Refresh</button></div>
        <div class="panel-body" id="gGrid"><div class="empty"><span class="spin"></span></div></div>
      </div>
      <div class="panel pad face-detail" id="gDetail">
        <div class="brackets"><span></span><span></span><span></span><span></span></div>
        <div class="empty">${I.face}<p>Select a face to inspect its 512-D embedding</p></div>
      </div>
    </div>`;
  $('#gRefresh', root).addEventListener('click', load);
  let faces = [];
  await load();

  async function load() {
    const grid = $('#gGrid', root);
    grid.innerHTML = `<div class="empty"><span class="spin"></span></div>`;
    try {
      faces = await api('/faces?limit=60');
    } catch (e) { grid.innerHTML = emptyState(e.message); return; }
    if (!faces.length) { grid.innerHTML = emptyState('No faces enrolled yet'); return; }

    grid.innerHTML = `<div class="face-grid">` + faces.map((f) => `
      <div class="face-card" data-id="${f.id}">
        <div class="face-thumb">${f.thumbnail
          ? `<img src="${f.thumbnail}" alt="">`
          : `<span class="noimg">${I.face}</span>`}</div>
        <div class="face-meta">
          <b>${esc(f.full_name)}</b>
          <span>${pct(f.det_score)} · ${fmtDate(f.created_at)}</span>
        </div>
        <canvas class="fp" width="240" height="30"></canvas>
      </div>`).join('') + `</div>`;

    faces.forEach((f) => {
      const cardEl = grid.querySelector(`.face-card[data-id="${f.id}"]`);
      fingerprint(cardEl.querySelector('canvas.fp'), f.embedding, 64);
      cardEl.addEventListener('click', () => showDetail(f, cardEl));
    });
  }

  const canEdit = can('operator');
  const replaceInput = el('<input type="file" accept="image/*" style="display:none">');
  root.appendChild(replaceInput);
  let replaceTarget = null;
  replaceInput.onchange = async () => {
    const file = replaceInput.files[0]; replaceInput.value = '';
    if (!file || !replaceTarget) return;
    try {
      const fd = new FormData(); fd.append('image', file);
      await api(`/faces/${replaceTarget}/image`, { method: 'PUT', form: fd });
      toast('Image replaced', 're-embedded'); await load();
      const f = faces.find((x) => x.id === replaceTarget);
      if (f) showDetail(f, $(`.face-card[data-id="${f.id}"]`, root));
    } catch (e) { toast('Replace failed', e.message, 'err'); }
  };

  function showDetail(f, cardEl) {
    root.querySelectorAll('.face-card').forEach((c) => c.classList.toggle('active', c === cardEl));
    const detail = $('#gDetail', root);
    detail.innerHTML = `
      <div class="brackets"><span></span><span></span><span></span><span></span></div>
      ${f.thumbnail ? `<img class="detail-thumb" src="${f.thumbnail}" alt="">`
        : `<div class="detail-thumb noimg">${I.face}</div>`}
      <p class="kicker" style="margin-bottom:8px">EMBEDDING FINGERPRINT · 512-D</p>
      <canvas class="big-fp" width="320" height="160"></canvas>
      <div class="readout" style="margin-top:14px">
        ${rdRow('Person', esc(f.full_name))}
        ${rdRow('Face ID', shortId(f.id))}
        ${rdRow('Person ID', shortId(f.person_id))}
        ${rdRow('Detection score', pct(f.det_score))}
        ${rdRow('Vector', `${f.embedding_dim}-D · ‖v‖=${f.embedding_norm}`)}
        ${rdRow('Source', esc(f.image_path || '—'))}
        ${rdRow('Enrolled', fmtDate(f.created_at, true))}
      </div>
      ${canEdit ? `<div class="inline" style="margin-top:16px">
        <button class="btn sm" data-replace>${I.swap} Replace image</button>
        <button class="btn sm ghost danger" data-del>${I.trash} Delete</button></div>` : ''}`;
    fingerprint($('.big-fp', detail), f.embedding, 32);
    if (canEdit) {
      detail.querySelector('[data-replace]').onclick = () => { replaceTarget = f.id; replaceInput.click(); };
      detail.querySelector('[data-del]').onclick = async () => {
        if (!await confirmDanger(`Delete this face of "${f.full_name}"? The embedding is removed from search.`)) return;
        try {
          await api(`/faces/${f.id}`, { method: 'DELETE' });
          toast('Face deleted', f.full_name); await load();
          $('#gDetail', root).innerHTML = `<div class="brackets"><span></span><span></span><span></span><span></span></div><div class="empty">${I.face}<p>Select a face to inspect its 512-D embedding</p></div>`;
        } catch (e) { toast('Delete failed', e.message, 'err'); }
      };
    }
  }
}};

// ============================================================================
// VIEW: BULK IMPORT
// ============================================================================
VIEWS.import = { title: 'Bulk Import', render: (root) => {
  root.innerHTML = `
    <div class="view-grid stagger" style="max-width:820px">
      <div class="panel pad"><div class="brackets"><span></span><span></span><span></span><span></span></div>
        <p class="kicker" style="margin-bottom:12px">PICK A FOLDER ON YOUR COMPUTER</p>
        <pre class="layout-hint">chosen-folder/
  Jane Doe/    img1.jpg  img2.jpg
  John Roe/    photo.png</pre>
        <p class="kicker" style="margin:12px 0">Each sub-folder name becomes a person; every image in it is enrolled under that identity.</p>
        <div class="inline" style="margin-top:6px">
          <button class="btn" id="impPick">📁 Choose folder…</button>
          <button class="btn primary" id="impStart" disabled>▸ Import</button>
        </div>
        <div id="impSummary" class="import-summary"></div>
        <input type="file" id="impFiles" webkitdirectory directory multiple style="display:none">
      </div>
      <div class="panel pad" id="impPanel" style="display:none"><div class="brackets"><span></span><span></span><span></span><span></span></div>
        <div class="panel-head" style="padding:0 0 14px;border-bottom:1px solid var(--line)"><h3>Import Progress</h3><span class="tag amber" id="impState">pending</span></div>
        <div class="progress" style="margin:18px 0"><div class="f" id="impFill"></div><div class="t" id="impTxt">0%</div></div>
        <div class="readout">
          ${rdRow('Processed', '<span id="impProc">0 / 0</span>')}
          ${rdRow('Succeeded', '<span id="impOk" class="accent">0</span>')}
          ${rdRow('Failed', '<span id="impFail" class="danger">0</span>')}
          ${rdRow('Persons', '<span id="impPersons">0</span>')}
        </div>
        <div id="impErrors" style="margin-top:12px"></div>
      </div>
    </div>`;

  const IMG_RE = /\.(jpe?g|png|webp|bmp)$/i;
  let items = [];   // [{personName, file}]

  $('#impPick').onclick = () => $('#impFiles', root).click();
  $('#impFiles', root).onchange = (e) => {
    const files = [...e.target.files].filter((f) => IMG_RE.test(f.name));
    items = files.map((f) => {
      const parts = (f.webkitRelativePath || f.name).split('/');
      const person = parts.length >= 2 ? parts[parts.length - 2] : 'Imported';
      return { personName: person.replace(/[_]+/g, ' ').trim() || 'Imported', file: f };
    });
    const byPerson = {};
    items.forEach((it) => { byPerson[it.personName] = (byPerson[it.personName] || 0) + 1; });
    const persons = Object.keys(byPerson);
    $('#impSummary', root).innerHTML = items.length
      ? `<p class="kicker" style="margin:14px 0 8px">${items.length} image(s) · ${persons.length} person(s)</p>`
        + `<div class="import-people">${persons.slice(0, 40).map((p) => `<span class="chip">${esc(p)} · ${byPerson[p]}</span>`).join('')}${persons.length > 40 ? `<span class="chip">+${persons.length - 40} more</span>` : ''}</div>`
      : `<p class="kicker" style="margin-top:14px;color:var(--danger)">No images found in that folder</p>`;
    $('#impStart', root).disabled = !items.length;
  };

  $('#impStart', root).onclick = async () => {
    if (!items.length) return;
    const btn = $('#impStart', root); btn.disabled = true;
    $('#impPick', root).disabled = true;
    $('#impPanel', root).style.display = 'block';
    const total = items.length; let processed = 0, ok = 0, fail = 0; const errs = [];
    const persons = new Set();
    for (const it of items) {
      try {
        const fd = new FormData();
        fd.append('person_name', it.personName);
        fd.append('image', it.file, it.file.name);
        await api('/faces/enroll', { method: 'POST', form: fd });
        ok++; persons.add(it.personName);
      } catch (e) { fail++; if (errs.length < 50) errs.push(`${it.personName}/${it.file.name}: ${e.message}`); }
      processed++;
      const p = Math.round((processed / total) * 100);
      $('#impFill', root).style.width = p + '%'; $('#impTxt', root).textContent = p + '%';
      $('#impProc', root).textContent = `${processed} / ${total}`;
      $('#impOk', root).textContent = ok; $('#impFail', root).textContent = fail;
      $('#impPersons', root).textContent = persons.size;
      const st = $('#impState', root); st.textContent = 'running'; st.className = 'tag reg';
      if (errs.length) $('#impErrors', root).innerHTML = `<p class="kicker" style="margin-bottom:6px;color:var(--danger)">ERRORS (${fail})</p>`
        + errs.slice(0, 8).map((x) => `<div style="font-family:var(--mono);font-size:11px;color:var(--muted);padding:2px 0">› ${esc(x)}</div>`).join('');
    }
    const st = $('#impState', root); st.textContent = fail && !ok ? 'failed' : 'completed';
    st.className = 'tag ' + (fail && !ok ? 'fail' : 'ok');
    toast('Import ' + st.textContent, `${ok} ok · ${fail} failed`, fail && !ok ? 'err' : 'ok');
    $('#impPick', root).disabled = false;
  };
}};

// ============================================================================
// VIEW: LOGS
// ============================================================================
VIEWS.logs = { title: 'Audit Log', render: async (root) => {
  root.innerHTML = `
    <div class="panel stagger"><div class="brackets"><span></span><span></span><span></span><span></span></div>
      <div class="panel-head"><h3>Recognition Audit Trail</h3>
        <div class="inline" style="gap:8px"><select id="lgLimit" style="width:110px">
          <option value="50">last 50</option><option value="100">last 100</option><option value="200">last 200</option></select>
          <button class="btn sm ghost" id="lgRefresh">↻ Refresh</button></div></div>
      <div class="panel-body" id="lgBody"><div class="empty"><span class="spin"></span></div></div>
    </div>`;
  $('#lgRefresh', root).addEventListener('click', loadLogs);
  $('#lgLimit', root).addEventListener('change', loadLogs);
  loadLogs();
  async function loadLogs() {
    try {
      const sel = $('#lgLimit', root);
      const logs = await api('/logs?limit=' + ((sel && sel.value) || 50));
      const body = $('#lgBody', root); if (!body) return;
      body.innerHTML = logs.length ? logsTable(logs) : emptyState('No events recorded');
    } catch (e) { const b = $('#lgBody', root); if (b) b.innerHTML = emptyState(e.message); }
  }
}};

// ============================================================================
// VIEW: API KEYS (admin) — 3rd-party 1:N access
// ============================================================================
VIEWS.apikeys = { title: 'API Keys', render: async (root) => {
  root.innerHTML = `
    <div class="view-grid stagger" style="max-width:900px">
      <div class="panel pad"><div class="brackets"><span></span><span></span><span></span><span></span></div>
        <p class="kicker" style="margin-bottom:10px">3RD-PARTY 1:N IDENTIFICATION</p>
        <div class="inline">
          <input id="akName" placeholder="Key name (e.g. partner-acme)">
          <button class="btn primary" id="akAdd">+ Generate Key</button>
        </div>
        <p class="kicker" style="margin-top:10px">POST multipart <span class="mono accent">/api/v1/external/search</span> with header <span class="mono accent">X-API-Key</span> → returns the top-1 match (or none). Rate-limited per key.</p>
      </div>
      <div class="panel"><div class="brackets"><span></span><span></span><span></span><span></span></div>
        <div class="panel-head"><h3>Keys</h3><button class="btn sm ghost" id="akRefresh">↻</button></div>
        <div class="panel-body" id="akList"><div class="empty"><span class="spin"></span></div></div>
      </div>
    </div>`;
  $('#akAdd', root).onclick = addKey;
  $('#akRefresh', root).onclick = load;
  await load();

  async function load() {
    try {
      const keys = await api('/api-keys');
      if (!keys.length) { $('#akList', root).innerHTML = emptyState('No API keys yet'); return; }
      $('#akList', root).innerHTML = `
        <table class="table"><thead><tr><th>Name</th><th>Prefix</th><th>Status</th><th>Last used</th><th>Created</th><th></th></tr></thead>
        <tbody>${keys.map((k) => `<tr data-id="${k.id}">
          <td style="font-family:var(--sans);font-weight:600">${esc(k.name)}</td>
          <td class="idcell">${esc(k.prefix)}…</td>
          <td><span class="tag ${k.is_active ? 'ok' : 'fail'}">${k.is_active ? 'active' : 'revoked'}</span></td>
          <td class="idcell">${k.last_used_at ? fmtDate(k.last_used_at, true) : 'never'}</td>
          <td class="idcell">${fmtDate(k.created_at)}</td>
          <td class="rowact"><button class="iconbtn danger" data-del title="Revoke">${I.trash}</button></td>
        </tr>`).join('')}</tbody></table>`;
      keys.forEach((k) => {
        $(`tr[data-id="${k.id}"] [data-del]`, $('#akList', root)).onclick = async () => {
          if (!await confirmDanger(`Revoke API key "${k.name}"? Callers using it will be denied immediately.`)) return;
          try { await api(`/api-keys/${k.id}`, { method: 'DELETE' }); toast('Revoked', k.name); load(); }
          catch (e) { toast('Revoke failed', e.message, 'err'); }
        };
      });
    } catch (e) { $('#akList', root).innerHTML = emptyState(e.message); }
  }

  async function addKey() {
    const name = $('#akName', root).value.trim();
    if (!name) return toast('Missing name', 'Name the key first', 'err');
    try {
      const k = await api('/api-keys', { method: 'POST', body: { name } });
      $('#akName', root).value = '';
      await modal('API Key Created', `
        <p class="kicker" style="margin-bottom:8px;color:var(--accent)">COPY NOW — SHOWN ONLY ONCE</p>
        <div class="keybox"><code id="rawkey">${esc(k.key)}</code><button class="btn sm" id="copyKey">Copy</button></div>
        <p class="kicker" style="margin-top:10px">Use as header: <span class="mono">X-API-Key: ${esc(k.prefix)}…</span></p>`,
        { okText: 'Done', onMount: (body) => {
          body.querySelector('#copyKey').onclick = () => {
            navigator.clipboard?.writeText(k.key).then(() => toast('Copied', 'API key in clipboard')).catch(() => {});
          };
        }});
      toast('Key created', k.name); load();
    } catch (e) { toast('Create failed', e.message, 'err'); }
  }
}};

// ---------- shared renderers ----------
const ACTION_TAG = { register: 'reg', verify: 'ok', search: 'ok', import: 'amber' };
function logsTable(logs) {
  return `<table class="table"><thead><tr><th>Time</th><th>Action</th><th>Result</th><th>Similarity</th><th>Person</th><th>Operator</th></tr></thead>
    <tbody>${logs.map((l) => `<tr>
      <td class="idcell">${fmtDate(l.created_at, true)}</td>
      <td><span class="tag ${ACTION_TAG[l.action] || 'reg'}">${esc(l.action)}</span></td>
      <td><span class="tag ${l.success ? 'ok' : 'fail'}">${l.success ? 'success' : 'fail'}</span></td>
      <td>${l.similarity != null ? pct(l.similarity) : '—'}</td>
      <td class="idcell">${shortId(l.person_id)}</td>
      <td class="idcell">${esc(l.user_id || '—')}</td></tr>`).join('')}</tbody></table>`;
}
function rdRow(lbl, val) { return `<div class="row"><span class="lbl">${esc(lbl)}</span><span class="val">${val}</span></div>`; }
function emptyState(msg) { return `<div class="empty">${I.inbox}<p>${esc(msg)}</p></div>`; }
function fmtDate(s, withTime) {
  if (!s) return '—';
  const d = new Date(s);
  if (isNaN(d.getTime())) return esc(String(s).slice(0, 19));  // never break a table on a bad date
  const date = d.toISOString().slice(0, 10);
  return withTime ? date + ' ' + d.toTimeString().slice(0, 8) : date;
}

// ---------- clock ----------
function tick() {
  const d = new Date();
  const c = $('#clock'), dt = $('#date');
  if (c) c.textContent = d.toTimeString().slice(0, 8);
  if (dt) dt.textContent = d.toISOString().slice(0, 10) + ' UTC' + (-d.getTimezoneOffset() / 60 >= 0 ? '+' : '') + (-d.getTimezoneOffset() / 60);
}
setInterval(tick, 1000); tick();

// ---------- boot ----------
$('#loginApi').value = S.api;
if (S.token) enterApp(); else $('#loginUser').focus();
