/**
 * KalaOS — Workspace Usage Analytics  (#41)
 *
 * Tracks workspace opens and surfaces insights: total opens, most active
 * workspace, last active date, weekly activity graph, and monthly statistics.
 *
 * localStorage key: 'kala-ws-analytics'
 * Each open event: { wsId, ts }  (timestamp in ms)
 * Max stored events: 2000 (oldest pruned automatically)
 */

/* ──────────────────────────────────────────────
   Constants
────────────────────────────────────────────── */

const _WSA_STORAGE_KEY = 'kala-ws-analytics';
const _WSA_MAX_EVENTS  = 2000;

/* ──────────────────────────────────────────────
   Storage
────────────────────────────────────────────── */

function _wsaLoad() {
  try { return JSON.parse(localStorage.getItem(_WSA_STORAGE_KEY) || '[]'); }
  catch { return []; }
}

function _wsaSave(events) {
  if (events.length > _WSA_MAX_EVENTS) events = events.slice(-_WSA_MAX_EVENTS);
  localStorage.setItem(_WSA_STORAGE_KEY, JSON.stringify(events));
}

/* ──────────────────────────────────────────────
   Tracking
────────────────────────────────────────────── */

/**
 * Record a workspace open event.
 * Called automatically when a workspace is opened via the Sharing panel.
 * @param {string} wsId
 */
function wsaTrackOpen(wsId) {
  if (!wsId) return;
  const events = _wsaLoad();
  events.push({ wsId, ts: Date.now() });
  _wsaSave(events);
}

/* ──────────────────────────────────────────────
   Analytics Computation
────────────────────────────────────────────── */

/**
 * Return per-workspace stats for all workspaces the current user can access.
 * @returns {object[]}  sorted by totalOpens desc
 *   { ws, totalOpens, lastOpenTs, weeklyOpens[7], monthlyOpens[12] }
 */
function wsaGetAllStats() {
  const email = typeof _wshCurrentUserEmail === 'function' ? _wshCurrentUserEmail() : null;
  if (!email) return [];

  const workspaces = typeof _wshLoad === 'function'
    ? _wshLoad().filter(w => w.members.some(m => m.email === email))
    : [];

  const events = _wsaLoad();
  const now    = Date.now();

  return workspaces
    .map(ws => {
      const wsEvents = events.filter(e => e.wsId === ws.id);
      const totalOpens = wsEvents.length;
      const lastOpenTs = wsEvents.length ? Math.max(...wsEvents.map(e => e.ts)) : null;

      // Weekly opens: last 7 days, index 0 = 6 days ago … index 6 = today
      const weeklyOpens = Array(7).fill(0);
      wsEvents.forEach(e => {
        const daysAgo = Math.floor((now - e.ts) / 86400000);
        if (daysAgo < 7) weeklyOpens[6 - daysAgo]++;
      });

      // Monthly opens: last 12 months, index 0 = 11 months ago … index 11 = this month
      const monthlyOpens = Array(12).fill(0);
      wsEvents.forEach(e => {
        const d = new Date(e.ts);
        const n = new Date(now);
        const monthsAgo = (n.getFullYear() - d.getFullYear()) * 12 + (n.getMonth() - d.getMonth());
        if (monthsAgo >= 0 && monthsAgo < 12) monthlyOpens[11 - monthsAgo]++;
      });

      return { ws, totalOpens, lastOpenTs, weeklyOpens, monthlyOpens };
    })
    .sort((a, b) => b.totalOpens - a.totalOpens);
}

/**
 * Return stats for a single workspace.
 * @param {string} wsId
 * @returns {object|null}
 */
function wsaGetStats(wsId) {
  return wsaGetAllStats().find(s => s.ws.id === wsId) || null;
}

/* ──────────────────────────────────────────────
   UI State
────────────────────────────────────────────── */

let _wsaDetailId = null; // wsId currently shown in detail view, null = overview

function openWorkspaceAnalytics() {
  const panel = document.getElementById('wsaPanel');
  if (!panel) return;
  _wsaDetailId = null;
  _wsaRenderDashboard();
  panel.classList.remove('hidden');
}

function closeWorkspaceAnalytics() {
  document.getElementById('wsaPanel')?.classList.add('hidden');
}

/* ──────────────────────────────────────────────
   Rendering — Dashboard Overview
────────────────────────────────────────────── */

