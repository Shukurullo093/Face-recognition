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
    { id: 'import',  label: 'Bulk Import', icon: 'import', role: 'admin' },
    { id: 'logs',    label: 'Audit Log',   icon: 'log',    role: 'viewer' },
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
  go(can('operator') ? 'overview' : 'overview');
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

function go(id) {
  if (!VIEWS[id]) id = 'overview';
  releaseCameras();
  S.view = id;
  document.querySelectorAll('.nav-item').forEach((n) => n.classList.toggle('active', n.dataset.view === id));
  const v = VIEWS[id];
  $('#viewTitle').textContent = v.title;
  $('#crumb').textContent = 'CONSOLE / ' + v.title.toUpperCase();
  const root = $('#view'); root.innerHTML = '';
  v.render(root);
}

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

  return { el: wrap, getFile: () => file, scanning, reticle, hasFile: () => !!file };
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
  $('#ovRefresh').addEventListener('click', loadOverview);
  loadOverview();

  async function loadOverview() {
    try {
      const s = await api('/stats');
      $('#ovStats').innerHTML = [
        ['Registered Persons', s.total_persons, 'identities in gallery', ''],
        ['Enrolled Faces', s.total_faces, 'embedding vectors', 'lime'],
        ['Recognition Events', s.total_events, 'lifetime queries', ''],
        ['Match Rate', pct(s.match_rate), `${s.successful_events} successful`, 'lime'],
      ].map(([k, v, sub, cls]) => `
        <div class="stat"><div class="k">${k}</div><div class="v ${cls}">${v}</div><div class="sub">${sub}</div></div>`).join('');

      const logs = await api('/logs?limit=12');
      $('#ovFeed').innerHTML = logs.length ? logsTable(logs) : emptyState('No recognition events yet');
    } catch (e) { toast('Load failed', e.message, 'err'); $('#ovFeed').innerHTML = emptyState(e.message); }
  }
}};

// ============================================================================
// VIEW: ENROLL
// ============================================================================
VIEWS.enroll = { title: 'Enroll', render: async (root) => {
  const vf = Viewfinder();
  root.innerHTML = `<div class="scan-cols stagger"></div>`;
  const cols = $('.scan-cols', root);

  const left = el(`<div class="panel"><div class="brackets"><span></span><span></span><span></span><span></span></div>
    <div class="panel-head"><h3>Capture Subject</h3><span class="kicker">SCRFD · ALIGN · ARCFACE</span></div>
    <div class="panel-body"></div></div>`);
  $('.panel-body', left).appendChild(vf.el);
  cols.appendChild(left);

  const right = el(`<div class="panel pad">
    <div class="brackets"><span></span><span></span><span></span><span></span></div>
    <div class="form-row"><label>Assign to Person</label>
      <div class="inline"><select id="enPerson"><option>loading…</option></select></div></div>
    <div class="form-row"><label>Or register a new identity</label>
      <div class="inline"><input id="enNew" placeholder="Full name (e.g. Jane Doe)"><button class="btn sm" id="enCreate">+ Add</button></div></div>
    <button class="btn primary block" id="enSubmit" style="margin-top:6px">▸ Generate Embedding & Enroll</button>
    <div id="enResult" style="margin-top:20px"></div>
  </div>`);
  cols.appendChild(right);

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
    if (!vf.hasFile()) return toast('No image', 'Provide a face image first', 'err');
    if (!sel.value) return toast('No person', 'Select or create a person', 'err');
    const btn = $('#enSubmit', right); btn.disabled = true; btn.innerHTML = '<span class="spin"></span> Processing';
    vf.scanning(true); $('#enResult', right).innerHTML = '';
    try {
      const fd = new FormData();
      fd.append('person_id', sel.value); fd.append('image', vf.getFile());
      const r = await api('/faces/register', { method: 'POST', form: fd });
      vf.reticle(r.bbox, 'ENROLLED ' + pct(r.confidence), true);
      $('#enResult', right).innerHTML = `
        <div class="verdict match">${I.check}<div>Enrolled<small>512-D vector committed to gallery</small></div></div>
        <div class="readout">
          ${rdRow('Face ID', shortId(r.face_id))}
          ${rdRow('Person ID', shortId(r.person_id))}
          ${rdRow('Detection score', pct(r.confidence))}
          ${rdRow('Embedding', '512-D · L2-normalised')}
        </div>`;
      toast('Enrolled', 'Face committed · ' + pct(r.confidence));
    } catch (e) {
      vf.scanning(false);
      $('#enResult', right).innerHTML = `<div class="verdict nomatch">${I.cross}<div>Failed<small>${esc(e.message)}</small></div></div>`;
      toast('Enrollment failed', e.message, 'err');
    } finally { vf.scanning(false); btn.disabled = false; btn.innerHTML = '▸ Generate Embedding & Enroll'; }
  });
}};

