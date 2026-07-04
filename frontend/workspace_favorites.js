/**
 * KalaOS — Favorite Workspace System  (#40)
 *
 * Lets users star/unstar workspaces. Favorites are persisted in localStorage,
 * surfaced in a dedicated panel, and shown first in the active workspace list.
 *
 * localStorage key: 'kala-ws-favorites'  →  { [wsId]: timestamp }
 */

/* ──────────────────────────────────────────────
   Storage
────────────────────────────────────────────── */

const _WSF_KEY = 'kala-ws-favorites';

function _wsfLoad() {
  try { return JSON.parse(localStorage.getItem(_WSF_KEY) || '{}'); }
  catch { return {}; }
}

function _wsfSave(favs) {
  localStorage.setItem(_WSF_KEY, JSON.stringify(favs));
}

/* ──────────────────────────────────────────────
   Public API
────────────────────────────────────────────── */

/**
 * Toggle favorite status for a workspace.
 * @param {string} wsId
 * @returns {boolean}  true = now favorited, false = unfavorited
 */
function wsfToggle(wsId) {
  const favs = _wsfLoad();
  if (favs[wsId]) {
    delete favs[wsId];
    _wsfSave(favs);
    return false;
  }
  favs[wsId] = Date.now();
  _wsfSave(favs);
  return true;
}

/**
 * Return whether a workspace is currently favorited.
 * @param {string} wsId
 * @returns {boolean}
 */
function wsfIsFav(wsId) {
  return !!_wsfLoad()[wsId];
}

/**
 * Return all favorited workspace ids sorted by when they were favorited (newest first).
 * @returns {string[]}
 */
function wsfGetAll() {
  const favs = _wsfLoad();
  return Object.entries(favs)
    .sort((a, b) => b[1] - a[1])
    .map(([id]) => id);
}

/* ──────────────────────────────────────────────
   UI State
────────────────────────────────────────────── */

let _wsfSortByFav = false; // toggled by the sort button in the sharing panel

function openWorkspaceFavorites() {
  const panel = document.getElementById('wsfPanel');
  if (!panel) return;
  _wsfRender();
  panel.classList.remove('hidden');
}

function closeWorkspaceFavorites() {
  document.getElementById('wsfPanel')?.classList.add('hidden');
}

/* ──────────────────────────────────────────────
   Favorites Panel Rendering
────────────────────────────────────────────── */

function _wsfRender() {
  const container = document.getElementById('wsfContent');
  if (!container) return;

  const favIds = wsfGetAll();
  const email  = typeof _wshCurrentUserEmail === 'function' ? _wshCurrentUserEmail() : null;
  const all    = typeof _wshLoad === 'function' ? _wshLoad() : [];

  // Resolve favorited workspaces the user is still a member of
  const favWorkspaces = favIds
    .map(id => all.find(w => w.id === id))
    .filter(ws => ws && email && ws.members.some(m => m.email === email));

  if (favWorkspaces.length === 0) {
    container.innerHTML = `
      <div class="wsf-empty">
        <span class="wsf-empty-icon">⭐</span>
        <p>No favorite workspaces yet.</p>
        <p class="wsf-empty-hint">Click the ⭐ star on any workspace in the Sharing panel to add it here.</p>
      </div>`;
    return;
  }

  container.innerHTML = `
    <div class="wsf-list">
      ${favWorkspaces.map(ws => _wsfCardHtml(ws)).join('')}
    </div>`;
}