function _wsaRenderDashboard() {
  const container = document.getElementById('wsaContent');
  if (!container) return;

  const stats = wsaGetAllStats();

  if (stats.length === 0) {
    container.innerHTML = `
      <div class="wsa-empty">
        <span class="wsa-empty-icon">📊</span>
        <p>No workspace activity yet.</p>
        <p class="wsa-empty-hint">Open workspaces via the Sharing panel to start tracking usage.</p>
      </div>`;
    return;
  }

  const totalAll   = stats.reduce((s, x) => s + x.totalOpens, 0);
  const mostActive = stats[0];
  const recentlyUsed = stats
    .filter(s => s.lastOpenTs)
    .sort((a, b) => b.lastOpenTs - a.lastOpenTs)[0];

  // Aggregate weekly across all workspaces
  const globalWeekly = Array(7).fill(0);
  stats.forEach(s => s.weeklyOpens.forEach((v, i) => { globalWeekly[i] += v; }));

  const dayLabels = _wsaDayLabels();

  container.innerHTML = `
    <div class="wsa-section">

      <!-- Summary cards -->
      <div class="wsa-summary-grid">
        <div class="wsa-stat-card">
          <span class="wsa-stat-value">${totalAll}</span>
          <span class="wsa-stat-label">Total Opens</span>
        </div>
        <div class="wsa-stat-card">
          <span class="wsa-stat-value">${stats.length}</span>
          <span class="wsa-stat-label">Workspaces Tracked</span>
        </div>
        <div class="wsa-stat-card wsa-stat-highlight">
          <span class="wsa-stat-value wsa-stat-name">${esc(mostActive.ws.name)}</span>
          <span class="wsa-stat-label">Most Active</span>
        </div>
        <div class="wsa-stat-card">
          <span class="wsa-stat-value wsa-stat-name">${recentlyUsed ? esc(recentlyUsed.ws.name) : '—'}</span>
          <span class="wsa-stat-label">Last Used</span>
        </div>
      </div>

      <!-- Global weekly graph -->
      <div class="wsa-chart-block">
        <div class="wsa-chart-title">📅 Activity — Last 7 Days (all workspaces)</div>
        ${_wsaBarChart(globalWeekly, dayLabels)}
      </div>

      <!-- Per-workspace table -->
      <div class="wsa-table-title">Workspace Breakdown</div>
      <div class="wsa-table">
        <div class="wsa-table-head">
          <span>Workspace</span>
          <span>Total Opens</span>
          <span>This Week</span>
          <span>Last Active</span>
          <span></span>
        </div>
        ${stats.map(s => `
          <div class="wsa-table-row" onclick="_wsaOpenDetail('${s.ws.id}')">
            <span class="wsa-ws-name">${esc(s.ws.name)}${s.ws.archivedAt ? ' <span class="wsa-archived-chip">archived</span>' : ''}</span>
            <span class="wsa-opens-val">${s.totalOpens}</span>
            <span class="wsa-week-val">${s.weeklyOpens.reduce((a,b)=>a+b,0)}</span>
            <span class="wsa-last-val">${s.lastOpenTs ? _wsaFormatDate(s.lastOpenTs) : '—'}</span>
            <span class="wsa-detail-arrow">›</span>
          </div>`).join('')}
      </div>
    </div>`;
}

/* ──────────────────────────────────────────────
   Rendering — Workspace Detail
────────────────────────────────────────────── */

function _wsaOpenDetail(wsId) {
  _wsaDetailId = wsId;
  _wsaRenderDetail(wsId);
}

