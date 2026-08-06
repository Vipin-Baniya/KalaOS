/**
 * KalaOS Automatic Session Restore
 *
 * Periodically saves workspace state to localStorage and restores it
 * when the user returns (logs in / refreshes).
 *
 * Features:
 *  - Auto-save workspace state (debounced)
 *  - Restore previous session on login
 *  - Notify users when a session is restored
 *  - Allow users to disable automatic restoration
 *  - Handle corrupted session data gracefully
 */

/* ──────────────────────────────────────────────
   Configuration
────────────────────────────────────────────── */
const SESSION_CONFIG = {
  storageKey: "kala-session-state",
  enabledKey: "kala-session-restore-enabled",
  dismissedKey: "kala-session-restore-dismissed",
  autoSaveInterval: 30000,        // 30 seconds
  autoSaveDebounce: 2000,         // 2 seconds after user input stops
  maxStateSize: 512 * 1024,       // 512KB max serialized state
  version: 1,                     // schema version for migration
};

/* ──────────────────────────────────────────────
   Session State Shape
   {
     version: 1,
     savedAt: ISO timestamp,
     studio: current studio mode,
     theme: current theme ID,
     sidebarCollapsed: boolean,
     aiPanelOpen: boolean,
     textEditor: {
       content: string,
       domain: string,
       artistName: string,
       writingMode: string,
     },
     beatState: { kick: [...], snare: [...], ... },
     beatBpm: number,
     beatPreset: string,
     mixer: { lead: {...}, bass: {...}, ... },
     mastering: { eq: [...], compressor: {...}, ... },
     timelineTracks: [...],
     videoScenes: [...],
     chatHistory: array of last 20 messages,
     designCanvas: JSON string or null,
     _size: number (internal, not serialized)
   }
────────────────────────────────────────────── */

/* ──────────────────────────────────────────────
   State helpers
────────────────────────────────────────────── */

const _session = {
  _timer: null,
  _debounceTimer: null,
  _restoreInProgress: false,
};

/**
 * Check if session restore is enabled by the user.
 */
function _isSessionRestoreEnabled() {
  const val = localStorage.getItem(SESSION_CONFIG.enabledKey);
  // Default to enabled if not explicitly set
  return val === null || val === "true";
}

/**
 * Collect the current workspace state from the DOM and global variables.
 */
function _collectState() {
  try {
    const state = {
      version: SESSION_CONFIG.version,
      savedAt: new Date().toISOString(),
      studio: typeof _currentStudio !== "undefined" ? _currentStudio : "general",
      theme: localStorage.getItem("kala-theme") || "dark-cosmos",
      sidebarCollapsed: localStorage.getItem("kala-sidebar-collapsed") === "1",
      aiPanelOpen: typeof _aiPanelOpen !== "undefined" ? _aiPanelOpen : true,
    };

    // Text editor state
    const artText = document.getElementById("artText");
    if (artText && artText.value.trim()) {
      state.textEditor = {
        content: artText.value,
        domain: document.getElementById("artDomain")?.value || "general",
        artistName: document.getElementById("artistName")?.value || "",
        writingMode: typeof _currentWritingMode !== "undefined" ? _currentWritingMode : "free",
      };
    }

    // Beat sequencer state
    if (typeof _beatState !== "undefined" && _beatState && Object.keys(_beatState).length > 0) {
      const hasBeats = Object.values(_beatState).some((row) =>
        Array.isArray(row) && row.some((v) => v)
      );
      if (hasBeats) {
        state.beatState = {};
        Object.entries(_beatState).forEach(([row, cells]) => {
          state.beatState[row] = cells.map(Boolean);
        });
        state.beatBpm = parseInt(document.getElementById("beatBpm")?.value || "90", 10);
        state.beatPreset = "custom";
      }
    }

    // Mixer settings
    const mixerState = _collectMixerState();
    if (mixerState) state.mixer = mixerState;

    // Mastering settings
    const masteringState = _collectMasteringState();
    if (masteringState) state.mastering = masteringState;

    // Timeline tracks
    if (typeof _tlTracks !== "undefined" && _tlTracks && _tlTracks.length > 0) {
      state.timelineTracks = _tlTracks;
    }

    // Video studio scenes
    if (typeof _vsScenes !== "undefined" && _vsScenes && _vsScenes.length > 0) {
      state.videoScenes = _vsScenes;
    }

    // Chat history (last 20 messages)
    if (typeof _chatHistory !== "undefined" && _chatHistory && _chatHistory.length > 0) {
      state.chatHistory = _chatHistory.slice(-20);
    }

    // Design canvas state (if fabric is loaded)
    if (typeof _dcCanvas !== "undefined" && _dcCanvas && _dcReady) {
      try {
        state.designCanvas = JSON.stringify(_dcCanvas.toJSON(["_kalaId", "animation"]));
      } catch (_) { /* skip canvas state */ }
    }

    return state;
  } catch (err) {
    console.warn("[SessionRestore] Error collecting state:", err);
    return null;
  }
}

