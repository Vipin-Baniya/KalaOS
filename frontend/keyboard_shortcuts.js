/**
 * KalaOS — Custom Keyboard Shortcut Management
 *
 * Allows users to view, edit, and reset keyboard shortcuts.
 * Preferences are saved to localStorage under 'kala-shortcuts'.
 */

/* ──────────────────────────────────────────────
   Default Shortcut Registry
────────────────────────────────────────────── */

const _KS_STORAGE_KEY = 'kala-shortcuts';

const _KS_DEFAULTS = [
  { id: 'studio-text',      label: 'Open Text Studio',     category: 'Navigation', key: 'T', ctrl: true, shift: false, action: () => switchStudio('text') },
  { id: 'studio-music',     label: 'Open Music Studio',    category: 'Navigation', key: 'M', ctrl: true, shift: false, action: () => switchStudio('music') },
  { id: 'studio-visual',    label: 'Open Visual Studio',   category: 'Navigation', key: 'U', ctrl: true, shift: false, action: () => switchStudio('visual') },
  { id: 'studio-dashboard', label: 'Go to Dashboard',      category: 'Navigation', key: 'D', ctrl: true, shift: false, action: () => switchStudio('dashboard') },
  { id: 'studio-chat',      label: 'Open Kala Chat',       category: 'Navigation', key: 'K', ctrl: true, shift: false, action: () => switchStudio('chat') },
  { id: 'run-analysis',     label: 'Run Deep Analysis',    category: 'Actions',    key: 'Enter', ctrl: true, shift: false, action: () => { if (typeof runDeepAnalysis === 'function') runDeepAnalysis(); } },
  { id: 'toggle-theme',     label: 'Open Theme Panel',     category: 'UI',         key: 'P', ctrl: true, shift: false, action: () => { if (typeof toggleThemePanel === 'function') toggleThemePanel(); } },
  { id: 'toggle-sidebar',   label: 'Toggle Sidebar',       category: 'UI',         key: 'B', ctrl: true, shift: false, action: () => { if (typeof toggleSidebar === 'function') toggleSidebar(); } },
  { id: 'open-shortcuts',   label: 'Open Shortcut Manager',category: 'UI',         key: '/', ctrl: true, shift: false, action: () => openShortcutManager() },
  { id: 'ai-suggestions',   label: 'AI Workspace Suggestions', category: 'UI',    key: 'I', ctrl: true, shift: false, action: () => { if (typeof openWorkspaceSuggestions === 'function') openWorkspaceSuggestions(); } },
];

/* ──────────────────────────────────────────────
   Storage
────────────────────────────────────────────── */

function _ksLoad() {
  try {
    const saved = JSON.parse(localStorage.getItem(_KS_STORAGE_KEY) || '{}');
    // Merge saved overrides onto defaults
    return _KS_DEFAULTS.map(def => {
      const override = saved[def.id];
      return override ? { ...def, ...override } : { ...def };
    });
  } catch {
    return _KS_DEFAULTS.map(d => ({ ...d }));
  }
}

function _ksSave(shortcuts) {
  const overrides = {};
  shortcuts.forEach(s => {
    const def = _KS_DEFAULTS.find(d => d.id === s.id);
    if (def && (s.key !== def.key || s.ctrl !== def.ctrl || s.shift !== def.shift)) {
      overrides[s.id] = { key: s.key, ctrl: s.ctrl, shift: s.shift };
    }
  });
  localStorage.setItem(_KS_STORAGE_KEY, JSON.stringify(overrides));
}

/* ──────────────────────────────────────────────
   Conflict Detection
────────────────────────────────────────────── */

function _ksConflicts(shortcuts, targetId, key, ctrl, shift) {
  return shortcuts.filter(s =>
    s.id !== targetId &&
    s.key.toUpperCase() === key.toUpperCase() &&
    s.ctrl === ctrl &&
    s.shift === shift
  );
}

/* ──────────────────────────────────────────────
   Global keydown listener
────────────────────────────────────────────── */

document.addEventListener('keydown', function (e) {
  // Don't fire shortcuts when typing in inputs/textareas
  const tag = (e.target.tagName || '').toLowerCase();
  if (tag === 'input' || tag === 'textarea' || tag === 'select') return;
  // Don't fire if a modal is open (except the shortcut manager itself)
  const shortcuts = _ksLoad();
  for (const s of shortcuts) {
    if (
      s.key.toUpperCase() === e.key.toUpperCase() &&
      s.ctrl === (e.ctrlKey || e.metaKey) &&
      s.shift === e.shiftKey
    ) {
      // Skip if shortcut manager is open and it's not the open-shortcuts shortcut
      const panel = document.getElementById('ksPanel');
      if (panel && !panel.classList.contains('hidden') && s.id !== 'open-shortcuts') return;
      e.preventDefault();
      if (typeof s.action === 'function') s.action();
      return;
    }
  }
});

/* ──────────────────────────────────────────────
   UI State
────────────────────────────────────────────── */

