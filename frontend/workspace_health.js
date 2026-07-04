/**
 * KalaOS — Workspace Health Score  (#51)
 *
 * Calculates a 0–100 health score for each workspace using 5 measurable
 * metrics derived from existing localStorage data. Displays an overall score,
 * per-metric breakdown, and actionable improvement suggestions.
 *
 * Reads from: 'kala-workspaces', 'kala-ws-activity', 'kala-ws-analytics',
 *             'kala-ws-favorites'
 * Writes to:  nothing — purely read-only analytics
 */

/* ──────────────────────────────────────────────
   Metric Definitions
────────────────────────────────────────────── */

/**
 * Each metric: { id, label, icon, weight, compute(ws) → 0–1, suggest(score, ws) → string|null }
 * Weights must sum to 1.
 */
const _WSH_HEALTH_METRICS = [
  {
    id: 'activity',
    label: 'Recent Activity',
    icon: '⚡',
    weight: 0.30,
    compute(ws) {
      // Score based on opens in the last 30 days (from analytics)
      const events = _wshHealthAnalyticsEvents(ws.id);
      const cutoff = Date.now() - 30 * 86400000;
      const recent = events.filter(e => e.ts >= cutoff).length;
      // 10+ opens in 30 days = perfect; 0 = 0
      return Math.min(recent / 10, 1);
    },
    suggest(score, ws) {
      if (score < 0.2) return 'This workspace has had little activity in the last 30 days. Open it regularly or consider archiving it.';
      if (score < 0.6) return 'Moderate activity detected. Try opening this workspace more consistently.';
      return null;
    },
  },
  {
    id: 'collaboration',
    label: 'Collaboration',
    icon: '🤝',
    weight: 0.25,
    compute(ws) {
      const memberCount = ws.members.length;
      const roles = new Set(ws.members.map(m => m.role));
      // 1 member = 0.2, 2 = 0.5, 3+ = 0.8; bonus 0.2 for role diversity (>1 role)
      const base  = Math.min((memberCount - 1) / 3, 0.8);
      const bonus = roles.size > 1 ? 0.2 : 0;
      return Math.min(base + bonus, 1);
    },
    suggest(score, ws) {
      if (ws.members.length === 1) return 'Invite collaborators to improve teamwork and workspace value.';
      if (ws.members.every(m => m.role === ws.members[0].role)) return 'Consider assigning different roles (Viewer, Editor, Admin) for better access control.';
      return null;
    },
  },
  {
    id: 'naming',
    label: 'Naming Quality',
    icon: '✏️',
    weight: 0.15,
    compute(ws) {
      const name = (ws.name || '').trim();
      // Penalise generic names, very short names, and "(copy)" suffixes
      const genericPatterns = [/^workspace\s*\d*$/i, /^untitled/i, /\(copy\)$/i, /\(imported\)$/i];
      if (genericPatterns.some(r => r.test(name))) return 0.2;
      if (name.length < 4)  return 0.3;
      if (name.length < 8)  return 0.6;
      if (name.length > 60) return 0.7; // overly long
      return 1;
    },
    suggest(score, ws) {
      const name = (ws.name || '').trim();
      if (/\(copy\)$/i.test(name))      return 'Rename this workspace — "(copy)" names are hard to identify at a glance.';
      if (/\(imported\)$/i.test(name))  return 'Rename this imported workspace to something meaningful.';
      if (/^workspace\s*\d*$/i.test(name) || /^untitled/i.test(name))
                                         return 'Give this workspace a descriptive name that reflects its purpose.';
      if (name.length < 4)               return 'The workspace name is too short. Use a more descriptive title.';
      return null;
    },
  },
  {
    id: 'engagement',
    label: 'Timeline Engagement',
    icon: '📅',
    weight: 0.20,
    compute(ws) {
      // Score based on total activity log events (invites, role changes, etc.)
      const log = _wshHealthActivityLog(ws.id);
      // 10+ events = perfect
      return Math.min(log.length / 10, 1);
    },
    suggest(score, ws) {
      if (score < 0.3) return 'Low timeline activity. Invite members, change roles, or use the workspace more to build its history.';
      return null;
    },
  },
  {
    id: 'maintenance',
    label: 'Maintenance',
    icon: '🔧',
    weight: 0.10,
    compute(ws) {
      // Penalise workspaces that are old but have never been opened
      const ageMs   = Date.now() - (ws.createdAt || Date.now());
      const ageDays = ageMs / 86400000;
      const events  = _wshHealthAnalyticsEvents(ws.id);
      if (ageDays < 1) return 1; // brand new
      if (events.length === 0 && ageDays > 7) return 0.2; // old and never opened
      if (events.length === 0) return 0.5;
      // Last open recency
      const lastOpen = Math.max(...events.map(e => e.ts));
      const daysSince = (Date.now() - lastOpen) / 86400000;
      if (daysSince > 60) return 0.3;
      if (daysSince > 30) return 0.6;
      return 1;
    },
    suggest(score, ws) {
      const events  = _wshHealthAnalyticsEvents(ws.id);
      const ageDays = (Date.now() - (ws.createdAt || Date.now())) / 86400000;
      if (events.length === 0 && ageDays > 7) return 'This workspace has never been opened. Open it or archive it to keep things tidy.';
      if (score < 0.4) return 'This workspace hasn\'t been opened in over 60 days. Consider archiving it if it\'s no longer needed.';
      if (score < 0.7) return 'This workspace hasn\'t been opened in over 30 days. Check if it\'s still relevant.';
      return null;
    },
  },
];

