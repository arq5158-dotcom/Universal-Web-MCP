/* Ashzo MCP · Studio
   Everything on this page updates by itself through two live streams:
     /api/live/stream  job progress, Flow chat, sign-in steps, accounts, vault, credits, agent activity
     /api/live/screen  frames mirrored from the Ashzo Browser (Live View)
   No page refresh is ever needed. */

'use strict';

// ─────────────────────────────────────────────────────────────── utilities
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
const ESC = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ESC[c]);
const ACTIVE = new Set(['queued', 'initializing', 'connecting', 'submitting', 'waiting', 'rendering', 'downloading']);

async function api(method, url, body) {
  const opts = { method, headers: {} };
  if (body !== undefined) {
    opts.headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(url, opts);
  let data = null;
  try { data = await res.json(); } catch { data = null; }
  if (!res.ok) {
    const msg = (data && (data.detail || data.message)) || `${res.status} ${res.statusText}`;
    throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
  }
  return data;
}

function fmtElapsed(ms) {
  if (!ms || ms < 0) return '';
  const s = Math.floor(ms / 1000);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
}
function timeAgo(ts) {
  if (!ts) return '';
  const s = Math.max(0, Math.floor((Date.now() - ts) / 1000));
  if (s < 45) return 'just now';
  if (s < 3600) return `${Math.round(s / 60)} min ago`;
  if (s < 86400) return `${Math.round(s / 3600)} h ago`;
  return new Date(ts).toLocaleDateString();
}
const spinner = (cls = '') => `<span class="spin-ring ${cls}" aria-hidden="true"></span>`;

function toast(text, type = 'info') {
  const box = $('#toastContainer');
  const el = document.createElement('div');
  el.className = 'toast';
  el.setAttribute('role', type === 'error' ? 'alert' : 'status');
  const icon = type === 'success' ? '<i class="fa-solid fa-circle-check text-emerald-400"></i>'
    : type === 'error' ? '<i class="fa-solid fa-circle-exclamation text-rose-400"></i>'
    : '<i class="fa-solid fa-circle-info text-indigo-400"></i>';
  el.innerHTML = `${icon}<span>${esc(text)}</span>`;
  box.appendChild(el);
  requestAnimationFrame(() => el.classList.add('is-in'));
  setTimeout(() => { el.classList.remove('is-in'); setTimeout(() => el.remove(), 320); }, type === 'error' ? 7000 : 4500);
}

// ─────────────────────────────────────────────────────────────── theme
// Light / dark / system with a circular reveal from the pressed button (View Transitions),
// the same effect as the Ashzo app; a short colour cross-fade where that API is missing.
const THEME_KEY = 'ashzo_theme';
const mq = window.matchMedia('(prefers-color-scheme: dark)');
function themePref() {
  try { const v = localStorage.getItem(THEME_KEY); return v === 'light' || v === 'dark' ? v : 'system'; } catch { return 'system'; }
}
const resolveTheme = (pref) => (pref === 'system' ? (mq.matches ? 'dark' : 'light') : pref);
function applyTheme(theme) {
  const root = document.documentElement;
  root.setAttribute('data-theme', theme);
  root.classList.toggle('dark', theme === 'dark');
  $$('meta[name="theme-color"]').forEach((m) => m.setAttribute('content', theme === 'dark' ? '#070709' : '#f8f9fc'));
}
function paintThemeToggle() {
  const pref = themePref();
  $$('[data-theme-opt]').forEach((b) => b.setAttribute('aria-checked', String(b.dataset.themeOpt === pref)));
}
function setTheme(pref, origin) {
  try { if (pref === 'system') localStorage.removeItem(THEME_KEY); else localStorage.setItem(THEME_KEY, pref); } catch { /* private mode */ }
  paintThemeToggle();
  const next = resolveTheme(pref);
  if (next === document.documentElement.getAttribute('data-theme')) return;
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (document.startViewTransition && !reduced) {
    const x = origin ? origin.x : window.innerWidth / 2;
    const y = origin ? origin.y : 0;
    const r = Math.hypot(Math.max(x, window.innerWidth - x), Math.max(y, window.innerHeight - y));
    const t = document.startViewTransition(() => applyTheme(next));
    t.ready.then(() => {
      document.documentElement.animate(
        { clipPath: [`circle(0px at ${x}px ${y}px)`, `circle(${r}px at ${x}px ${y}px)`] },
        { duration: 700, easing: 'cubic-bezier(.65,0,.35,1)', pseudoElement: '::view-transition-new(root)' });
    }).catch(() => {});
    return;
  }
  const root = document.documentElement;
  if (!reduced) root.classList.add('theme-fade');
  applyTheme(next);
  setTimeout(() => root.classList.remove('theme-fade'), 450);
}
function initTheme() {
  applyTheme(resolveTheme(themePref()));
  paintThemeToggle();
  $$('[data-theme-opt]').forEach((b) => b.addEventListener('click', (e) => {
    const r = e.currentTarget.getBoundingClientRect();
    setTheme(b.dataset.themeOpt, { x: r.left + r.width / 2, y: r.top + r.height / 2 });
  }));
  mq.addEventListener('change', () => { if (themePref() === 'system') applyTheme(resolveTheme('system')); });
}

// ─────────────────────────────────────────────────────────────── dropdowns & popovers (overlays)
const dropdownHandlers = {};
function dropdownValue(id) { return $('#' + id).dataset.value; }
function setDropdown(id, value, silent = false) {
  const dd = $('#' + id);
  const item = $$('.dropdown-item', dd).find((i) => i.dataset.value === String(value));
  if (!item) return;
  dd.dataset.value = item.dataset.value;
  $$('.dropdown-item', dd).forEach((i) => { i.classList.toggle('is-selected', i === item); i.setAttribute('aria-selected', String(i === item)); });
  const icon = item.dataset.icon ? `<i class="${esc(item.dataset.icon)} mr-1.5"></i>` : '';
  $('[data-display]', dd).innerHTML = icon + esc(item.dataset.label || item.textContent.trim());
  if (!silent && dropdownHandlers[id]) dropdownHandlers[id](item.dataset.value);
}
function closeAllOverlays(except) {
  $$('.custom-dropdown.is-open, .popover-anchor.is-open').forEach((d) => { if (d !== except) d.classList.remove('is-open'); });
}
function openDropdown(dd) {
  closeAllOverlays(dd);
  // Open upward when there isn't room below; the menu is absolutely positioned so the page never moves.
  const r = dd.getBoundingClientRect();
  const menu = $('.dropdown-menu', dd);
  const need = Math.min(menu.scrollHeight || 220, 260) + 12;
  dd.classList.toggle('drop-up', window.innerHeight - r.bottom < need && r.top > need);
  dd.classList.add('is-open');
}
function initDropdowns() {
  $$('.custom-dropdown').forEach((dd) => {
    $('.dropdown-trigger', dd).addEventListener('click', (e) => {
      e.stopPropagation();
      if (dd.classList.contains('is-open')) dd.classList.remove('is-open'); else openDropdown(dd);
    });
    $$('.dropdown-item', dd).forEach((item) => item.addEventListener('click', (e) => {
      e.stopPropagation();
      setDropdown(dd.id, item.dataset.value);
      dd.classList.remove('is-open');
      $('.dropdown-trigger', dd).focus();
    }));
  });
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.custom-dropdown') && !e.target.closest('.popover-anchor')) closeAllOverlays();
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      const open = $('.custom-dropdown.is-open, .popover-anchor.is-open');
      if (open) { open.classList.remove('is-open'); return; }
      const modal = $$('.modal-overlay.is-open').pop();
      if (modal) { modal.id === 'loginModal' ? closeLoginModal() : closeModal(modal.id); }
    }
  });
}
// (not named togglePopover: inline onclick would call the built-in HTMLElement.togglePopover instead)
function toggleFeedPanel(id, e) {
  if (e) e.stopPropagation();
  const anchor = $('#' + id).closest('.popover-anchor');
  const open = !anchor.classList.contains('is-open');
  closeAllOverlays(anchor);
  anchor.classList.toggle('is-open', open);
  if (open && id === 'feedPopover') {
    unread = 0; paintFeedCount();
    const logs = $('#terminalLogs'); logs.scrollTop = logs.scrollHeight;
  }
}