function _wsfCardHtml(ws) {
  const myRole   = typeof _wshMyRole === 'function' ? _wshMyRole(ws) : null;
  const roleInfo = (typeof _WSH_ROLES !== 'undefined' && myRole) ? (_WSH_ROLES[myRole] || {}) : {};
  const archived = ws.archivedAt
    ? `<span class="wsf-archived-badge">🗄️ Archived</span>` : '';
  const favTs    = _wsfLoad()[ws.id];
  const favDate  = favTs
    ? `Starred ${new Date(favTs).toLocaleDateString(undefined,{month:'short',day:'numeric'})}` : '';

  return `
    <div class="wsf-card" id="wsf-card-${ws.id}">
      <div class="wsf-card-main" onclick="_wsfOpenWorkspace('${ws.id}')" style="cursor:pointer;flex:1">
        <div class="wsf-card-name-row">
          <span class="wsf-card-name">${esc(ws.name)}</span>
          ${archived}
          ${roleInfo.label ? `<span class="wsf-role-badge wsh-role-${myRole}">${roleInfo.icon || ''} ${roleInfo.label}</span>` : ''}
        </div>
        <span class="wsf-card-meta">
          ${ws.members.length} member${ws.members.length !== 1 ? 's' : ''}
          ${favDate ? `· ${favDate}` : ''}
        </span>
      </div>
      <button class="wsf-star-btn wsf-star-active"
              onclick="_wsfToggleFromPanel('${ws.id}')"
              title="Remove from favorites"
              aria-label="Remove from favorites">⭐</button>
    </div>`;
}

function _wsfToggleFromPanel(wsId) {
  wsfToggle(wsId);
  _wsfRender();
  // Refresh sharing panel list if open
  if (typeof _wshRenderWorkspaceList === 'function') {
    const wshContent = document.getElementById('wshContent');
    if (wshContent && wshContent.innerHTML) _wshRenderWorkspaceList();
  }
  showToast(wsfIsFav(wsId) ? '⭐ Added to favorites.' : 'Removed from favorites.');
}

function _wsfOpenWorkspace(wsId) {
  closeWorkspaceFavorites();
  if (typeof openWorkspaceSharing === 'function') {
    openWorkspaceSharing();
    setTimeout(() => {
      if (typeof _wshOpenWorkspace === 'function') _wshOpenWorkspace(wsId);
    }, 50);
  }
}

/* ──────────────────────────────────────────────
   Patch workspace_sharing.js list rendering
   — injects star buttons + favorites-first sort
────────────────────────────────────────────── */

document.addEventListener('DOMContentLoaded', () => {
  setTimeout(_wsfPatchSharing, 300);
});

function _wsfPatchSharing() {
  if (typeof _wshRenderWorkspaceList !== 'function') return;
  if (_wshRenderWorkspaceList._wsfPatched) return;

  const _origRender = _wshRenderWorkspaceList;

  window._wshRenderWorkspaceList = function() {
    _origRender();
    _wsfInjectStars();
    _wsfInjectSortBtn();
  };
  window._wshRenderWorkspaceList._wsfPatched = true;

  // Also patch _wshRenderDetail to inject star in detail header
  if (typeof _wshRenderDetail === 'function' && !_wshRenderDetail._wsfPatched) {
    const _origDetail = _wshRenderDetail;
    window._wshRenderDetail = function(ws) {
      _origDetail(ws);
      _wsfInjectDetailStar(ws.id);
    };
    window._wshRenderDetail._wsfPatched = true;
  }
}

/**
 * Inject a star toggle button into every active workspace card rendered by
 * _wshRenderWorkspaceList. Cards have id="wsh-card-{wsId}".
 */
function _wsfInjectStars() {
  document.querySelectorAll('[id^="wsh-card-"]').forEach(card => {
    const wsId = card.id.replace('wsh-card-', '');
    if (card.querySelector('.wsf-star-btn')) return; // already injected
    const isFav = wsfIsFav(wsId);
    const btn = document.createElement('button');
    btn.className = `wsf-star-btn${isFav ? ' wsf-star-active' : ''}`;
    btn.title = isFav ? 'Remove from favorites' : 'Add to favorites';
    btn.setAttribute('aria-label', btn.title);
    btn.setAttribute('aria-pressed', String(isFav));
    btn.textContent = isFav ? '⭐' : '☆';
    btn.onclick = (e) => {
      e.stopPropagation();
      const nowFav = wsfToggle(wsId);
      btn.textContent = nowFav ? '⭐' : '☆';
      btn.className = `wsf-star-btn${nowFav ? ' wsf-star-active' : ''}`;
      btn.title = nowFav ? 'Remove from favorites' : 'Add to favorites';
      btn.setAttribute('aria-pressed', String(nowFav));
      showToast(nowFav ? '⭐ Added to favorites.' : 'Removed from favorites.');
    };
    // Insert before the first action button in the card
    const actions = card.querySelector('.wsh-ws-card-actions');
    if (actions) actions.prepend(btn);
    else card.appendChild(btn);
  });

  // If sort-by-favorites is active, reorder cards in the DOM
  if (_wsfSortByFav) _wsfSortCards();
}