/**
 * Collect mixer channel states from DOM faders.
 */
function _collectMixerState() {
  const channels = ["lead", "bass", "drums", "synth", "fx", "master"];
  const state = {};
  let hasData = false;

  channels.forEach((ch) => {
    const fader = document.getElementById(`ch-${ch}-fader`);
    const pan = document.getElementById(`ch-${ch}-pan`);
    const muteBtn = document.getElementById(`mute-${ch}`);
    const soloBtn = document.getElementById(`solo-${ch}`);

    const faderVal = fader ? fader.textContent : null;
    const panVal = pan ? pan.textContent : null;

    if (faderVal || panVal) {
      hasData = true;
      state[ch] = {
        fader: faderVal || "80",
        pan: panVal || "C",
        muted: muteBtn ? muteBtn.classList.contains("active") : false,
        soloed: soloBtn ? soloBtn.classList.contains("active") : false,
      };
    }
  });

  return hasData ? state : null;
}

/**
 * Collect mastering chain settings from DOM sliders.
 */
function _collectMasteringState() {
  const eqBands = ["eqSubBass", "eqBass", "eqLowMid", "eqMid", "eqHiMid", "eqPresence", "eqAir"];
  const eq = [];
  let hasEq = false;

  eqBands.forEach((id) => {
    const slider = document.getElementById(id);
    if (slider) {
      const val = parseFloat(slider.value);
      eq.push(val);
      if (val !== 0) hasEq = true;
    } else {
      eq.push(0);
    }
  });

  if (!hasEq) return null;

  return {
    eq,
    compressor: {
      threshold: document.getElementById("compThresh")?.value || "-12",
      ratio: document.getElementById("compRatio")?.value || "4",
      attack: document.getElementById("compAttack")?.value || "20",
      release: document.getElementById("compRelease")?.value || "150",
      gain: document.getElementById("compGain")?.value || "3",
      knee: document.getElementById("compKnee")?.value || "5",
    },
    stereoWidth: document.getElementById("stereoWidth")?.value || "100",
    limiter: {
      ceiling: document.getElementById("limCeiling")?.value || "-0.3",
      lufs: document.getElementById("limLufs")?.value || "-14",
    },
  };
}

/**
 * Save current workspace state to localStorage.
 */
function _saveState() {
  if (!_isSessionRestoreEnabled()) return;

  const state = _collectState();
  if (!state) return;

  try {
    const serialized = JSON.stringify(state);
    if (serialized.length > SESSION_CONFIG.maxStateSize) {
      console.warn("[SessionRestore] State too large, skipping save:", serialized.length);
      return;
    }
    localStorage.setItem(SESSION_CONFIG.storageKey, serialized);
  } catch (err) {
    // localStorage quota exceeded or unavailable
    console.warn("[SessionRestore] Failed to save state:", err);
  }
}

/**
 * Debounced save — called after user interactions.
 */
function _debouncedSave() {
  if (_session._debounceTimer) clearTimeout(_session._debounceTimer);
  _session._debounceTimer = setTimeout(() => {
    _saveState();
  }, SESSION_CONFIG.autoSaveDebounce);
}