/* ──────────────────────────────────────────────
   Data Helpers (read-only, no cross-file deps)
────────────────────────────────────────────── */

function _wshHealthAnalyticsEvents(wsId) {
  try {
    const all = JSON.parse(localStorage.getItem('kala-ws-analytics') || '[]');
    return all.filter(e => e.wsId === wsId);
  } catch { return []; }
}

function _wshHealthActivityLog(wsId) {
  try {
    const log = JSON.parse(localStorage.getItem('kala-ws-activity') || '{}');
    return log[wsId] || [];
  } catch { return []; }
}

/* ──────────────────────────────────────────────
   Score Computation
────────────────────────────────────────────── */

/**
 * Compute the health score for a single workspace.
 * @param {object} ws  — workspace object from _wshLoad()
 * @returns {{
 *   overall: number,          // 0–100 integer
 *   grade: string,            // 'Excellent'|'Good'|'Fair'|'Poor'
 *   gradeColor: string,       // CSS color token
 *   metrics: object[],        // per-metric { id, label, icon, score0to1, pct, suggestion }
 *   suggestions: string[],    // non-null suggestions only
 * }}
 */
function wshComputeHealth(ws) {
  const metrics = _WSH_HEALTH_METRICS.map(m => {
    const raw  = Math.max(0, Math.min(1, m.compute(ws)));
    const sugg = m.suggest(raw, ws);
    return { id: m.id, label: m.label, icon: m.icon, weight: m.weight, score0to1: raw, pct: Math.round(raw * 100), suggestion: sugg };
  });

  const overall = Math.round(
    metrics.reduce((sum, m) => sum + m.score0to1 * m.weight, 0) * 100
  );

  let grade, gradeColor;
  if (overall >= 80) { grade = 'Excellent'; gradeColor = '#4ade80'; }
  else if (overall >= 60) { grade = 'Good';      gradeColor = '#7c5af1'; }
  else if (overall >= 40) { grade = 'Fair';      gradeColor = '#f0b429'; }
  else                    { grade = 'Poor';      gradeColor = '#e23270'; }

  return {
    overall,
    grade,
    gradeColor,
    metrics,
    suggestions: metrics.map(m => m.suggestion).filter(Boolean),
  };
}

/**
 * Compute health for all accessible workspaces, sorted by score ascending
 * (worst first — most in need of attention).
 * @returns {object[]}  { ws, health }
 */
function wshComputeAllHealth() {
  const email = typeof _wshCurrentUserEmail === 'function' ? _wshCurrentUserEmail() : null;
  if (!email) return [];
  const workspaces = typeof _wshLoad === 'function'
    ? _wshLoad().filter(w => !w.archivedAt && w.members.some(m => m.email === email))
    : [];
  return workspaces
    .map(ws => ({ ws, health: wshComputeHealth(ws) }))
    .sort((a, b) => a.health.overall - b.health.overall);
}

