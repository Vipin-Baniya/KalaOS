/**
 * KalaOS — AI-Based Workspace Suggestions
 *
 * Tracks studio usage patterns and recommends layout/productivity improvements.
 * All data is stored locally in localStorage — nothing is sent to any server.
 */

/* ──────────────────────────────────────────────
   Usage Tracking
────────────────────────────────────────────── */

const _WS_STORAGE_KEY = 'kala-workspace-usage';
const _WS_MAX_EVENTS  = 200;

function _wsLoadUsage() {
  try { return JSON.parse(localStorage.getItem(_WS_STORAGE_KEY) || '{}'); }
  catch { return {}; }
}

function _wsSaveUsage(data) {
  localStorage.setItem(_WS_STORAGE_KEY, JSON.stringify(data));
}

/**
 * Record a studio visit. Call this whenever the user switches studios.
 * @param {string} studio  e.g. "text", "music", "visual"
 */
function wsTrackStudioVisit(studio) {
  const data = _wsLoadUsage();
  if (!data.visits) data.visits = [];
  data.visits.push({ studio, ts: Date.now() });
  if (data.visits.length > _WS_MAX_EVENTS) data.visits.shift();
  _wsSaveUsage(data);
}

/* ──────────────────────────────────────────────
   Suggestion Engine
────────────────────────────────────────────── */

const _ALL_STUDIOS = [
  'text', 'music', 'visual', 'animation', 'video',
  'chat', 'feed', 'dms', 'profile', 'collab', 'stream', 'export', 'platform-connect',
];

function _wsComputeFrequency(visits) {
  const freq = {};
  _ALL_STUDIOS.forEach(s => { freq[s] = 0; });
  (visits || []).forEach(v => { if (freq[v.studio] !== undefined) freq[v.studio]++; });
  return freq;
}

function _wsTopStudios(freq, n) {
  return Object.entries(freq)
    .sort((a, b) => b[1] - a[1])
    .filter(([, count]) => count > 0)
    .slice(0, n)
    .map(([studio]) => studio);
}

function _wsUnusedStudios(freq) {
  return _ALL_STUDIOS.filter(s => freq[s] === 0);
}

/**
 * Generate an array of suggestion objects based on usage data.
 * Each suggestion: { id, icon, title, description, action, actionLabel }
 */
function wsGenerateSuggestions() {
  const data    = _wsLoadUsage();
  const visits  = data.visits || [];
  const freq    = _wsComputeFrequency(visits);
  const top     = _wsTopStudios(freq, 3);
  const unused  = _wsUnusedStudios(freq);
  const total   = visits.length;
  const suggestions = [];

  // 1. Frequently used tools — recommend pinning them
  if (top.length >= 2) {
    suggestions.push({
      id: 'pin-top-studios',
      icon: '📌',
      title: `You use ${_wsStudioLabel(top[0])} & ${_wsStudioLabel(top[1])} most`,
      description: `These are your go-to studios. Consider keeping them at the top of your sidebar for faster access.`,
      action: () => _wsHighlightStudios(top.slice(0, 2)),
      actionLabel: 'Highlight in sidebar',
    });
  }

  // 2. Unused studios — suggest removal or hiding
  if (unused.length >= 3) {
    const sample = unused.slice(0, 3).map(_wsStudioLabel).join(', ');
    suggestions.push({
      id: 'hide-unused',
      icon: '🧹',
      title: 'Unused studios detected',
      description: `You haven't visited ${sample} yet. Hide them to reduce sidebar clutter.`,
      action: () => _wsHideUnusedStudios(unused.slice(0, 3)),
      actionLabel: 'Hide unused studios',
    });
  }

  // 3. Productivity tip — keyboard shortcut
  if (total >= 5) {
    suggestions.push({
      id: 'keyboard-shortcut',
      icon: '⌨️',
      title: 'Speed up analysis',
      description: 'Press Ctrl+Enter (or ⌘+Enter on Mac) in the Text Studio to run a deep analysis without reaching for the mouse.',
      action: () => _wsSwitchTo('text'),
      actionLabel: 'Open Text Studio',
    });
  }

  // 4. Music + Text combo tip
  if (freq['text'] > 0 && freq['music'] === 0) {
    suggestions.push({
      id: 'try-music',
      icon: '🎵',
      title: 'Turn your lyrics into music',
      description: 'You write in the Text Studio — try the Music Studio to generate beat patterns and production plans from your lyrics.',
      action: () => _wsSwitchTo('music'),
      actionLabel: 'Open Music Studio',
    });
  }

  // 5. Visual + Text combo tip
  if (freq['text'] > 0 && freq['visual'] === 0) {
    suggestions.push({
      id: 'try-visual',
      icon: '🎨',
      title: 'Visualise your art',
      description: 'Pair your text work with the Visual Studio to create cover art, logos, or mood boards.',
      action: () => _wsSwitchTo('visual'),
      actionLabel: 'Open Visual Studio',
    });
  }

  // 6. Collab tip for active users
  if (total >= 10 && freq['collab'] === 0) {
    suggestions.push({
      id: 'try-collab',
      icon: '🤝',
      title: 'Collaborate with others',
      description: 'You\'re an active creator! The Collaboration Studio lets you co-create and share projects with other artists.',
      action: () => _wsSwitchTo('collab'),
      actionLabel: 'Open Collab Studio',
    });
  }

  // 7. Export tip
  if ((freq['text'] + freq['music'] + freq['visual']) >= 5 && freq['export'] === 0) {
    suggestions.push({
      id: 'try-export',
      icon: '📦',
      title: 'Export your work',
      description: 'You\'ve been creating — use the Export Studio to package and share your projects.',
      action: () => _wsSwitchTo('export'),
      actionLabel: 'Open Export Studio',
    });
  }

  // 8. Default tip when no data yet
  if (suggestions.length === 0) {
    suggestions.push({
      id: 'get-started',
      icon: '✨',
      title: 'Start exploring KalaOS',
      description: 'Visit a few studios and come back here — Kala will learn your habits and suggest personalised workspace improvements.',
      action: () => _wsSwitchTo('text'),
      actionLabel: 'Open Text Studio',
    });
  }

  return suggestions;
}