/**
 * Periodic auto-save timer.
 */
function _startAutoSave() {
  _stopAutoSave();
  _session._timer = setInterval(() => {
    _saveState();
  }, SESSION_CONFIG.autoSaveInterval);
}

function _stopAutoSave() {
  if (_session._timer) {
    clearInterval(_session._timer);
    _session._timer = null;
  }
  if (_session._debounceTimer) {
    clearTimeout(_session._debounceTimer);
    _session._debounceTimer = null;
  }
}

/* ──────────────────────────────────────────────
   Save triggers
────────────────────────────────────────────── */

/**
 * Set up event listeners that trigger debounced state saves.
 */
function _initSaveTriggers() {
  // Text editor input
  const artText = document.getElementById("artText");
  if (artText) {
    artText.addEventListener("input", _debouncedSave);
  }

  // Beat sequencer — observe cell clicks via event delegation
  const beatPanel = document.querySelector(".beat-grid-wrap");
  if (beatPanel) {
    beatPanel.addEventListener("click", (e) => {
      if (e.target.classList.contains("beat-cell")) _debouncedSave();
    });
  }

  // Beat BPM change
  const beatBpm = document.getElementById("beatBpm");
  if (beatBpm) beatBpm.addEventListener("change", _debouncedSave);

  // Mixer fader changes
  document.querySelectorAll(".mixer-fader, .mixer-pan").forEach((el) => {
    el.addEventListener("input", _debouncedSave);
  });

  // Mastering eq / compressor changes
  document.querySelectorAll("#masteringChain input[type='range']").forEach((el) => {
    el.addEventListener("input", _debouncedSave);
  });

  // Timeline changes
  document.querySelectorAll("#mtool-timeline .tl-strip").forEach((el) => {
    el.addEventListener("click", _debouncedSave);
  });

  // Video studio scene changes
  const vsSceneList = document.getElementById("vsSceneList");
  if (vsSceneList) {
    const observer = new MutationObserver(() => _debouncedSave());
    observer.observe(vsSceneList, { childList: true, subtree: true });
  }

  // Design canvas changes
  if (typeof _dcCanvas !== "undefined" && _dcCanvas) {
    _dcCanvas.on("object:added", _debouncedSave);
    _dcCanvas.on("object:removed", _debouncedSave);
    _dcCanvas.on("object:modified", _debouncedSave);
  }

  // Save on page visibility change (tab switch / minimize)
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") {
      _saveState();
    }
  });

  // Save before unload
  window.addEventListener("beforeunload", () => {
    _saveState();
  });
}

/* ──────────────────────────────────────────────
   Restore
────────────────────────────────────────────── */

/**
 * Try to restore a previously saved session.
 * Returns true if state was successfully restored.
 */
function _tryRestore() {
  if (!_isSessionRestoreEnabled()) return false;

  const raw = localStorage.getItem(SESSION_CONFIG.storageKey);
  if (!raw) return false;

  let state;
  try {
    state = JSON.parse(raw);
  } catch (_) {
    // Corrupted data — clean up and return
    console.warn("[SessionRestore] Corrupted session data, clearing.");
    localStorage.removeItem(SESSION_CONFIG.storageKey);
    return false;
  }

  // Validate schema version
  if (!state || typeof state !== "object" || !state.version) {
    console.warn("[SessionRestore] Invalid session data shape.");
    localStorage.removeItem(SESSION_CONFIG.storageKey);
    return false;
  }

  // Check if the session is too old (older than 7 days)
  if (state.savedAt) {
    const savedDate = new Date(state.savedAt);
    const now = new Date();
    const daysSinceSave = (now - savedDate) / (1000 * 60 * 60 * 24);
    if (daysSinceSave > 7) {
      console.info("[SessionRestore] Session is too old (", daysSinceSave.toFixed(1), " days), discarding.");
      localStorage.removeItem(SESSION_CONFIG.storageKey);
      return false;
    }
  }

  // Mark that restore is in progress to batch UI updates
  _session._restoreInProgress = true;

  try {
    _restoreTheme(state);
    _restoreSidebarPanel(state);
    _restoreTextEditor(state);
    _restoreBeatState(state);
    _restoreMixer(state);
    _restoreMastering(state);
    _restoreTimeline(state);
    _restoreVideoScenes(state);
    _restoreDesignCanvas(state);
    _restoreStudio(state);
  } catch (err) {
    console.warn("[SessionRestore] Error during restoration, partial restore may have occurred:", err);
  }

  _session._restoreInProgress = false;
  return true;
}