// ─────────────────────────────────────────────────────────────── modals
function openModal(id) { $('#' + id).classList.add('is-open'); }
function closeModal(id) { $('#' + id).classList.remove('is-open'); }
function backdropClose(e, id) {
  if (e.target === e.currentTarget) { id === 'loginModal' ? closeLoginModal() : closeModal(id); }
}
let confirmResolver = null;
function confirmDialog(title, text, okLabel = 'Remove') {
  $('#confirmTitle').textContent = title;
  $('#confirmText').textContent = text;
  $('#confirmOk').textContent = okLabel;
  openModal('confirmModal');
  return new Promise((res) => { confirmResolver = res; });
}
function resolveConfirm(v) { closeModal('confirmModal'); if (confirmResolver) confirmResolver(v); confirmResolver = null; }

// ─────────────────────────────────────────────────────────────── tabs
function switchTab(tab) {
  $$('.tab-content').forEach((el) => { el.classList.add('hidden'); el.classList.remove('tab-animating'); });
  $$('.tab-btn').forEach((b) => b.classList.toggle('is-active', b.id === 'tab-btn-' + tab));
  const el = $('#tab-' + tab);
  if (el) { el.classList.remove('hidden'); void el.offsetWidth; el.classList.add('tab-animating'); }
  if (tab === 'sessions') { loadSessions(); loadBrowserStatus(); }
  if (tab === 'flow') { loadDownloads(); }
  try { history.replaceState(null, '', '#' + tab); } catch {}
}

// ─────────────────────────────────────────────────────────────── generator form
const DURATIONS = {
  omni_flash: ['4', '6', '8', '10', '30s_ad'],
  gemini_omni: ['4', '6', '8', '10'],
  veo_3_1: ['4', '6', '8', '30s_ad'],
};
let selectedDuration = '8';
function renderDurations() {
  const model = dropdownValue('dropdown-model');
  const list = DURATIONS[model] || DURATIONS.omni_flash;
  if (!list.includes(selectedDuration)) selectedDuration = '8';
  $('#durationPills').innerHTML = list.map((d) =>
    `<button type="button" class="dur-btn ${d === selectedDuration ? 'is-selected' : ''}" data-dur="${d}">${d === '30s_ad' ? '30s · 4 scenes' : d + 's'}</button>`).join('');
  $$('#durationPills .dur-btn').forEach((b) => b.addEventListener('click', () => { selectedDuration = b.dataset.dur; renderDurations(); }));
}
function appendTag(t) {
  const a = $('#promptInput');
  a.value = a.value.trim() ? a.value.trim().replace(/[,.]?$/, '') + ', ' + t : t;
  a.focus();
}

// Reference frames (image files are uploaded to the app and attached in Flow)
const refs = { first: null, last: null };
let pickingRole = null;
function pickReference(role) { pickingRole = role; $('#refFileInput').value = ''; $('#refFileInput').click(); }
async function uploadReference(role, file) {
  if (!file || !file.type.startsWith('image/')) return toast('Choose an image file.', 'error');
  if (file.size > 15 * 1024 * 1024) return toast('That image is over 15 MB.', 'error');
  const slot = $('#ref-' + role);
  const img = $('img', slot);
  img.src = URL.createObjectURL(file);
  img.classList.remove('hidden');
  $('.ref-empty', slot).classList.add('hidden');
  $('.ref-clear', slot).classList.remove('hidden');
  try {
    const data = await new Promise((res, rej) => {
      const r = new FileReader();
      r.onload = () => res(String(r.result).split(',')[1]);
      r.onerror = rej;
      r.readAsDataURL(file);
    });
    const out = await api('POST', '/api/flow/reference', { filename: file.name, data_b64: data });
    refs[role] = out;
  } catch (e) {
    clearReference(role);
    toast('Upload failed: ' + e.message, 'error');
  }
}
function clearReference(role) {
  refs[role] = null;
  const slot = $('#ref-' + role);
  $('img', slot).classList.add('hidden');
  $('img', slot).removeAttribute('src');
  $('.ref-empty', slot).classList.remove('hidden');
  $('.ref-clear', slot).classList.add('hidden');
}
function initReferences() {
  $('#refFileInput').addEventListener('change', (e) => { if (pickingRole && e.target.files[0]) uploadReference(pickingRole, e.target.files[0]); });
  $$('.ref-slot').forEach((slot) => {
    const role = slot.dataset.role;
    slot.addEventListener('dragover', (e) => { e.preventDefault(); slot.classList.add('is-drag'); });
    slot.addEventListener('dragleave', () => slot.classList.remove('is-drag'));
    slot.addEventListener('drop', (e) => {
      e.preventDefault(); slot.classList.remove('is-drag');
      if (e.dataTransfer.files[0]) uploadReference(role, e.dataTransfer.files[0]);
    });
  });
}