/* ──────────────────────────────────────────────
   Helpers
────────────────────────────────────────────── */

const _STUDIO_LABELS = {
  text: 'Text Studio', music: 'Music Studio', visual: 'Visual Studio',
  animation: 'Animation Studio', video: 'Video Studio', chat: 'Kala Chat',
  feed: 'Feed', dms: 'Messages', profile: 'Profile', collab: 'Collab Studio',
  stream: 'Stream Studio', export: 'Export Studio', 'platform-connect': 'Platform Connect',
};

function _wsStudioLabel(studio) {
  return _STUDIO_LABELS[studio] || studio;
}

function _wsSwitchTo(studio) {
  if (typeof switchStudio === 'function') switchStudio(studio);
}

function _wsHighlightStudios(studios) {
  studios.forEach(s => {
    const btnId = s.replace('-', '') + 'StudioBtn';
    const btn = document.getElementById(btnId) ||
                document.getElementById(s + 'StudioBtn');
    if (btn) {
      btn.style.transition = 'box-shadow .3s';
      btn.style.boxShadow = '0 0 0 3px var(--accent)';
      setTimeout(() => { btn.style.boxShadow = ''; }, 2500);
    }
  });
  showToast('Studios highlighted in the sidebar.');
}

function _wsHideUnusedStudios(studios) {
  studios.forEach(s => {
    const btnId = s.replace('-', '') + 'StudioBtn';
    const btn = document.getElementById(btnId) ||
                document.getElementById(s + 'StudioBtn');
    if (btn) btn.style.display = 'none';
  });
  showToast(`${studios.length} unused studios hidden. Refresh to restore.`);
}

/* ──────────────────────────────────────────────
   UI — Suggestions Panel
────────────────────────────────────────────── */

function openWorkspaceSuggestions() {
  const panel = document.getElementById('wsSuggestionsPanel');
  if (!panel) return;
  _wsRenderSuggestions();
  panel.classList.remove('hidden');
}

function closeWorkspaceSuggestions() {
  const panel = document.getElementById('wsSuggestionsPanel');
  if (panel) panel.classList.add('hidden');
}

function _wsRenderSuggestions() {
  const list = document.getElementById('wsSuggestionsList');
  if (!list) return;

  const suggestions = wsGenerateSuggestions();
  const dismissed   = JSON.parse(localStorage.getItem('kala-ws-dismissed') || '[]');
  const visible     = suggestions.filter(s => !dismissed.includes(s.id));

  if (visible.length === 0) {
    list.innerHTML = `
      <div class="ws-suggestions-empty">
        <span style="font-size:2rem">🎉</span>
        <p>All suggestions applied or dismissed. Keep creating!</p>
      </div>`;
    return;
  }

  list.innerHTML = visible.map(s => `
    <div class="ws-suggestion-card" id="ws-card-${s.id}">
      <div class="ws-suggestion-header">
        <span class="ws-suggestion-icon" aria-hidden="true">${s.icon}</span>
        <span class="ws-suggestion-title">${esc(s.title)}</span>
        <button class="ws-dismiss-btn" onclick="wsDismiss('${s.id}')" title="Dismiss" aria-label="Dismiss suggestion">✕</button>
      </div>
      <p class="ws-suggestion-desc">${esc(s.description)}</p>
      <button class="btn-primary ws-apply-btn" onclick="wsApply('${s.id}')">${esc(s.actionLabel)}</button>
    </div>
  `).join('');
}

function wsApply(id) {
  const suggestions = wsGenerateSuggestions();
  const s = suggestions.find(x => x.id === id);
  if (s && typeof s.action === 'function') {
    s.action();
    wsDismiss(id);
  }
}

function wsDismiss(id) {
  const dismissed = JSON.parse(localStorage.getItem('kala-ws-dismissed') || '[]');
  if (!dismissed.includes(id)) dismissed.push(id);
  localStorage.setItem('kala-ws-dismissed', JSON.stringify(dismissed));
  const card = document.getElementById(`ws-card-${id}`);
  if (card) {
    card.style.opacity = '0';
    card.style.transform = 'translateX(20px)';
    card.style.transition = 'opacity .2s, transform .2s';
    setTimeout(() => { card.remove(); _wsCheckEmpty(); }, 220);
  }
}

function _wsCheckEmpty() {
  const list = document.getElementById('wsSuggestionsList');
  if (list && list.children.length === 0) {
    list.innerHTML = `
      <div class="ws-suggestions-empty">
        <span style="font-size:2rem">🎉</span>
        <p>All suggestions applied or dismissed. Keep creating!</p>
      </div>`;
  }
}

function wsResetDismissed() {
  localStorage.removeItem('kala-ws-dismissed');
  _wsRenderSuggestions();
}

/* ──────────────────────────────────────────────
   Hook into switchStudio for tracking
────────────────────────────────────────────── */

document.addEventListener('DOMContentLoaded', () => {
  // Patch switchStudio to track visits
  if (typeof switchStudio === 'function') {
    const _origSwitch = switchStudio;
    switchStudio = function(mode) {
      wsTrackStudioVisit(mode);
      _origSwitch(mode);
    };
  }
});