function _restoreTheme(state) {
  if (state.theme && typeof applyTheme === "function") {
    applyTheme(state.theme, false);
  }
}

function _restoreSidebarPanel(state) {
  if (state.sidebarCollapsed) {
    const sidebar = document.getElementById("appSidebar");
    const icon = document.getElementById("sidebarToggleIcon");
    if (sidebar) sidebar.classList.add("collapsed");
    if (icon) icon.textContent = "▶";
  }
  if (state.aiPanelOpen === false && typeof _hideAiPanel === "function") {
    _hideAiPanel();
  } else if (state.aiPanelOpen  && typeof _showAiPanel === "function") {
    _showAiPanel();
  }
}

function _restoreTextEditor(state) {
  if (!state.textEditor) return;

  const artText = document.getElementById("artText");
  const domain = document.getElementById("artDomain");
  const artistName = document.getElementById("artistName");

  if (artText && state.textEditor.content) {
    artText.value = state.textEditor.content;
    if (typeof onEditorInput === "function") onEditorInput();
  }
  if (domain && state.textEditor.domain) {
    domain.value = state.textEditor.domain;
  }
  if (artistName && state.textEditor.artistName) {
    artistName.value = state.textEditor.artistName;
  }
  if (state.textEditor.writingMode && typeof setWritingMode === "function") {
    setWritingMode(state.textEditor.writingMode);
  }
}

function _restoreBeatState(state) {
  if (!state.beatState) return;
  if (typeof _beatState === "undefined") return;

  try {
    Object.entries(state.beatState).forEach(([row, cells]) => {
      if (_beatState[row] && Array.isArray(cells)) {
        _beatState[row] = cells.slice(0, 16);
        const container = document.getElementById(`cells-${row}`);
        if (container) {
          for (let i = 0; i < Math.min(cells.length, 16); i++) {
            if (container.children[i]) {
              container.children[i].classList.toggle("on", !!cells[i]);
            }
          }
        }
      }
    });

    if (state.beatBpm) {
      const bpmInput = document.getElementById("beatBpm");
      if (bpmInput) bpmInput.value = state.beatBpm;
    }
  } catch (_) { /* partial beat restore ok */ }
}

function _restoreMixer(state) {
  if (!state.mixer) return;

  try {
    Object.entries(state.mixer).forEach(([ch, settings]) => {
      if (settings.fader) {
        const faderInput = document.querySelector(`#ch-${ch} .mixer-fader`);
        if (faderInput) {
          faderInput.value = settings.fader;
          if (typeof updateMixFader === "function") updateMixFader(ch, settings.fader);
        }
      }
      if (settings.pan) {
        const panInput = document.querySelector(`#ch-${ch} .mixer-pan`);
        if (panInput) {
          // Convert "C", "L12", "R8" back to numeric
          const panMap = { C: 0 };
          const match = settings.pan.match(/^([LR])(\d+)$/);
          const panVal = match
            ? (match[1] === "L" ? -parseInt(match[2], 10) : parseInt(match[2], 10))
            : (panMap[settings.pan] !== undefined ? panMap[settings.pan] : 0);
          panInput.value = panVal;
          if (typeof updateMixPan === "function") updateMixPan(ch, panVal);
        }
      }
      if (settings.muted && typeof toggleMixMute === "function") {
        toggleMixMute(ch);
      }
    });
  } catch (_) { /* partial mixer restore ok */ }
}