async function submitGeneration() {
  const prompt = $('#promptInput').value.trim();
  if (!prompt) { toast('Write a prompt first.', 'error'); $('#promptInput').focus(); return; }
  const btn = $('#genBtn');
  btn.disabled = true;
  btn.innerHTML = `${spinner()}<span>Starting…</span>`;
  try {
    const data = await api('POST', '/api/flow/generate', {
      prompt,
      model: dropdownValue('dropdown-model'),
      duration: selectedDuration,
      download_quality: dropdownValue('dropdown-quality'),
      aspect_ratio: dropdownValue('dropdown-aspect'),
      starting_frame: $('#startFrame').value.trim() || null,
      ending_frame: $('#endFrame').value.trim() || null,
      starting_frame_path: refs.first ? refs.first.path : null,
      ending_frame_path: refs.last ? refs.last.path : null,
      slug: $('#slugInput').value.trim() || 'video',
    });
    if (data.status === 'busy') toast(data.message, 'error');
    else toast('Started. Watch it live on the right.', 'success');
  } catch (e) {
    toast('Could not start: ' + e.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="fa-solid fa-play text-[9px]"></i><span>Generate video</span>';
  }
}
async function cancelJob() {
  const b = $('#cancelJobBtn');
  b.disabled = true;
  try { await api('POST', '/api/flow/cancel'); } catch (e) { toast(e.message, 'error'); }
  finally { b.disabled = false; }
}

// ─────────────────────────────────────────────────────────────── HUD
let hudJob = null;
function updateHud(job) {
  if (!job) return;
  hudJob = job;
  const stage = (job.stage || 'idle').toLowerCase();
  const active = ACTIVE.has(stage);
  const label = { idle: 'Agent standby', queued: 'Queued', connecting: 'Opening Flow', initializing: 'Starting', submitting: 'Sending to Flow',
    waiting: 'Waiting for Flow', rendering: 'Rendering', downloading: 'Saving', ready: 'Done', error: 'Stopped', cancelled: 'Cancelled' }[stage] || stage;
  $('#liveAgentStage').textContent = job.title && stage !== 'idle' ? `${label} · ${job.title}` : label;
  const badge = $('#liveAgentBadge');
  badge.textContent = stage.toUpperCase();
  badge.className = 'text-[9px] font-mono px-1.5 rounded border ' + (
    stage === 'ready' ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
    : stage === 'error' ? 'bg-rose-500/15 text-rose-400 border-rose-500/30'
    : active ? 'bg-indigo-500/15 text-indigo-400 border-indigo-500/30'
    : 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20');
  $('#hudIcon').innerHTML = active ? spinner() : stage === 'ready' ? '<i class="fa-solid fa-check text-emerald-400 text-[11px]"></i>'
    : stage === 'error' ? '<i class="fa-solid fa-triangle-exclamation text-rose-400 text-[11px]"></i>'
    : '<span class="w-1.5 h-1.5 rounded-full volt-dot"></span>';
  $('#liveStatusText').textContent = job.message || '';
  $('#liveStatusText').title = job.message || '';
  const p = typeof job.progress === 'number' ? job.progress : (stage === 'ready' ? 100 : 0);
  $('#liveProgressBar').style.width = Math.max(0, Math.min(100, p)) + '%';
  $('#cancelJobBtn').classList.toggle('hidden', !(active && (job.kind || 'flow') === 'flow'));
  tickElapsed();
}
function tickElapsed() {
  const j = hudJob;
  const el = $('#liveElapsed');
  if (j && ACTIVE.has((j.stage || '').toLowerCase()) && j.started_at) el.textContent = fmtElapsed(Date.now() - j.started_at);
  else el.textContent = '';
  $$('[data-elapsed-from]').forEach((n) => { n.textContent = fmtElapsed(Date.now() - Number(n.dataset.elapsedFrom)); });
}

// ─────────────────────────────────────────────────────────────── activity feed
let unread = 0;
function paintFeedCount() {
  const c = $('#feedCount');
  c.textContent = unread > 99 ? '99+' : String(unread);
  c.classList.toggle('hidden', unread === 0);
}
function clearFeed() { $('#terminalLogs').innerHTML = ''; }
function appendLog(evt) {
  if (!evt || !evt.message || evt.type === 'generation') return;
  const box = $('#terminalLogs');
  const row = document.createElement('div');
  const isErr = evt.stage === 'error' || (evt.data && evt.data.ok === false) || (evt.data && evt.data.phase === 'error');
  const isOk = evt.type === 'video_ready' || (evt.data && evt.data.phase === 'success');
  row.className = 'log-row' + (isErr ? ' err' : isOk ? ' ok' : '') + (evt.type === 'agent' ? ' agent' : '');
  const tag = evt.type === 'agent' ? 'AGENT' : evt.type === 'flow_chat' ? 'FLOW' : evt.type === 'auth' ? 'SIGN-IN'
    : evt.type === 'recorder' ? 'API' : (evt.stage || evt.type || '').toUpperCase();
  const src = evt.source === 'mcp-agent' ? ' <span class="t">· via MCP</span>' : '';
  row.innerHTML = `<span class="t">[${esc(evt.timestamp || '')}]</span> <span class="s">${esc(tag)}</span> ${esc(evt.message)}${src}`;
  box.appendChild(row);
  while (box.children.length > 400) box.removeChild(box.firstChild);
  const anchor = $('#feedPopover').closest('.popover-anchor');
  if (anchor.classList.contains('is-open')) box.scrollTop = box.scrollHeight;
  else { unread += 1; paintFeedCount(); }
}

// ─────────────────────────────────────────────────────────────── live view
let liveTab = 'screen';
let lastFrameAt = 0;
function setLiveTab(tab) {
  liveTab = tab;
  $$('[data-live-tab]').forEach((b) => b.setAttribute('aria-selected', String(b.dataset.liveTab === tab)));
  $('#live-screen').classList.toggle('hidden', tab !== 'screen');
  $('#live-chat').classList.toggle('hidden', tab !== 'chat');
  if (tab === 'chat') { chatUnread = 0; paintChatCount(); const l = $('#chatList'); l.scrollTop = l.scrollHeight; }
}
function onFrame(f) {
  if (!f || !f.image) return;
  const img = $('#screenImg');
  img.src = 'data:image/jpeg;base64,' + f.image;
  img.classList.remove('hidden');
  $('#screenEmpty').classList.add('hidden');
  const meta = f.meta || {};
  const url = $('#screenUrl');
  if (meta.url) { url.textContent = (meta.title ? meta.title + ' — ' : '') + meta.url; url.classList.remove('hidden'); }
  lastFrameAt = Date.now();
  paintLiveState();
}
function paintLiveState() {
  const el = $('#liveViewState');
  const age = Date.now() - lastFrameAt;
  if (!lastFrameAt) { el.innerHTML = 'Idle'; return; }
  if (age < 6000) el.innerHTML = '<span class="inline-flex items-center gap-1.5 text-rose-400"><span class="w-1.5 h-1.5 rounded-full bg-rose-500 live-dot"></span>LIVE</span>';
  else el.textContent = 'Last picture ' + timeAgo(lastFrameAt);
}
async function peekBrowser() {
  try {
    const r = await api('POST', '/api/browser/peek');
    if (!r.running) toast('The Ashzo Browser is not open. Press "Show window" to start it.', 'info');
  } catch (e) { toast(e.message, 'error'); }
}
// In Docker the Ashzo Browser runs on the container's virtual screen, so "the window" is a browser view (noVNC) in a tab.
let viewerUrl = null;
function openViewer() {
  if (!viewerUrl) return;
  const tab = window.open(viewerUrl, 'ashzo-browser-view');
  if (!tab) toast('Your browser blocked the new tab. Open ' + viewerUrl, 'info');
}
async function showBrowserWindow() {
  openViewer(); // first, so the browser still counts it as a click
  try {
    toast('Opening the Ashzo Browser…');
    await api('POST', '/api/browser/open');
  } catch (e) { toast(e.message, 'error'); }
}

// Flow chat
let chatUnread = 0;
function paintChatCount() {
  const c = $('#chatCount');
  c.textContent = chatUnread ? `(${chatUnread})` : '';
  c.classList.toggle('hidden', !chatUnread);
}
function addChat(text, who = 'flow', title) {
  $('#chatEmpty') && $('#chatEmpty').remove();
  const list = $('#chatList');
  const m = document.createElement('div');
  m.className = 'chat-msg ' + (who === 'you' ? 'you' : 'flow');
  m.innerHTML = `<span class="who">${who === 'you' ? esc(title || 'Sent to Flow') : "Flow's agent"}</span>${esc(text)}`;
  list.appendChild(m);
  while (list.children.length > 200) list.removeChild(list.firstChild);
  list.scrollTop = list.scrollHeight;
  if (liveTab !== 'chat') { chatUnread += 1; paintChatCount(); }
}

// ─────────────────────────────────────────────────────────────── generations (live cards)
const gens = new Map();
const genKeys = new Map();
const genSent = new Set();
function genKey(g) { return [g.state, g.progress, g.message, (g.files || []).length, (g.chat || []).length].join('|'); }
function statusChip(g) {
  const s = (g.state || '').toLowerCase();
  if (ACTIVE.has(s)) return `<span class="status-chip active">${spinner()} ${esc(s)}</span>`;
  if (s === 'ready') return '<span class="status-chip ready"><i class="fa-solid fa-check"></i> ready</span>';
  if (s === 'error') return '<span class="status-chip error"><i class="fa-solid fa-triangle-exclamation"></i> stopped</span>';
  if (s === 'cancelled') return '<span class="status-chip cancelled">cancelled</span>';
  return `<span class="status-chip cancelled">${esc(s || 'unknown')}</span>`;
}
function genCardHTML(g) {
  const s = (g.state || '').toLowerCase();
  const active = ACTIVE.has(s);
  const files = g.files || [];
  const dur = g.duration === '30s_ad' ? '30s · 4 scenes' : (g.duration ? g.duration + 's' : '');
  let media;
  if (files.length && files[0].url) {
    media = `<video src="${esc(files[0].url)}" controls preload="metadata" playsinline muted></video>`;
  } else if (active) {
    media = `<div class="flex flex-col items-center gap-2 text-[11px] font-mono">${spinner('lg')}<span>${esc(g.message || 'Working…')}</span></div>`;
  } else if (s === 'error') {
    media = `<div class="px-5 text-center text-[11px] font-mono text-rose-400">${esc(g.message || 'Stopped')}</div>`;
  } else {
    media = '<i class="fa-regular fa-file-video text-xl"></i>';
  }
  const refsHtml = (g.references || []).map((r) => `<figure>${r.url ? `<img src="${esc(r.url)}" alt="${esc(r.role)} frame">`
    : `<div class="noimg" title="${esc(r.name || '')}"><i class="fa-regular fa-image"></i></div>`}<figcaption>${esc(r.role)}</figcaption></figure>`).join('');
  const last = (g.chat || []).slice(-1)[0];
  const more = files.length > 1 ? `<div class="flex flex-wrap gap-1.5">${files.slice(1).map((f) => `<a class="gen-chip hover:text-indigo-400" href="${esc(f.url)}" target="_blank" rel="noopener">scene ${esc(f.scene)}</a>`).join('')}</div>` : '';
  return `
    <div class="gen-media">${media}</div>
    <div class="gen-body">
      <div class="flex items-center justify-between gap-2">
        <div class="flex items-center gap-2 min-w-0">${statusChip(g)}<span class="text-xs font-semibold truncate">${esc(g.title || 'video')}</span></div>
        <span class="text-[10px] font-mono ashzo-text-dim whitespace-nowrap">${active && g.started_at ? `<span data-elapsed-from="${Number(g.started_at)}">${fmtElapsed(Date.now() - g.started_at)}</span>` : esc(timeAgo(g.finished_at || g.started_at))}</span>
      </div>
      ${active ? `<div class="w-full rounded-full h-1 overflow-hidden progress-track"><div class="h-1 rounded-full bg-gradient-to-r from-indigo-500 to-emerald-400 transition-all duration-500" style="width:${Math.max(3, Math.min(100, g.progress || 0))}%"></div></div>` : ''}
      <p class="gen-prompt" title="Click to expand">${esc(g.prompt || '')}</p>
      <div class="flex flex-wrap gap-1.5">
        <span class="gen-chip">${esc(g.model_label || g.model || '')}</span>
        ${dur ? `<span class="gen-chip">${esc(dur)}</span>` : ''}
        ${g.aspect_ratio ? `<span class="gen-chip">${esc(g.aspect_ratio)}</span>` : ''}
        ${g.quality ? `<span class="gen-chip">${esc(g.quality)}</span>` : ''}
        <span class="gen-chip">${g.source === 'mcp-agent' ? '<i class="fa-solid fa-robot mr-1"></i>Agent' : '<i class="fa-regular fa-user mr-1"></i>You'}</span>
      </div>
      ${refsHtml ? `<div class="gen-refs">${refsHtml}</div>` : ''}
      ${last ? `<p class="gen-reply" title="${esc(last.text)}">${esc(last.text)}</p>` : ''}
      ${more}
      ${files.length && files[0].url ? `<div class="flex items-center justify-between text-[10px] font-mono ashzo-text-dim"><span class="truncate" title="${esc(files[0].name)}">${esc(files[0].name)}</span><a href="${esc(files[0].url)}" download class="text-indigo-400 hover:text-indigo-300 ml-2"><i class="fa-solid fa-download"></i></a></div>` : ''}
    </div>`;
}
function upsertGeneration(g, fromLive = false) {
  if (!g || !g.id) return;
  gens.set(g.id, g);
  const key = genKey(g);
  let card = document.getElementById('gen-' + g.id);
  if (card && genKeys.get(g.id) === key) return;
  genKeys.set(g.id, key);
  const s = (g.state || '').toLowerCase();
  if (!card) {
    card = document.createElement('article');
    card.id = 'gen-' + g.id;
    const grid = $('#generationsGrid');
    grid.insertBefore(card, grid.firstChild);
  }
  card.className = 'gen-card' + (ACTIVE.has(s) ? ' is-active' : '') + (s === 'error' ? ' is-error' : '');
  card.innerHTML = genCardHTML(g);
  $('.gen-prompt', card).addEventListener('click', (e) => e.currentTarget.classList.toggle('is-open'));
  $('#generationsEmpty').classList.toggle('hidden', gens.size > 0);
  if (fromLive && g.sent_message && !genSent.has(g.id)) {
    genSent.add(g.id);
    addChat(g.sent_message, 'you', `Sent to Flow · ${g.title}`);
  }
}
async function loadGenerations() {
  try {
    const items = await api('GET', '/api/flow/generations');
    items.slice().reverse().forEach((g) => upsertGeneration(g));
    $('#generationsEmpty').classList.toggle('hidden', gens.size > 0);
  } catch (e) { console.warn(e); }
}

// ─────────────────────────────────────────────────────────────── vault
let knownFiles = null;
async function loadDownloads() {
  try {
    const files = await api('GET', '/api/flow/downloads');
    const box = $('#downloadsList');
    $('#vaultCount').textContent = files.length ? `${files.length} video${files.length === 1 ? '' : 's'}` : '';
    if (!files.length) { box.innerHTML = '<p class="text-xs ashzo-text-dim font-mono text-center py-8">No videos yet. Finished videos land here by themselves.</p>'; knownFiles = new Set(); return; }
    const prev = knownFiles;
    knownFiles = new Set(files.map((f) => f.rel));
    box.innerHTML = files.map((f) => `
      <div class="vault-item ${prev && !prev.has(f.rel) ? 'is-new' : ''} p-2.5 rounded-xl ashzo-card-sub border ashzo-border flex items-center justify-between gap-2">
        <div class="min-w-0">
          <p class="text-xs font-mono font-medium truncate" title="${esc(f.rel)}">${esc(f.name)}</p>
          <p class="text-[9.5px] font-mono ashzo-text-dim mt-0.5">${esc(f.size_mb)} MB · ${esc(f.modified)}</p>
        </div>
        <div class="flex items-center gap-1 flex-none">
          <button type="button" data-rename="${esc(f.rel)}" data-name="${esc(f.name)}" class="p-1 rounded ashzo-text-dim hover:text-indigo-400 transition" title="Rename" aria-label="Rename"><i class="fa-solid fa-pen text-[10px]"></i></button>
          <a href="${esc(f.url)}" target="_blank" rel="noopener" class="p-1 rounded ashzo-text-dim hover:text-indigo-400 transition" title="Play" aria-label="Play"><i class="fa-solid fa-play text-[10px]"></i></a>
          <a href="${esc(f.url)}" download class="p-1 rounded text-indigo-400 hover:text-indigo-300 transition" title="Download" aria-label="Download"><i class="fa-solid fa-download text-[10px]"></i></a>
        </div>
      </div>`).join('');
    $$('[data-rename]', box).forEach((b) => b.addEventListener('click', () => openRename(b.dataset.rename, b.dataset.name)));
  } catch (e) { console.warn(e); }
}
function openRename(rel, name) {
  $('#oldFilepathInput').value = rel;
  $('#newFilenameInput').value = name;
  openModal('renameModal');
  setTimeout(() => $('#newFilenameInput').select(), 60);
}
async function saveRename() {
  const rel = $('#oldFilepathInput').value;
  const newName = $('#newFilenameInput').value.trim();
  if (!newName) return;
  try {
    await api('POST', '/api/flow/rename', { rel, new_name: newName });
    closeModal('renameModal');
    toast('Renamed.', 'success');
    loadDownloads();
  } catch (e) { toast(e.message, 'error'); }
}

// ─────────────────────────────────────────────────────────────── credits
function paintCredits(c) {
  const val = $('#creditsValue');
  const dot = $('#creditsDot');
  const tier = $('#creditsTier');
  if (c && typeof c.live_credits === 'number') {
    val.textContent = c.live_credits.toLocaleString();
    val.className = 'font-semibold text-emerald-400';
    dot.className = 'w-1.5 h-1.5 rounded-full volt-dot';
    tier.textContent = c.tier || '';
    tier.classList.toggle('hidden', !c.tier);
    $('#creditsValue').parentElement.title = 'Checked ' + timeAgo(c.checked_at);
  } else {
    val.textContent = '—';
    val.className = 'font-semibold ashzo-text-dim';
    dot.className = 'w-1.5 h-1.5 rounded-full bg-slate-500';
    tier.classList.add('hidden');
    $('#creditsValue').parentElement.title = (c && c.message) || 'Press refresh to check your Flow credits.';
  }
}
async function loadCredits() {
  try { paintCredits(await api('GET', '/api/flow/credits')); } catch { paintCredits(null); }
}
async function refreshCredits() {
  const btn = $('#refreshCreditsBtn');
  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-rotate spin-btn"></i>';
  try {
    const c = await api('GET', '/api/flow/credits?refresh=true');
    paintCredits(c);
    if (c.status !== 'success') toast(c.message || "Couldn't read credits.", 'error');
  } catch (e) { toast(e.message, 'error'); }
  finally { btn.disabled = false; btn.innerHTML = '<i class="fa-solid fa-rotate"></i>'; }
}

// ─────────────────────────────────────────────────────────────── accounts
async function loadSessions() {
  try {
    const data = await api('GET', '/api/sessions');
    const sessions = data.sessions || [];
    const grid = $('#sessionsGrid');
    const active = sessions.find((s) => s.is_active);
    const name = active ? (active.email || active.name) : 'Not connected';
    $('#activeAccountName').textContent = name;
    $('#activeAccountName').className = 'font-medium truncate max-w-[170px] ' + (active ? 'text-indigo-400' : 'ashzo-text-muted');
    $('#activeDot').className = 'w-1.5 h-1.5 rounded-full ' + (active && active.cookie_count ? 'volt-dot' : 'bg-slate-500');
    if (!sessions.length) {
      grid.innerHTML = '<p class="text-xs ashzo-text-dim font-mono py-6 col-span-full text-center">No accounts yet. Press Add account and sign in once.</p>';
      return;
    }
    grid.innerHTML = sessions.map((s) => {
      const has = (s.cookie_count || 0) > 0;
      return `
      <div class="p-3.5 rounded-xl border transition ${s.is_active ? 'border-indigo-500/60 bg-indigo-500/5' : 'ashzo-card-sub ashzo-border'}">
        <div class="flex items-start justify-between gap-2">
          <div class="min-w-0">
            <p class="font-medium text-xs truncate">${esc(s.name)}</p>
            <p class="text-[10px] font-mono ashzo-text-dim mt-0.5 truncate">${esc(s.email || s.domain || '')}</p>
          </div>
          ${s.is_active ? '<span class="text-[8px] font-mono bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-1.5 py-0.5 rounded uppercase font-semibold">Active</span>' : ''}
        </div>
        <div class="mt-3 flex items-center justify-between text-xs">
          <span class="text-[9.5px] font-mono ${has ? 'text-emerald-400' : 'text-amber-400'}">${has ? `${esc(s.cookie_count)} cookies` : 'Needs sign-in'}</span>
          <div class="flex items-center gap-1.5">
            <button type="button" data-login="${esc(s.domain || '')}" data-email="${esc(s.email || '')}" class="text-[9.5px] font-mono px-2 py-0.5 rounded border ashzo-border hover:text-indigo-400 transition">Sign in again</button>
            ${!s.is_active ? `<button type="button" data-select="${esc(s.id)}" class="text-[9.5px] font-mono bg-indigo-600/10 text-indigo-400 border border-indigo-500/30 px-2 py-0.5 rounded hover:bg-indigo-600/20 transition">Use</button>` : ''}
            <button type="button" data-remove="${esc(s.id)}" data-label="${esc(s.email || s.name)}" class="text-[10px] ashzo-text-dim hover:text-rose-400 p-1 transition" aria-label="Remove"><i class="fa-regular fa-trash-can"></i></button>
          </div>
        </div>
      </div>`;
    }).join('');
    $$('[data-select]', grid).forEach((b) => b.addEventListener('click', async () => { await api('POST', `/api/sessions/${encodeURIComponent(b.dataset.select)}/select`); loadSessions(); }));
    $$('[data-remove]', grid).forEach((b) => b.addEventListener('click', async () => {
      if (await confirmDialog('Remove this account?', `${b.dataset.label} will be removed from Ashzo MCP. You can sign in again any time.`)) {
        await api('DELETE', `/api/sessions/${encodeURIComponent(b.dataset.remove)}`);
        loadSessions();
      }
    }));
    $$('[data-login]', grid).forEach((b) => b.addEventListener('click', () => openLoginModal(b.dataset.email, b.dataset.login ? 'https://' + b.dataset.login + '/' : '')));
  } catch (e) { console.warn(e); }
}
async function loadBrowserStatus() {
  try {
    const s = await api('GET', '/api/browser/status');
    viewerUrl = s.viewer_url || null;
    if (viewerUrl) {
      $$('[onclick="showBrowserWindow()"]').forEach((b) => {
        const label = [...b.childNodes].reverse().find((n) => n.nodeType === 3 && n.textContent.trim());
        if (label) label.textContent = label.textContent.replace(/Show window|Open window|Bring the window to front/, 'Open browser view');
      });
    }
    $('#browserStatus').textContent = s.running ? `Running · ${s.page ? new URL(s.page).host : 'no tab'}` : (s.chrome ? 'Not running' : 'Chrome not found');
  } catch { $('#browserStatus').textContent = 'Unknown'; }
}

// ─────────────────────────────────────────────────────────────── sign-in (Connect)
let loginJob = null;
let loginTimer = null;
function loginView(view) {
  $('#loginForm').classList.toggle('hidden', view !== 'form');
  $('#loginProgress').classList.toggle('hidden', view === 'form');
}
function openLoginModal(presetEmail, presetUrl) {
  loginJob = null;
  loginView('form');
  $('#loginEmailInput').value = presetEmail || '';
  if (presetUrl) {
    const known = $$('#dropdown-platform .dropdown-item').find((i) => i.dataset.value !== 'custom' && presetUrl.includes(new URL(i.dataset.value).host.replace('accounts.', '')));
    if (known) setDropdown('dropdown-platform', known.dataset.value);
    else { setDropdown('dropdown-platform', 'custom'); $('#loginCustomUrl').value = presetUrl; }
  }
  const btn = $('#launchLoginBtn');
  btn.disabled = false;
  btn.innerHTML = '<span>Open sign-in</span>';
  btn.onclick = startLogin;
  btn.classList.remove('hidden');
  $('#loginCancelBtn').textContent = 'Cancel';
  openModal('loginModal');
}
function closeLoginModal() {
  closeModal('loginModal');
  clearInterval(loginTimer);
}
async function startLogin() {
  const preset = dropdownValue('dropdown-platform');
  const url = preset === 'custom' ? $('#loginCustomUrl').value.trim() : preset;
  if (!url) { toast('Enter the website address.', 'error'); return; }
  openViewer(); // Docker: show the browser view now, the sign-in page appears in it
  const btn = $('#launchLoginBtn');
  btn.disabled = true;
  btn.innerHTML = `${spinner()}<span>Opening…</span>`;
  try {
    const r = await api('POST', '/api/auth/start', { target_url: url, expected_email: $('#loginEmailInput').value.trim() || null });
    paintLogin(r.job);
    if (r.status === 'busy') toast(r.message, 'info');
  } catch (e) {
    paintLogin({ phase: 'error', message: e.message });
  }
}
function paintLogin(job) {
  if (!job) return;
  loginJob = job;
  loginView('progress');
  const order = ['opening', 'waiting', 'saving'];
  const phase = job.phase;
  const idx = phase === 'success' ? 3 : order.indexOf(phase);
  $$('.login-steps li').forEach((li, i) => {
    li.classList.toggle('is-done', i < idx);
    li.classList.toggle('is-active', i === idx);
    $('.step-icon', li).innerHTML = i < idx ? '<i class="fa-solid fa-check"></i>' : i === idx ? spinner() : String(i + 1);
  });
  const msg = $('#loginMessage');
  const bad = ['error', 'timeout', 'cancelled'].includes(phase);
  msg.className = 'p-3 rounded-lg border text-[11px] font-mono ' + (phase === 'success' ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
    : bad ? 'bg-rose-500/10 border-rose-500/30 text-rose-400' : 'ashzo-card-sub ashzo-border');
  msg.textContent = job.message || '';
  const btn = $('#launchLoginBtn');
  const cancel = $('#loginCancelBtn');
  clearInterval(loginTimer);
  if (phase === 'success') {
    btn.classList.add('hidden');
    cancel.textContent = 'Close';
    $$('.login-steps li').forEach((li) => { li.classList.add('is-done'); li.classList.remove('is-active'); $('.step-icon', li).innerHTML = '<i class="fa-solid fa-check"></i>'; });
    $('#loginCountdown').textContent = '';
    setTimeout(() => { if (loginJob && loginJob.phase === 'success') closeLoginModal(); }, 1600);
  } else if (bad) {
    btn.classList.remove('hidden');
    btn.disabled = false;
    btn.innerHTML = '<span>Try again</span>';
    btn.onclick = () => { loginView('form'); btn.innerHTML = '<span>Open sign-in</span>'; btn.onclick = startLogin; };
    cancel.textContent = 'Close';
    $('#loginCountdown').textContent = '';
  } else {
    btn.classList.add('hidden');
    cancel.textContent = 'Cancel sign-in';
    if (job.deadline) {
      const tick = () => {
        const left = job.deadline - Date.now();
        $('#loginCountdown').textContent = left > 0 ? `Waiting for you · ${fmtElapsed(left)} left` : '';
      };
      tick();
      loginTimer = setInterval(tick, 1000);
    } else $('#loginCountdown').textContent = '';
  }
}
async function cancelLogin() {
  if (loginJob && ['opening', 'waiting', 'saving', 'starting'].includes(loginJob.phase)) {
    try { await api('POST', '/api/auth/cancel', { job_id: loginJob.id }); } catch (e) { toast(e.message, 'error'); }
    return;
  }
  closeLoginModal();
}

// ─────────────────────────────────────────────────────────────── settings
async function openSettings() {
  try {
    const s = await api('GET', '/api/settings');
    $('#setProjectUrl').value = s.flow_project_url || '';
    $('#setVisible').checked = !!s.browser_visible;
    $('#setRenderTimeout').value = Math.round((s.render_timeout_seconds || 900) / 60);
    $('#setLoginTimeout').value = Math.round((s.login_timeout_seconds || 300) / 60);
    openModal('settingsModal');
  } catch (e) { toast(e.message, 'error'); }
}
async function saveSettings() {
  const url = $('#setProjectUrl').value.trim();
  if (url && !/^https:\/\/(flow\.google\.com|labs\.google)\//.test(url)) { toast('Paste a Google Flow link (https://flow.google.com/…).', 'error'); return; }
  try {
    await api('POST', '/api/settings', {
      flow_project_url: url || 'https://flow.google.com/',
      browser_visible: $('#setVisible').checked,
      render_timeout_seconds: Math.max(2, Number($('#setRenderTimeout').value) || 15) * 60,
      login_timeout_seconds: Math.max(1, Number($('#setLoginTimeout').value) || 5) * 60,
      aspect_ratio: dropdownValue('dropdown-aspect'),
    });
    closeModal('settingsModal');
    toast('Settings saved.', 'success');
  } catch (e) { toast(e.message, 'error'); }
}

// ─────────────────────────────────────────────────────────────── explorer & API recorder
let learnerPoll = null;
function paintLearner(s) {
  if (!s) return;
  $('#learnerPhase').textContent = s.state || 'Ready';
  $('#learnerPhase').className = 'font-semibold ' + (s.state === 'ERROR' ? 'text-rose-400' : s.state === 'READY' || s.state === 'IDLE' ? 'text-emerald-400' : 'text-indigo-400');
  $('#learnerPct').textContent = (s.progress ?? 0) + '%';
  $('#learnerBar').style.width = (s.progress || 0) + '%';
  $('#learnerText').textContent = s.status_text || '';
}
async function runLearner() {
  const url = $('#learnerUrl').value.trim();
  if (!url) return;
  const btn = $('#learnerBtn');
  btn.disabled = true;
  btn.innerHTML = `${spinner()} Exploring`;
  try {
    await api('POST', '/api/learn-platform', { url });
    clearInterval(learnerPoll);
    learnerPoll = setInterval(async () => {
      const s = await api('GET', '/api/learn-platform/status');
      paintLearner(s);
      if (s.state === 'READY' || s.state === 'ERROR' || s.state === 'IDLE') {
        clearInterval(learnerPoll);
        btn.disabled = false;
        btn.textContent = 'Explore';
      }
    }, 1200);
  } catch (e) { toast(e.message, 'error'); btn.disabled = false; btn.textContent = 'Explore'; }
}
let recording = false;
function paintRecorder(rec) {
  recording = !!rec;
  const btn = $('#recorderBtn');
  btn.innerHTML = recording ? '<i class="fa-solid fa-stop text-[9px]"></i><span>Stop</span>' : '<i class="fa-solid fa-circle text-[8px]"></i><span>Record</span>';
  $('#recorderState').innerHTML = recording ? '<span class="inline-flex items-center gap-1.5 text-rose-400"><span class="w-1.5 h-1.5 rounded-full bg-rose-500 live-dot"></span>Recording</span>' : 'Not recording';
}
async function toggleRecorder() {
  const btn = $('#recorderBtn');
  btn.disabled = true;
  try {
    if (!recording) {
      $('#recorderList').innerHTML = '';
      const r = await api('POST', '/api/flow/recorder/start');
      paintRecorder(r.recording);
    } else {
      const r = await api('POST', '/api/flow/recorder/stop');
      paintRecorder(false);
      if (r.file) toast(`Saved ${r.count} requests to ${r.file.split(/[\\/]/).pop()}`, 'success');
    }
  } catch (e) { toast(e.message, 'error'); }
  finally { btn.disabled = false; }
}
function onRecorderEvent(evt) {
  const d = evt.data || {};
  if (typeof d.recording === 'boolean') paintRecorder(d.recording);
  const list = $('#recorderList');
  const row = document.createElement('div');
  row.className = 'log-row';
  row.innerHTML = `<span class="t">[${esc(evt.timestamp)}]</span> ${esc(evt.message)}`;
  list.appendChild(row);
  list.scrollTop = list.scrollHeight;
}

// ─────────────────────────────────────────────────────────────── fast path
async function runRequest() {
  const btn = $('#runBtn');
  btn.disabled = true;
  btn.innerHTML = spinner();
  $('#runnerOutput code').textContent = 'Running…';
  try {
    const data = await api('POST', '/api/request', { url: $('#runnerUrl').value.trim(), method: 'GET', force_tier: Number(dropdownValue('dropdown-tier')) });
    $('#runnerOutput code').textContent = JSON.stringify(data, null, 2);
  } catch (e) { $('#runnerOutput code').textContent = 'Error: ' + e.message; }
  finally { btn.disabled = false; btn.textContent = 'Run'; }
}

// ─────────────────────────────────────────────────────────────── live streams
let es = null;
let esRetry = 1000;
function setConn(state) {
  const dot = $('#liveConnDot');
  const txt = $('#liveConnText');
  if (state === 'live') { dot.className = 'w-1.5 h-1.5 rounded-full volt-dot'; txt.textContent = 'Live'; }
  else if (state === 'retry') { dot.className = 'w-1.5 h-1.5 rounded-full bg-amber-400'; txt.textContent = 'Reconnecting…'; }
  else { dot.className = 'w-1.5 h-1.5 rounded-full bg-amber-400'; txt.textContent = 'Connecting…'; }
}
let vaultTimer = null;
function handleEvent(evt) {
  switch (evt.type) {
    case 'init': {
      const d = evt.data || {};
      updateHud(d.active_job);
      (d.recent_logs || []).forEach(appendLog);
      unread = 0; paintFeedCount();
      (d.flow_chat || []).forEach((c) => addChat(c.message));
      chatUnread = 0; paintChatCount();
      return;
    }
    case 'generation':
      upsertGeneration(evt.data, true);
      return;
    case 'flow_chat':
      addChat(evt.message);
      appendLog(evt);
      return;
    case 'auth':
      appendLog(evt);
      if (evt.data) {
        if (!loginJob || loginJob.id === evt.data.id || !$('#loginModal').classList.contains('is-open')) {
          if ($('#loginModal').classList.contains('is-open')) paintLogin(evt.data);
        }
        if (evt.data.phase === 'success') { toast(evt.message, 'success'); loadSessions(); }
        if (evt.data.phase === 'timeout' || evt.data.phase === 'error') toast(evt.message, 'error');
      }
      return;
    case 'sessions_changed':
      loadSessions();
      return;
    case 'vault_changed':
      clearTimeout(vaultTimer);
      vaultTimer = setTimeout(loadDownloads, 300);
      return;
    case 'credits':
      paintCredits(evt.data);
      return;
    case 'recorder':
      onRecorderEvent(evt);
      appendLog(evt);
      return;
    case 'browser':
      appendLog(evt);
      loadBrowserStatus();
      return;
    default:
      if (evt.stage) {
        const kind = (evt.data && evt.data.kind) || 'flow';
        if (kind === 'flow') updateHud({ ...(hudJob || {}), ...evt.data, stage: evt.stage, progress: evt.progress ?? (hudJob || {}).progress, message: evt.message,
          started_at: (evt.data && evt.data.started_at) || (hudJob && ACTIVE.has((hudJob.stage || '').toLowerCase()) && hudJob.started_at) || evt.ts });
        if (evt.stage === 'error') toast(evt.message, 'error');
      }
      if (evt.type === 'video_ready') { toast(evt.message, 'success'); loadDownloads(); loadCredits(); }
      appendLog(evt);
  }
}
function connectStream() {
  if (es) es.close();
  setConn(esRetry > 1000 ? 'retry' : 'connecting');
  es = new EventSource('/api/live/stream');
  es.onopen = () => { esRetry = 1000; setConn('live'); };
  es.onmessage = (e) => { try { handleEvent(JSON.parse(e.data)); } catch (err) { console.warn('bad event', err); } };
  es.onerror = () => {
    setConn('retry');
    es.close();
    setTimeout(connectStream, esRetry);
    esRetry = Math.min(esRetry * 2, 15000);
  };
}
let screenEs = null;
function connectScreen() {
  if (screenEs) screenEs.close();
  screenEs = new EventSource('/api/live/screen');
  screenEs.onmessage = (e) => { try { onFrame(JSON.parse(e.data)); } catch {} };
  screenEs.onerror = () => { screenEs.close(); setTimeout(connectScreen, 3000); };
}

// ─────────────────────────────────────────────────────────────── init
function init() {
  initTheme();
  initDropdowns();
  initReferences();
  dropdownHandlers['dropdown-model'] = () => renderDurations();
  dropdownHandlers['dropdown-platform'] = (v) => $('#customUrlDiv').classList.toggle('hidden', v !== 'custom');
  renderDurations();
  api('GET', '/api/settings').then((s) => { if (s && s.aspect_ratio) setDropdown('dropdown-aspect', s.aspect_ratio, true); }).catch(() => {});
  api('GET', '/api/health').then((h) => { if (h && h.version) $('#versionBadge').textContent = 'v' + h.version.split('.').slice(0, 2).join('.'); }).catch(() => {});
  loadBrowserStatus(); // learns the browser-view address when running in Docker
  loadSessions();
  loadDownloads();
  loadCredits();
  loadGenerations();
  connectStream();
  connectScreen();
  setInterval(() => { tickElapsed(); paintLiveState(); }, 1000);
  const tab = (location.hash || '').slice(1);
  if (['sessions', 'learner', 'playground'].includes(tab)) switchTab(tab);
}
document.addEventListener('DOMContentLoaded', init);
