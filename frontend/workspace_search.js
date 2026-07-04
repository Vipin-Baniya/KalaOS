/**
 * KalaOS — Global Workspace Search  (#42)
 *
 * Searches all workspaces the current user is a member of by name, tags, and
 * description. Results are highlighted and keyboard-navigable.
 *
 * Keyboard shortcut: Ctrl+K (or Cmd+K on Mac) opens the search panel.
 * localStorage key: none — purely reads from 'kala-workspaces'.
 */

/* ──────────────────────────────────────────────
   Search Logic
────────────────────────────────────────────── */

/**
 * Search all accessible workspaces (active + archived) by name, tags, and description.
 * Returns matches with a `highlights` map for each matched field.
 * @param {string} query
 * @returns {object[]}  workspace objects extended with { highlights: { name, tags, description } }
 */
function wshSearchWorkspaces(query) {
  const q = (query || '').trim().toLowerCase();
  if (!q) return [];

  const email = _wshCurrentUserEmail();
  if (!email) return [];

  const all = _wshLoad().filter(ws => ws.members.some(m => m.email === email));

  return all
    .map(ws => {
      const nameMatch  = (ws.name        || '').toLowerCase().includes(q);
      const descMatch  = (ws.description || '').toLowerCase().includes(q);
      const tagsMatch  = Array.isArray(ws.tags) && ws.tags.some(t => t.toLowerCase().includes(q));

      if (!nameMatch && !descMatch && !tagsMatch) return null;

      return {
        ...ws,
        highlights: {
          name:        nameMatch  ? _wsHighlight(ws.name, q)        : esc(ws.name),
          description: descMatch  ? _wsHighlight(ws.description, q) : null,
          tags:        tagsMatch  ? ws.tags.filter(t => t.toLowerCase().includes(q)) : [],
        },
      };
    })
    .filter(Boolean);
}

/**
 * Wrap every occurrence of `term` in `text` with a <mark> span.
 * @param {string} text
 * @param {string} term  — already lowercased
 * @returns {string}  HTML string
 */
function _wsHighlight(text, term) {
  if (!text) return '';
  const escaped = esc(text);
  const re = new RegExp(`(${term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
  return escaped.replace(re, '<mark class="wss-mark">$1</mark>');
}

/* ──────────────────────────────────────────────
   UI State
────────────────────────────────────────────── */

let _wssQuery          = '';
let _wssSelectedIndex  = -1;

function openWorkspaceSearch() {
  const panel = document.getElementById('wssPanel');
  if (!panel) return;
  panel.classList.remove('hidden');
  const input = document.getElementById('wssInput');
  if (input) { input.value = ''; input.focus(); }
  _wssQuery         = '';
  _wssSelectedIndex = -1;
  _wssRenderResults([]);
}

function closeWorkspaceSearch() {
  document.getElementById('wssPanel')?.classList.add('hidden');
}

/* ──────────────────────────────────────────────
   Rendering
────────────────────────────────────────────── */

function _wssOnInput(value) {
  _wssQuery         = value;
  _wssSelectedIndex = -1;
  const results = wshSearchWorkspaces(value);
  _wssRenderResults(results);
}

function _wssRenderResults(results) {
  const list = document.getElementById('wssList');
  if (!list) return;

  if (!_wssQuery.trim()) {
    list.innerHTML = `<p class="wss-hint">Type to search workspaces by name, tags, or description.</p>`;
    return;
  }

  if (results.length === 0) {
    list.innerHTML = `<p class="wss-empty">No workspaces match <strong>${esc(_wssQuery)}</strong>.</p>`;
    return;
  }

  list.innerHTML = results.map((ws, i) => {
    const roleInfo  = _WSH_ROLES[_wshMyRole(ws)] || {};
    const archived  = ws.archivedAt ? `<span class="wss-archived-badge">🗄️ Archived</span>` : '';
    const descHtml  = ws.highlights.description
      ? `<span class="wss-desc">${ws.highlights.description}</span>` : '';
    const tagsHtml  = ws.highlights.tags.length
      ? ws.highlights.tags.map(t => `<span class="wss-tag">${esc(t)}</span>`).join('') : '';

    return `
      <div class="wss-result${i === _wssSelectedIndex ? ' wss-result-selected' : ''}"
           id="wss-result-${i}"
           onclick="_wssOpenResult('${ws.id}')"
           onmouseenter="_wssSetSelected(${i})">
        <div class="wss-result-main">
          <span class="wss-result-name">${ws.highlights.name}</span>
          ${archived}
          <span class="wss-role-badge wsh-role-${_wshMyRole(ws)}">${roleInfo.icon || ''} ${roleInfo.label || ''}</span>
        </div>
        ${descHtml}
        ${tagsHtml ? `<div class="wss-tags">${tagsHtml}</div>` : ''}
        <span class="wss-meta">${ws.members.length} member${ws.members.length !== 1 ? 's' : ''} · Created ${_wshFormatDate(ws.createdAt)}</span>
      </div>`;
  }).join('');
}

function _wssSetSelected(index) {
  _wssSelectedIndex = index;
  document.querySelectorAll('.wss-result').forEach((el, i) => {
    el.classList.toggle('wss-result-selected', i === index);
  });
}

function _wssOpenResult(wsId) {
  closeWorkspaceSearch();
  // Open the workspace in the sharing panel
  if (typeof openWorkspaceSharing === 'function') {
    openWorkspaceSharing();
    setTimeout(() => {
      if (typeof _wshOpenWorkspace === 'function') _wshOpenWorkspace(wsId);
    }, 50);
  }
}

/* ──────────────────────────────────────────────
   Keyboard Navigation
────────────────────────────────────────────── */

function _wssOnKeydown(e) {
  const results = document.querySelectorAll('.wss-result');
  if (!results.length) return;

  if (e.key === 'ArrowDown') {
    e.preventDefault();
    _wssSetSelected(Math.min(_wssSelectedIndex + 1, results.length - 1));
    results[_wssSelectedIndex]?.scrollIntoView({ block: 'nearest' });
  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    _wssSetSelected(Math.max(_wssSelectedIndex - 1, 0));
    results[_wssSelectedIndex]?.scrollIntoView({ block: 'nearest' });
  } else if (e.key === 'Enter' && _wssSelectedIndex >= 0) {
    e.preventDefault();
    results[_wssSelectedIndex]?.click();
  } else if (e.key === 'Escape') {
    closeWorkspaceSearch();
  }
}

/* ──────────────────────────────────────────────
   Global Ctrl+K / Cmd+K shortcut
────────────────────────────────────────────── */

document.addEventListener('keydown', e => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault();
    const panel = document.getElementById('wssPanel');
    if (panel && !panel.classList.contains('hidden')) {
      closeWorkspaceSearch();
    } else {
      openWorkspaceSearch();
    }
  }
});