/* ──────────────────────────────────────────────
   UI State
────────────────────────────────────────────── */

let _wsHealthDetailId = null;

function openWorkspaceHealth() {
  const panel = document.getElementById('wshHealthPanel');
  if (!panel) return;
  _wsHealthDetailId = null;
  _wsHealthRenderOverview();
  panel.classList.remove('hidden');
}

function closeWorkspaceHealth() {
  document.getElementById('wshHealthPanel')?.classList.add('hidden');
}

/* ──────────────────────────────────────────────
   Rendering — Overview
────────────────────────────────────────────── */

function _wsHealthRenderOverview() {
  const container = document.getElementById('wshHealthContent');
  if (!container) return;

  const all = wshComputeAllHealth();

  if (all.length === 0) {
    container.innerHTML = `
      <div class="wsh-health-empty">
        <span class="wsh-health-empty-icon">🏥</span>
        <p>No active workspaces to analyse.</p>
        <p class="wsh-health-empty-hint">Create a workspace in the Sharing panel to see its health score.</p>
      </div>`;
    return;
  }

  // Fleet summary
  const avgScore  = Math.round(all.reduce((s, x) => s + x.health.overall, 0) / all.length);
  const excellent = all.filter(x => x.health.overall >= 80).length;
  const poor      = all.filter(x => x.health.overall < 40).length;
  const totalSugg = all.reduce((s, x) => s + x.health.suggestions.length, 0);

  container.innerHTML = `
    <div class="wsh-health-section">

      <!-- Fleet summary -->
      <div class="wsh-health-summary-grid">
        <div class="wsh-health-stat">
          ${_wsHealthRing(avgScore, '#7c5af1', 52)}
          <span class="wsh-health-stat-label">Avg Score</span>
        </div>
        <div class="wsh-health-stat">
          <span class="wsh-health-big" style="color:#4ade80">${excellent}</span>
          <span class="wsh-health-stat-label">Excellent</span>
        </div>
        <div class="wsh-health-stat">
          <span class="wsh-health-big" style="color:#e23270">${poor}</span>
          <span class="wsh-health-stat-label">Need Attention</span>
        </div>
        <div class="wsh-health-stat">
          <span class="wsh-health-big" style="color:#f0b429">${totalSugg}</span>
          <span class="wsh-health-stat-label">Suggestions</span>
        </div>
      </div>

      <!-- Per-workspace cards -->
      <div class="wsh-health-list">
        ${all.map(({ ws, health }) => `
          <div class="wsh-health-card" onclick="_wsHealthOpenDetail('${ws.id}')">
            <div class="wsh-health-card-left">
              ${_wsHealthRing(health.overall, health.gradeColor, 44)}
            </div>
            <div class="wsh-health-card-body">
              <div class="wsh-health-card-name-row">
                <span class="wsh-health-card-name">${esc(ws.name)}</span>
                <span class="wsh-health-grade-chip" style="--grade-color:${health.gradeColor}">${health.grade}</span>
              </div>
              <div class="wsh-health-metric-bars">
                ${health.metrics.map(m => `
                  <div class="wsh-health-mini-bar" title="${m.label}: ${m.pct}%">
                    <div class="wsh-health-mini-fill" style="width:${m.pct}%;background:${_wsHealthMetricColor(m.pct)}"></div>
                  </div>`).join('')}
              </div>
              ${health.suggestions.length > 0
                ? `<span class="wsh-health-sugg-count">💡 ${health.suggestions.length} suggestion${health.suggestions.length !== 1 ? 's' : ''}</span>`
                : `<span class="wsh-health-sugg-count wsh-health-sugg-ok">✓ No issues</span>`}
            </div>
            <span class="wsh-health-arrow">›</span>
          </div>`).join('')}
      </div>
    </div>`;
}

/* ──────────────────────────────────────────────
   Rendering — Detail
────────────────────────────────────────────── */

function _wsHealthOpenDetail(wsId) {
  _wsHealthDetailId = wsId;
  _wsHealthRenderDetail(wsId);
}