function _restoreMastering(state) {
  if (!state.mastering) return;
  if (typeof loadEqPreset !== "function") return;

  try {
    // Apply EQ
    const eqBands = ["eqSubBass", "eqBass", "eqLowMid", "eqMid", "eqHiMid", "eqPresence", "eqAir"];
    const eqBandNames = ["sub-bass", "bass", "low-mid", "mid", "hi-mid", "presence", "air"];

    if (state.mastering.eq && Array.isArray(state.mastering.eq)) {
      state.mastering.eq.forEach((val, i) => {
        if (i < eqBands.length) {
          const slider = document.getElementById(eqBands[i]);
          if (slider) {
            slider.value = val;
            if (typeof updateEqBand === "function") updateEqBand(eqBandNames[i], val);
          }
        }
      });
    }

    // Compressor
    const comp = state.mastering.compressor || {};
    const compMap = {
      threshold: "compThresh",
      ratio: "compRatio",
      attack: "compAttack",
      release: "compRelease",
      gain: "compGain",
      knee: "compKnee",
    };
    Object.entries(compMap).forEach(([key, id]) => {
      if (comp[key] !== undefined) {
        const slider = document.getElementById(id);
        if (slider) slider.value = comp[key];
      }
    });
    // Trigger update for each comp parameter
    ["thresh", "ratio", "attack", "release", "gain", "knee"].forEach((param) => {
      if (typeof updateCompressor === "function") {
        const val = comp[param === "knee" ? "knee" : param];
        if (val !== undefined) updateCompressor(param, val);
      }
    });

    // Stereo width
    if (state.mastering.stereoWidth) {
      const sw = document.getElementById("stereoWidth");
      if (sw) {
        sw.value = state.mastering.stereoWidth;
        if (typeof updateStereoWidth === "function") updateStereoWidth(state.mastering.stereoWidth);
      }
    }

    // Limiter
    const lim = state.mastering.limiter || {};
    if (lim.ceiling) {
      const lc = document.getElementById("limCeiling");
      if (lc) {
        lc.value = lim.ceiling;
        if (typeof updateLimiter === "function") updateLimiter("ceiling", lim.ceiling);
      }
    }
    if (lim.lufs) {
      const ll = document.getElementById("limLufs");
      if (ll) {
        ll.value = lim.lufs;
        if (typeof updateLimiter === "function") updateLimiter("lufs", lim.lufs);
      }
    }
  } catch (_) { /* partial mastering restore ok */ }
}

function _restoreTimeline(state) {
  if (!state.timelineTracks) return;
  if (typeof _tlTracks === "undefined") return;

  try {
    // Only restore if the timeline hasn't been initialized with defaults yet
    const ruler = document.getElementById("tlRuler");
    if (!ruler) return;

    // If there are existing default tracks with no blocks, replace them
    const hasExisting = _tlTracks.some((t) => t.blocks && t.blocks.length > 0);
    if (!hasExisting) {
      _tlTracks.length = 0;
      state.timelineTracks.forEach((t) => {
        _tlTracks.push({
          id: t.id,
          label: t.label,
          color: t.color,
          blocks: (t.blocks || []).map((b) => ({
            id: b.id,
            bar: b.bar,
            len: b.len,
            label: b.label,
            type: b.type,
          })),
        });
      });
      if (typeof renderTimeline === "function") renderTimeline();
    }
  } catch (_) { /* partial timeline restore ok */ }
}

function _restoreVideoScenes(state) {
  if (!state.videoScenes) return;
  if (typeof _vsScenes === "undefined") return;

  try {
    _vsScenes.length = 0;
    state.videoScenes.forEach((s) => {
      _vsScenes.push({
        index: s.index,
        text: s.text,
        image_concept: s.image_concept || "",
        animation: s.animation || "fade",
        duration: s.duration || 4,
        voice_text: s.voice_text || s.text || "",
        bg_music: s.bg_music || "",
      });
    });
    if (typeof _vsRenderSceneList === "function") _vsRenderSceneList();
    if (typeof _vsUpdatePreviewInfo === "function") _vsUpdatePreviewInfo();
  } catch (_) { /* partial video scenes restore ok */ }
}