let _ksEditingId = null;   // id of shortcut currently being recorded
let _ksShortcuts = null;   // working copy during edit session

function openShortcutManager() {
  const panel = document.getElementById('ksPanel');
  if (!panel) return;
  _ksShortcuts = _ksLoad();
  _ksRender();
  panel.classList.remove('hidden');
}

function closeShortcutManager() {
  const panel = document.getElementById('ksPanel');
  if (panel) panel.classList.add('hidden');
  _ksEditingId = null;
}

/* ──────────────────────────────────────────────
   Rendering
────────────────────────────────────────────── */

function _ksFormatCombo(s) {
  const parts = [];
  if (s.ctrl)  parts.push(navigator.platform.includes('Mac') ? '⌘' : 'Ctrl');
  if (s.shift) parts.push('Shift');
  parts.push(s.key === ' ' ? 'Space' : s.key.toUpperCase());
  return parts.join(' + ');
}

function _ksRender() {
  const list = document.getElementById('ksShortcutList');
  if (!list || !_ksShortcuts) return;

  const categories = [...new Set(_ksShortcuts.map(s => s.category))];

  list.innerHTML = categories.map(cat => {
    const items = _ksShortcuts.filter(s => s.category === cat);
    return `
      <div class="ks-category">
        <div class="ks-category-label">${esc(cat)}</div>
        ${items.map(s => {
          const isEditing = _ksEditingId === s.id;
          const conflicts = _ksConflicts(_ksShortcuts, s.id, s.key, s.ctrl, s.shift);
          const hasConflict = conflicts.length > 0;
          const def = _KS_DEFAULTS.find(d => d.id === s.id);
          const isModified = def && (s.key !== def.key || s.ctrl !== def.ctrl || s.shift !== def.shift);
          return `
            <div class="ks-row${hasConflict ? ' ks-conflict' : ''}${isEditing ? ' ks-editing' : ''}" id="ks-row-${s.id}">
              <span class="ks-label">${esc(s.label)}</span>
              <div class="ks-combo-wrap">
                ${isEditing
                  ? `<span class="ks-recording" id="ks-recording-${s.id}">Press a key combo…</span>`
                  : `<kbd class="ks-kbd${hasConflict ? ' ks-kbd-conflict' : ''}">${esc(_ksFormatCombo(s))}</kbd>`
                }
                ${hasConflict && !isEditing ? `<span class="ks-conflict-hint" title="Conflicts with: ${esc(conflicts.map(c => c.label).join(', '))}">⚠</span>` : ''}
              </div>
              <div class="ks-row-actions">
                ${isEditing
                  ? `<button class="btn-ghost-sm ks-btn" onclick="_ksCancelEdit()">Cancel</button>`
                  : `<button class="btn-ghost-sm ks-btn" onclick="_ksStartEdit('${s.id}')">Edit</button>`
                }
                ${isModified ? `<button class="btn-ghost-sm ks-btn" onclick="_ksResetOne('${s.id}')" title="Reset to default">↺</button>` : ''}
              </div>
            </div>`;
        }).join('')}
      </div>`;
  }).join('');
}

/* ──────────────────────────────────────────────
   Edit / Record
────────────────────────────────────────────── */

function _ksStartEdit(id) {
  _ksEditingId = id;
  _ksRender();
  // Listen for the next key combo
  const handler = function (e) {
    // Ignore modifier-only presses
    if (['Control', 'Meta', 'Shift', 'Alt'].includes(e.key)) return;
    e.preventDefault();
    e.stopPropagation();
    document.removeEventListener('keydown', handler, true);

    const newKey   = e.key;
    const newCtrl  = e.ctrlKey || e.metaKey;
    const newShift = e.shiftKey;

    const conflicts = _ksConflicts(_ksShortcuts, id, newKey, newCtrl, newShift);
    const s = _ksShortcuts.find(x => x.id === id);
    if (s) {
      s.key   = newKey;
      s.ctrl  = newCtrl;
      s.shift = newShift;
    }
    _ksEditingId = null;
    _ksSave(_ksShortcuts);
    _ksRender();

    if (conflicts.length > 0) {
      showToast(`⚠ Conflict with "${conflicts[0].label}" — both shortcuts are saved but only one will fire.`);
    } else {
      showToast(`Shortcut updated: ${_ksFormatCombo(s)}`);
    }
  };
  document.addEventListener('keydown', handler, true);
}

function _ksCancelEdit() {
  _ksEditingId = null;
  _ksRender();
}

function _ksResetOne(id) {
  const def = _KS_DEFAULTS.find(d => d.id === id);
  const s   = _ksShortcuts.find(x => x.id === id);
  if (def && s) {
    s.key   = def.key;
    s.ctrl  = def.ctrl;
    s.shift = def.shift;
    _ksSave(_ksShortcuts);
    _ksRender();
    showToast('Shortcut reset to default.');
  }
}

function ksResetAll() {
  localStorage.removeItem(_KS_STORAGE_KEY);
  _ksShortcuts = _ksLoad();
  _ksRender();
  showToast('All shortcuts reset to defaults.');
}