function _wsaRenderDetail(wsId) {
  const container = document.getElementById('wsaContent');
  if (!container) return;

  const s = wsaGetStats(wsId);
  if (!s) { _wsaRenderDashboard(); return; }

  const dayLabels   = _wsaDayLabels();
  const monthLabels = _wsaMonthLabels();
  const weekTotal   = s.weeklyOpens.reduce((a,b)=>a+b,0);
  const monthTotal  = s.monthlyOpens.reduce((a,b)=>a+b,0);

  container.innerHTML = `
    <div class="wsa-section">
      <div class="wsa-detail-header">
        <button class="btn-ghost wsh-btn-sm" onclick="_wsaRenderDashboard()">← Back</button>
        <span class="wsa-detail-title">${esc(s.ws.name)}</span>
      </div>

      <div class="wsa-summary-grid">
        <div class="wsa-stat-card">
          <span class="wsa-stat-value">${s.totalOpens}</span>
          <span class="wsa-stat-label">Total Opens</span>
        </div>
        <div class="wsa-stat-card">
          <span class="wsa-stat-value">${weekTotal}</span>
          <span class="wsa-stat-label">This Week</span>
        </div>
        <div class="wsa-stat-card">
          <span class="wsa-stat-value">${monthTotal}</span>
          <span class="wsa-stat-label">This Month</span>
        </div>
        <div class="wsa-stat-card">
          <span class="wsa-stat-value">${s.lastOpenTs ? _wsaFormatDate(s.lastOpenTs) : '—'}</span>
          <span class="wsa-stat-label">Last Active</span>
        </div>
      </div>

      <div class="wsa-chart-block">
        <div class="wsa-chart-title">📅 Weekly Activity (last 7 days)</div>
        ${_wsaBarChart(s.weeklyOpens, dayLabels)}
      </div>

      <div class="wsa-chart-block">
        <div class="wsa-chart-title">📆 Monthly Activity (last 12 months)</div>
        ${_wsaBarChart(s.monthlyOpens, monthLabels, true)}
      </div>

      <div class="wsa-members-note">
        ${s.ws.members.length} member${s.ws.members.length !== 1 ? 's' : ''}
        · Created ${_wsaFormatDate(s.ws.createdAt)}
        ${s.ws.archivedAt ? `· <span class="wsa-archived-chip">archived ${_wsaFormatDate(s.ws.archivedAt)}</span>` : ''}
      </div>
    </div>`;
}

/* ──────────────────────────────────────────────
   Chart Helper — SVG bar chart
────────────────────────────────────────────── */

/**
 * Render a simple SVG bar chart.
 * @param {number[]} values
 * @param {string[]} labels
 * @param {boolean}  compact  — use smaller bars for 12-month view
 * @returns {string}  HTML string
 */
function _wsaBarChart(values, labels, compact = false) {
  const max    = Math.max(...values, 1);
  const W      = 100 / values.length;
  const barW   = compact ? W * 0.55 : W * 0.6;
  const barX   = (i) => i * W + (W - barW) / 2;
  const height = compact ? 60 : 80;

  const bars = values.map((v, i) => {
    const barH  = Math.max((v / max) * height, v > 0 ? 3 : 0);
    const y     = height - barH;
    const pct   = max > 0 ? Math.round((v / max) * 100) : 0;
    return `
      <g class="wsa-bar-group" aria-label="${labels[i]}: ${v} opens">
        <rect class="wsa-bar${v === 0 ? ' wsa-bar-zero' : ''}"
          x="${barX(i)}%" y="${y}" width="${barW}%" height="${barH}"
          rx="2" />
        <text class="wsa-bar-label" x="${i * W + W / 2}%" y="${height + 14}" text-anchor="middle">${labels[i]}</text>
        ${v > 0 ? `<text class="wsa-bar-val" x="${i * W + W / 2}%" y="${y - 3}" text-anchor="middle">${v}</text>` : ''}
      </g>`;
  }).join('');

  return `
    <div class="wsa-chart-wrap">
      <svg class="wsa-chart" viewBox="0 0 100 ${height + 22}" preserveAspectRatio="none"
           role="img" aria-label="Bar chart">
        ${bars}
      </svg>
    </div>`;
}

/* ──────────────────────────────────────────────
   Label Helpers
────────────────────────────────────────────── */

function _wsaDayLabels() {
  const days = ['Su','Mo','Tu','We','Th','Fr','Sa'];
  const today = new Date().getDay();
  return Array.from({ length: 7 }, (_, i) => days[(today - 6 + i + 7) % 7]);
}

function _wsaMonthLabels() {
  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const now = new Date();
  return Array.from({ length: 12 }, (_, i) => months[(now.getMonth() - 11 + i + 12) % 12]);
}

function _wsaFormatDate(ts) {
  if (!ts) return '—';
  return new Date(ts).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}

/* ──────────────────────────────────────────────
   Auto-instrument workspace opens
────────────────────────────────────────────── */

// Patch _wshOpenWorkspace after DOM is ready so every workspace open is tracked.
document.addEventListener('DOMContentLoaded', () => {
  const _origOpen = typeof _wshOpenWorkspace !== 'undefined' ? _wshOpenWorkspace : null;
  // Use a polling approach since workspace_sharing.js loads before this file
  const _patch = () => {
    if (typeof _wshOpenWorkspace === 'function' && _wshOpenWorkspace._wsaPatched !== true) {
      const _orig = _wshOpenWorkspace;
      window._wshOpenWorkspace = function(wsId) {
        wsaTrackOpen(wsId);
        return _orig(wsId);
      };
      window._wshOpenWorkspace._wsaPatched = true;
    }
  };
  _patch();
  setTimeout(_patch, 500);
});