function _restoreDesignCanvas(state) {
  if (!state.designCanvas) return;
  if (typeof _dcCanvas === "undefined" || !_dcReady) return;

  try {
    _dcCanvas.loadFromJSON(JSON.parse(state.designCanvas), () => {
      _dcCanvas.renderAll();
      if (typeof dcRefreshLayers === "function") dcRefreshLayers();
    });
  } catch (_) { /* canvas restore failed silently */ }
}

function _restoreStudio(state) {
  if (!state.studio || typeof switchStudio !== "function") return;
  if (state.studio === "general" || state.studio === "dashboard") return;

  // Delay studio switch to let other restore operations complete first
  setTimeout(() => {
    try {
      switchStudio(state.studio);
    } catch (_) { /* studio switch is best-effort */ }
  }, 100);
}

/* ──────────────────────────────────────────────
   Session Restore UI
────────────────────────────────────────────── */

/**
 * Show a notification banner when a session is restored.
 */
function _showRestoreNotification() {
  if (localStorage.getItem(SESSION_CONFIG.dismissedKey) === "true") return;

  const banner = document.getElementById("sessionRestoreBanner");
  if (!banner) return;

  banner.classList.remove("hidden");
}

function dismissSessionRestoreBanner() {
  const banner = document.getElementById("sessionRestoreBanner");
  if (banner) banner.classList.add("hidden");
  localStorage.setItem(SESSION_CONFIG.dismissedKey, "true");
}

function toggleSessionRestoreSetting() {
  const current = _isSessionRestoreEnabled();
  const newVal = !current;
  localStorage.setItem(SESSION_CONFIG.enabledKey, String(newVal));

  // Update toggle button
  const toggle = document.getElementById("sessionRestoreToggle");
  if (toggle) {
    toggle.classList.toggle("active", newVal);
    toggle.setAttribute("aria-checked", String(newVal));
  }

  // If enabling, save current state immediately
  if (newVal) {
    _saveState();
    _startAutoSave();
  } else {
    // If disabling, clear saved state and stop auto-save
    localStorage.removeItem(SESSION_CONFIG.storageKey);
    _stopAutoSave();
  }
}

/* ──────────────────────────────────────────────
   Public API
────────────────────────────────────────────── */

/**
 * Initialize the Session Restore system.
 * Called from app.js during DOMContentLoaded.
 */
function initSessionRestore() {
  // Restore UI controls
  _renderSettingsToggle();

  // Try to restore previous session
  const restored = _tryRestore();

  if (restored) {
    _showRestoreNotification();
  }

  // Start periodic auto-save (only if enabled)
  if (_isSessionRestoreEnabled()) {
    _startAutoSave();
    _initSaveTriggers();
  }

  console.info(
    "[SessionRestore] Initialized.",
    restored ? "Previous session restored." : "No previous session found."
  );
}

/**
 * Initialize the session restore toggle in settings.
 */
function _renderSettingsToggle() {
  const toggle = document.getElementById("sessionRestoreToggle");
  if (!toggle) return;

  const enabled = _isSessionRestoreEnabled();
  toggle.classList.toggle("active", enabled);
  toggle.setAttribute("aria-checked", String(enabled));
}

/**
 * Manually trigger a state save (e.g., after a significant action).
 */
function saveSessionState() {
  _saveState();
}

/**
 * Clear all saved session data (e.g., on logout).
 */
function clearSessionState() {
  localStorage.removeItem(SESSION_CONFIG.storageKey);
  localStorage.removeItem(SESSION_CONFIG.dismissedKey);
  _stopAutoSave();
}

// Export for use from other scripts
window.initSessionRestore = initSessionRestore;
window.dismissSessionRestoreBanner = dismissSessionRestoreBanner;
window.toggleSessionRestoreSetting = toggleSessionRestoreSetting;
window.saveSessionState = saveSessionState;
window.clearSessionState = clearSessionState;