/**
 * Inject a star button into the workspace detail header.
 */
function _wsfInjectDetailStar(wsId) {
  const header = document.querySelector('.wsh-section-header');
  if (!header || header.querySelector('.wsf-star-btn')) return;
  const isFav = wsfIsFav(wsId);
  const btn = document.createElement('button');
  btn.className = `wsf-star-btn wsf-star-detail${isFav ? ' wsf-star-active' : ''}`;
  btn.title = isFav ? 'Remove from favorites' : 'Add to favorites';
  btn.setAttribute('aria-label', btn.title);
  btn.setAttribute('aria-pressed', String(isFav));
  btn.textContent = isFav ? '⭐' : '☆';
  btn.onclick = () => {
    const nowFav = wsfToggle(wsId);
    btn.textContent = nowFav ? '⭐' : '☆';
    btn.className = `wsf-star-btn wsf-star-detail${nowFav ? ' wsf-star-active' : ''}`;
    btn.title = nowFav ? 'Remove from favorites' : 'Add to favorites';
    btn.setAttribute('aria-pressed', String(nowFav));
    showToast(nowFav ? '⭐ Added to favorites.' : 'Removed from favorites.');
  };
  // Append after the title span
  const title = header.querySelector('.wsh-section-title');
  if (title) title.after(btn);
  else header.appendChild(btn);
}

/**
 * Inject a "Sort by Favorites" toggle button into the workspace list header.
 */
function _wsfInjectSortBtn() {
  const header = document.querySelector('.wsh-section-header');
  if (!header || header.querySelector('.wsf-sort-btn')) return;
  const btn = document.createElement('button');
  btn.className = `btn-ghost wsh-btn-sm wsf-sort-btn${_wsfSortByFav ? ' wsf-sort-active' : ''}`;
  btn.title = 'Sort favorites first';
  btn.textContent = _wsfSortByFav ? '⭐ Sorted' : '☆ Sort by Fav';
  btn.onclick = () => {
    _wsfSortByFav = !_wsfSortByFav;
    btn.textContent = _wsfSortByFav ? '⭐ Sorted' : '☆ Sort by Fav';
    btn.classList.toggle('wsf-sort-active', _wsfSortByFav);
    _wsfSortCards();
    showToast(_wsfSortByFav ? 'Favorites shown first.' : 'Default sort restored.');
  };
  header.appendChild(btn);
}

/**
 * Reorder workspace cards in the DOM: favorited cards float to the top.
 */
function _wsfSortCards() {
  const container = document.querySelector('#wshContent .wsh-section');
  if (!container) return;
  const cards = [...container.querySelectorAll('[id^="wsh-card-"]')];
  if (cards.length < 2) return;

  const favIds = new Set(wsfGetAll());
  const favCards   = cards.filter(c => favIds.has(c.id.replace('wsh-card-', '')));
  const otherCards = cards.filter(c => !favIds.has(c.id.replace('wsh-card-', '')));

  // Add visual separator if there are both fav and non-fav cards
  const sep = container.querySelector('.wsf-sep');
  if (sep) sep.remove();

  [...favCards, ...otherCards].forEach(card => container.appendChild(card));

  if (_wsfSortByFav && favCards.length > 0 && otherCards.length > 0) {
    const divider = document.createElement('div');
    divider.className = 'wsf-sep';
    divider.textContent = 'Other workspaces';
    otherCards[0].before(divider);
  }
}