// ============================================================================
// VIEW: VERIFY (1:1)
// ============================================================================
VIEWS.verify = { title: 'Verify 1:1', render: async (root) => {
  const vf = Viewfinder();
  root.innerHTML = `<div class="scan-cols stagger"></div>`;
  const cols = $('.scan-cols', root);
  const left = el(`<div class="panel"><div class="brackets"><span></span><span></span><span></span><span></span></div>
    <div class="panel-head"><h3>Probe Image</h3><span class="kicker">1:1 VERIFICATION</span></div>
    <div class="panel-body"></div></div>`);
  $('.panel-body', left).appendChild(vf.el); cols.appendChild(left);

  const right = el(`<div class="panel pad"><div class="brackets"><span></span><span></span><span></span><span></span></div>
    <div class="form-row"><label>Claimed Identity</label><select id="vPerson"><option>loading…</option></select></div>
    <button class="btn primary block" id="vSubmit">▸ Verify Identity</button>
    <div id="vResult" style="margin-top:20px"></div>
  </div>`);
  cols.appendChild(right);

  const sel = $('#vPerson', right);
  try { sel.innerHTML = `<option value="">— select person —</option>` + await personOptions(); }
  catch (e) { sel.innerHTML = `<option value="">${esc(e.message)}</option>`; }

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
VIEWS.search = { title: 'Identify 1:N', render: (root) => {
  const vf = Viewfinder();
  root.innerHTML = `<div class="scan-cols stagger"></div>`;
  const cols = $('.scan-cols', root);
  const left = el(`<div class="panel"><div class="brackets"><span></span><span></span><span></span><span></span></div>
    <div class="panel-head"><h3>Unknown Subject</h3><span class="kicker">1:N · HNSW COSINE</span></div>
    <div class="panel-body"></div></div>`);
  $('.panel-body', left).appendChild(vf.el); cols.appendChild(left);

  const right = el(`<div class="panel pad"><div class="brackets"><span></span><span></span><span></span><span></span></div>
    <div class="form-row"><label>Candidates (top K)</label><input id="sK" type="number" min="1" max="100" value="10"></div>
    <button class="btn primary block" id="sSubmit">▸ Search Gallery</button>
    <div id="sResult" style="margin-top:20px"></div>
  </div>`);
  cols.appendChild(right);

  $('#sSubmit', right).addEventListener('click', async () => {
    if (!vf.hasFile()) return toast('No image', 'Provide a query image', 'err');
    const btn = $('#sSubmit', right); btn.disabled = true; btn.innerHTML = '<span class="spin"></span> Searching';
    vf.scanning(true); $('#sResult', right).innerHTML = '';
    try {
      const k = Math.max(1, Math.min(100, +$('#sK', right).value || 10));
      const fd = new FormData(); fd.append('image', vf.getFile());
      const r = await api('/faces/search?top_k=' + k, { method: 'POST', form: fd });
      if (!r.matches.length) {
        $('#sResult', right).innerHTML = `<div class="verdict nomatch">${I.cross}<div>No Candidates<small>above threshold ${r.threshold}</small></div></div>`;
      } else {
        const best = r.matches[0];
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
        // Scope to .match-list so the "verdict match" header (which also carries
        // the .match class for styling) is excluded and indices stay aligned.
        requestAnimationFrame(() => $('#sResult', right).querySelectorAll('.match-list .match').forEach((m, i) => {
          const f = m.querySelector('.f');
          if (f) f.style.width = Math.min(100, r.matches[i].similarity_score * 100) + '%';
        }));
      }
      toast('Search complete', `${r.matches.length} candidate(s)`, r.matches.length ? 'ok' : 'err');
    } catch (e) {
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
    const full_name = $('#pName').value.trim();
    if (!full_name) return toast('Missing name', 'Enter a full name', 'err');
    const external_id = $('#pExt').value.trim() || null;
    try {
      await api('/persons', { method: 'POST', body: { full_name, external_id } });
      $('#pName').value = ''; $('#pExt').value = '';
      toast('Registered', full_name); loadPersons();
    } catch (e) { toast('Failed', e.message, 'err'); }
  }
  async function loadPersons() {
    try {
      const ppl = await api('/persons?limit=200');
      $('#pList').innerHTML = ppl.length ? `
        <table class="table"><thead><tr><th>Name</th><th>External ID</th><th>ID</th><th>Status</th><th>Created</th></tr></thead>
        <tbody>${ppl.map((p) => `<tr>
          <td style="font-family:var(--sans);font-weight:600">${esc(p.full_name)}</td>
          <td class="idcell">${esc(p.external_id || '—')}</td>
          <td class="idcell">${shortId(p.id)}</td>
          <td><span class="tag ${p.is_active ? 'ok' : 'fail'}">${p.is_active ? 'active' : 'inactive'}</span></td>
          <td class="idcell">${fmtDate(p.created_at)}</td></tr>`).join('')}</tbody></table>`
        : emptyState('No persons registered');
    } catch (e) { $('#pList').innerHTML = emptyState(e.message); }
  }
}};

// ============================================================================
// VIEW: BULK IMPORT
// ============================================================================
VIEWS.import = { title: 'Bulk Import', render: (root) => {
  root.innerHTML = `
    <div class="view-grid stagger" style="max-width:760px">
      <div class="panel pad"><div class="brackets"><span></span><span></span><span></span><span></span></div>
        <p class="kicker" style="margin-bottom:14px">FOLDER LAYOUT</p>
        <pre style="font-family:var(--mono);font-size:12px;color:var(--muted);background:var(--bg-2);border:1px solid var(--line);border-radius:var(--r);padding:14px;line-height:1.7">&lt;root&gt;/
  Jane_Doe/   img1.jpg  img2.jpg
  John_Roe/   photo.png</pre>
        <div class="form-row" style="margin-top:16px"><label>Server-side root path</label>
          <input id="impPath" placeholder="/data/gallery"></div>
        <button class="btn primary block" id="impStart">▸ Launch Import Job</button>
      </div>
      <div class="panel pad" id="impPanel" style="display:none"><div class="brackets"><span></span><span></span><span></span><span></span></div>
        <div class="panel-head" style="padding:0 0 14px;border-bottom:1px solid var(--line)"><h3>Job Telemetry</h3><span class="tag amber" id="impState">pending</span></div>
        <div class="progress" style="margin:18px 0"><div class="f" id="impFill"></div><div class="t" id="impTxt">0%</div></div>
        <div class="readout">
          ${rdRow('Job ID', '<span id="impId">—</span>')}
          ${rdRow('Processed', '<span id="impProc">0 / 0</span>')}
          ${rdRow('Succeeded', '<span id="impOk" class="accent">0</span>')}
          ${rdRow('Failed', '<span id="impFail" class="danger">0</span>')}
        </div>
        <div id="impErrors" style="margin-top:12px"></div>
      </div>
    </div>`;

  let poll = null;
  $('#impStart').addEventListener('click', async () => {
    const root_path = $('#impPath').value.trim();
    if (!root_path) return toast('Missing path', 'Enter the server-side root path', 'err');
    try {
      const job = await api('/faces/import', { method: 'POST', body: { root_path } });
      $('#impPanel').style.display = 'block';
      $('#impId').textContent = shortId(job.job_id);
      toast('Import started', 'Polling job ' + shortId(job.job_id));
      clearInterval(poll);
      poll = setInterval(() => pollJob(job.job_id), 1000);
      pollJob(job.job_id);
    } catch (e) { toast('Launch failed', e.message, 'err'); }
  });

  async function pollJob(id) {
    try {
      const j = await api('/faces/import/' + id);
      const p = j.total ? Math.round((j.processed / j.total) * 100) : (j.state === 'completed' ? 100 : 0);
      $('#impFill').style.width = p + '%'; $('#impTxt').textContent = p + '%';
      $('#impProc').textContent = `${j.processed} / ${j.total}`;
      $('#impOk').textContent = j.succeeded; $('#impFail').textContent = j.failed;
      const st = $('#impState'); st.textContent = j.state;
      st.className = 'tag ' + ({ completed: 'ok', failed: 'fail', running: 'reg', pending: 'amber' }[j.state] || 'amber');
      if (j.errors?.length) $('#impErrors').innerHTML = `<p class="kicker" style="margin-bottom:6px;color:var(--danger)">ERRORS (${j.errors.length})</p>` +
        j.errors.slice(0, 8).map((e) => `<div style="font-family:var(--mono);font-size:11px;color:var(--muted);padding:2px 0">› ${esc(e)}</div>`).join('');
      if (j.state === 'completed' || j.state === 'failed') {
        clearInterval(poll);
        toast('Import ' + j.state, `${j.succeeded} ok · ${j.failed} failed`, j.state === 'completed' ? 'ok' : 'err');
      }
    } catch (e) { clearInterval(poll); toast('Poll failed', e.message, 'err'); }
  }
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
  $('#lgRefresh').addEventListener('click', loadLogs);
  $('#lgLimit').addEventListener('change', loadLogs);
  loadLogs();
  async function loadLogs() {
    try {
      const logs = await api('/logs?limit=' + ($('#lgLimit').value || 50));
      $('#lgBody').innerHTML = logs.length ? logsTable(logs) : emptyState('No events recorded');
    } catch (e) { $('#lgBody').innerHTML = emptyState(e.message); }
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