function _wsHealthRenderDetail(wsId) {
  const container = document.getElementById('wshHealthContent');
  if (!container) return;

  const ws = typeof wshGetWorkspace === 'function' ? wshGetWorkspace(wsId) : null;
  if (!ws) { _wsHealthRenderOverview(); return; }

  const health = wshComputeHealth(ws);

  container.innerHTML = `
    <div class="wsh-health-section">
      <div class="wsh-health-detail-header">
        <button class="btn-ghost wsh-btn-sm" onclick="_wsHealthRenderOverview()">← Back</button>
        <span class="wsh-health-detail-title">${esc(ws.name)}</span>
        <button class="btn-ghost wsh-btn-sm" onclick="_wsHealthRefreshDetail('${wsId}')">↺ Refresh</button>
      </div>

      <!-- Overall score ring -->
      <div class="wsh-health-overall-row">
        ${_wsHealthRing(health.overall, health.gradeColor, 72)}
        <div class="wsh-health-overall-info">
          <span class="wsh-health-overall-score" style="color:${health.gradeColor}">${health.overall}<span class="wsh-health-overall-unit">/100</span></span>
          <span class="wsh-health-grade-chip" style="--grade-color:${health.gradeColor}">${health.grade}</span>
          <span class="wsh-health-overall-hint">${_wsHealthGradeHint(health.grade)}</span>
        </div>
      </div>

      <!-- Per-metric breakdown -->
      <div class="wsh-health-metrics-list">
        ${health.metrics.map(m => `
          <div class="wsh-health-metric-row">
            <span class="wsh-health-metric-icon">${m.icon}</span>
            <div class="wsh-health-metric-body">
              <div class="wsh-health-metric-top">
                <span class="wsh-health-metric-label">${m.label}</span>
                <span class="wsh-health-metric-pct" style="color:${_wsHealthMetricColor(m.pct)}">${m.pct}%</span>
              </div>
              <div class="wsh-health-bar-track">
                <div class="wsh-health-bar-fill" style="width:${m.pct}%;background:${_wsHealthMetricColor(m.pct)}"></div>
              </div>
              <span class="wsh-health-metric-weight">Weight: ${Math.round(m.weight * 100)}%</span>
            </div>
          </div>`).join('')}
      </div>

      <!-- Suggestions -->
      ${health.suggestions.length > 0 ? `
      <div class="wsh-health-suggestions">
        <div class="wsh-health-sugg-title">💡 Improvement Suggestions</div>
        ${health.suggestions.map(s => `
          <div class="wsh-health-sugg-item">
            <span class="wsh-health-sugg-dot"></span>
            <span>${esc(s)}</span>
          </div>`).join('')}
      </div>` : `
      <div class="wsh-health-suggestions wsh-health-sugg-all-ok">
        <span>✅ This workspace is in great shape — no suggestions.</span>
      </div>`}
    </div>`;
}

function _wsHealthRefreshDetail(wsId) {
  _wsHealthRenderDetail(wsId);
  showToast('Health score refreshed.');
}

/* ──────────────────────────────────────────────
   SVG Ring Helper
────────────────────────────────────────────── */

function _wsHealthRing(score, color, size) {
  const r   = 15.9;
  const pct = Math.round(score);
  return `
    <div class="wsh-health-ring-wrap" style="width:${size}px;height:${size}px">
      <svg viewBox="0 0 36 36" class="wsh-health-ring" aria-label="Health score ${pct}%">
        <circle class="wsh-health-ring-bg" cx="18" cy="18" r="${r}" />
        <circle class="wsh-health-ring-fill" cx="18" cy="18" r="${r}"
          stroke="${color}"
          stroke-dasharray="${pct} ${100 - pct}"
          stroke-dashoffset="25" />
      </svg>
      <span class="wsh-health-ring-label" style="color:${color};font-size:${size < 50 ? '.65rem' : '.85rem'}">${pct}</span>
    </div>`;
}

/* ──────────────────────────────────────────────
   Utility
────────────────────────────────────────────── */

function _wsHealthMetricColor(pct) {
  if (pct >= 70) return '#4ade80';
  if (pct >= 40) return '#f0b429';
  return '#e23270';
}

function _wsHealthGradeHint(grade) {
  return {
    Excellent: 'This workspace is well-maintained and actively used.',
    Good:      'This workspace is in good shape with minor room for improvement.',
    Fair:      'Some areas need attention to keep this workspace healthy.',
    Poor:      'This workspace needs significant improvement.',
  }[grade] || '';
}
