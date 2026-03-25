/**
 * KalaOS Studio — Frontend Application
 *
 * Communicates with the KalaOS backend (default: http://localhost:8000).
 * All results are rendered in-page; no data is sent anywhere else.
 *
 * To point the UI at a different backend, set the global before this script:
 *   <script>window.KALA_API_BASE = "https://your-backend.example.com";</script>
 *
 * No build step required — plain ES2020 JavaScript.
 */

/* ──────────────────────────────────────────────
   Configuration
────────────────────────────────────────────── */
const API_BASE = (typeof window !== "undefined" && window.KALA_API_BASE) || "http://localhost:8000";

/* ──────────────────────────────────────────────
   State
────────────────────────────────────────────── */
let _lastResponse = null;
let _authToken    = null;
let _currentUser  = null;
let _deferredInstallPrompt = null;

/* ══════════════════════════════════════════════
   THEME SYSTEM
══════════════════════════════════════════════ */

const THEME_ACCENT_COLORS = {
  "dark-cosmos": "#7c5af1",
  "ember":       "#f0703a",
  "ocean":       "#2dd4bf",
  "forest":      "#4ade80",
  "crimson":     "#e23270",
  "light":       "#6d28d9",
  "custom":      null,
};

function applyTheme(themeId, save = true) {
  document.documentElement.setAttribute("data-theme", themeId);
  if (save) {
    localStorage.setItem("kala-theme", themeId);
  }

  // Update theme-color meta (affects browser chrome on mobile)
  const color = THEME_ACCENT_COLORS[themeId] || THEME_ACCENT_COLORS["dark-cosmos"];
  const meta = document.getElementById("themeColorMeta");
  if (meta && color) meta.setAttribute("content", color);

  // Update swatch active states
  document.querySelectorAll(".theme-swatch").forEach(s => {
    const active = s.dataset.theme === themeId;
    s.classList.toggle("active", active);
    s.setAttribute("aria-checked", String(active));
  });

  // If switching away from custom, clear inline overrides
  if (themeId !== "custom") {
    const html = document.documentElement;
    ["--bg", "--surface", "--surface-2", "--accent", "--text"].forEach(p => {
      html.style.removeProperty(p);
    });
  }
}

function applyCustomColor(property, value) {
  document.documentElement.style.setProperty(property, value);
  // Mark theme as "custom" in localStorage but don't switch the data-theme attribute
  // so the user can still see which preset is the base
  const custom = JSON.parse(localStorage.getItem("kala-custom-vars") || "{}");
  custom[property] = value;
  localStorage.setItem("kala-custom-vars", JSON.stringify(custom));
}

function saveCustomTheme() {
  applyTheme("custom");
  // Persist the current inline overrides as the custom theme
  const custom = JSON.parse(localStorage.getItem("kala-custom-vars") || "{}");
  localStorage.setItem("kala-custom-theme", JSON.stringify(custom));
  setStatus("Custom theme saved.", false);
}

function resetCustomTheme() {
  localStorage.removeItem("kala-custom-vars");
  localStorage.removeItem("kala-custom-theme");
  const html = document.documentElement;
  ["--bg", "--surface", "--surface-2", "--accent", "--text"].forEach(p => html.style.removeProperty(p));
  applyTheme("dark-cosmos");
}

function loadSavedTheme() {
  const saved = localStorage.getItem("kala-theme");
  if (saved) {
    applyTheme(saved, false);
  } else {
    // No explicit preference — follow the OS colour scheme
    const preferLight = window.matchMedia?.("(prefers-color-scheme: light)").matches;
    applyTheme(preferLight ? "light" : "dark-cosmos", false);
  }
  // Keep in sync with OS changes when the user hasn't pinned a theme
  window.matchMedia?.("(prefers-color-scheme: light)").addEventListener("change", (e) => {
    if (!localStorage.getItem("kala-theme")) {
      applyTheme(e.matches ? "light" : "dark-cosmos", false);
    }
  });
  // Re-apply any persisted custom overrides
  const custom = JSON.parse(localStorage.getItem("kala-custom-vars") || "{}");
  Object.entries(custom).forEach(([k, v]) => document.documentElement.style.setProperty(k, v));
  // Sync color pickers to current values
  _syncColorPickers();
}

function _syncColorPickers() {
  const style = getComputedStyle(document.documentElement);
  const map = {
    "customBg":      "--bg",
    "customSurface": "--surface",
    "customAccent":  "--accent",
    "customText":    "--text",
  };
  Object.entries(map).forEach(([id, prop]) => {
    const el_ = document.getElementById(id);
    if (!el_) return;
    const val = style.getPropertyValue(prop).trim();
    if (val) {
      // Convert rgb to hex for the color picker
      const hex = _rgbToHex(val);
      if (hex) el_.value = hex;
    }
  });
}

function _rgbToHex(color) {
  // Handle rgb(r, g, b) and #rrggbb
  if (color.startsWith("#")) return color.slice(0, 7);
  const m = color.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
  if (!m) return null;
  return "#" + [m[1], m[2], m[3]].map(n => parseInt(n).toString(16).padStart(2, "0")).join("");
}

function toggleThemePanel() {
  const panel   = document.getElementById("themePanel");
  const overlay = document.getElementById("themePanelOverlay");
  const isOpen  = panel.classList.contains("open");
  panel.classList.toggle("open", !isOpen);
  panel.setAttribute("aria-hidden", String(isOpen));
  overlay.classList.toggle("hidden", isOpen);
}

/* ══════════════════════════════════════════════
   AUTH SYSTEM
══════════════════════════════════════════════ */

function _loadSession() {
  _authToken   = localStorage.getItem("kala-auth-token") || null;
  _currentUser = JSON.parse(localStorage.getItem("kala-current-user") || "null");
}

function _saveSession(token, user) {
  _authToken   = token;
  _currentUser = user;
  if (token) {
    localStorage.setItem("kala-auth-token", token);
    localStorage.setItem("kala-current-user", JSON.stringify(user));
  } else {
    localStorage.removeItem("kala-auth-token");
    localStorage.removeItem("kala-current-user");
  }
}

function _updateUserUI() {
  const name   = _currentUser ? _currentUser.name  : "Guest";
  const email  = _currentUser ? _currentUser.email : "";
  const avatar = name.charAt(0).toUpperCase();

  el("userAvatar").textContent    = avatar;
  el("userNameLabel").textContent = name;
  el("dropdownName").textContent  = name;
  el("dropdownEmail").textContent = email;
}

function showAuthScreen(name) {
  document.querySelectorAll(".auth-screen").forEach(s => {
    s.classList.toggle("active", s.id === `auth-${name}`);
  });
  // Clear alerts when switching screens
  ["loginError", "registerError", "registerSuccess",
   "forgotError", "forgotSuccess", "resetError", "resetSuccess"].forEach(id => {
    const e = document.getElementById(id);
    if (e) { e.textContent = ""; e.classList.add("hidden"); }
  });
}

function _setAuthMessage(id, msg, isError) {
  const e = document.getElementById(id);
  if (!e) return;
  e.textContent = msg;
  e.classList.toggle("hidden", !msg);
  e.className = "auth-alert " + (isError ? "auth-error" : "auth-success") + (msg ? "" : " hidden");
}

async function handleLogin() {
  const btn      = document.getElementById("loginSubmitBtn");
  const email    = document.getElementById("loginEmail").value.trim();
  const password = document.getElementById("loginPassword").value;
  _setAuthMessage("loginError", "", true);

  if (!email || !password) {
    _setAuthMessage("loginError", "Please enter your email and password.", true);
    return;
  }
  btn.disabled = true;
  btn.textContent = "Signing in…";

  try {
    const resp = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || "Login failed.");
    _saveSession(data.token, data.user);
    _updateUserUI();
    showApp();
  } catch (err) {
    _setAuthMessage("loginError", err.message, true);
  } finally {
    btn.disabled = false;
    btn.textContent = "Sign In";
  }
}

async function handleRegister() {
  const btn      = document.getElementById("registerSubmitBtn");
  const name     = document.getElementById("registerName").value.trim();
  const email    = document.getElementById("registerEmail").value.trim();
  const password = document.getElementById("registerPassword").value;
  _setAuthMessage("registerError", "", true);
  _setAuthMessage("registerSuccess", "", false);

  if (!email || !password) {
    _setAuthMessage("registerError", "Please fill in all required fields.", true);
    return;
  }
  btn.disabled = true;
  btn.textContent = "Creating account…";

  try {
    const resp = await fetch(`${API_BASE}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, name }),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || "Registration failed.");
    _setAuthMessage("registerSuccess", "Account created! Signing you in…", false);
    // Auto login
    await new Promise(r => setTimeout(r, 800));
    const lr = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const ld = await lr.json();
    if (lr.ok) {
      _saveSession(ld.token, ld.user);
      _updateUserUI();
      showApp();
    } else {
      showAuthScreen("login");
    }
  } catch (err) {
    _setAuthMessage("registerError", err.message, true);
  } finally {
    btn.disabled = false;
    btn.textContent = "Create Account";
  }
}

async function handleForgotPassword() {
  const btn   = document.getElementById("forgotSubmitBtn");
  const email = document.getElementById("forgotEmail").value.trim();
  _setAuthMessage("forgotError", "", true);
  _setAuthMessage("forgotSuccess", "", false);

  if (!email) {
    _setAuthMessage("forgotError", "Please enter your email address.", true);
    return;
  }
  btn.disabled = true;
  btn.textContent = "Sending…";

  try {
    const resp = await fetch(`${API_BASE}/auth/forgot-password`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || "Request failed.");
    // Show the reset token (in production this would be emailed)
    const tokenMsg = data.reset_token
      ? `Reset token (copy this — in production it would be emailed):\n\n${data.reset_token}`
      : "If that email exists, a reset link has been sent.";
    _setAuthMessage("forgotSuccess", tokenMsg, false);
  } catch (err) {
    _setAuthMessage("forgotError", err.message, true);
  } finally {
    btn.disabled = false;
    btn.textContent = "Send Reset Link";
  }
}

async function handleResetPassword() {
  const btn      = document.getElementById("resetSubmitBtn");
  const token    = document.getElementById("resetToken").value.trim();
  const password = document.getElementById("resetPassword").value;
  _setAuthMessage("resetError", "", true);
  _setAuthMessage("resetSuccess", "", false);

  if (!token || !password) {
    _setAuthMessage("resetError", "Please enter both the reset token and your new password.", true);
    return;
  }
  btn.disabled = true;
  btn.textContent = "Resetting…";

  try {
    const resp = await fetch(`${API_BASE}/auth/reset-password`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token, new_password: password }),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || "Reset failed.");
    _setAuthMessage("resetSuccess", "Password updated! You can now sign in.", false);
    setTimeout(() => showAuthScreen("login"), 1800);
  } catch (err) {
    _setAuthMessage("resetError", err.message, true);
  } finally {
    btn.disabled = false;
    btn.textContent = "Set New Password";
  }
}

function handleLogout() {
  // Revoke the token server-side (best-effort; don't block the UI on failure)
  if (_authToken) {
    fetch(`${API_BASE}/auth/logout`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token: _authToken }),
    }).catch(() => { /* ignore network errors on logout */ });
  }
  _saveSession(null, null);
  hide("userDropdown");
  el("userMenuBtn").setAttribute("aria-expanded", "false");
  showAuth();
}

/* ══════════════════════════════════════════════
   PROFILE MODAL
══════════════════════════════════════════════ */

function showProfileModal() {
  const overlay = el("profileModalOverlay");
  if (!overlay) return;
  // Pre-fill name
  if (_currentUser) {
    const nameInput = el("profileName");
    if (nameInput) nameInput.value = _currentUser.name || "";
  }
  // Clear messages
  ["profileError", "profileSuccess"].forEach(id => {
    const e = el(id);
    if (e) { e.textContent = ""; e.classList.add("hidden"); }
  });
  el("profileOldPass").value = "";
  el("profileNewPass").value = "";
  overlay.classList.remove("hidden");
}

function hideProfileModal() {
  const overlay = el("profileModalOverlay");
  if (overlay) overlay.classList.add("hidden");
}

function _setProfileMessage(id, msg, isError) {
  const e = el(id);
  if (!e) return;
  e.textContent = msg;
  e.classList.toggle("hidden", !msg);
  e.className = "auth-alert " + (isError ? "auth-error" : "auth-success") + (msg ? "" : " hidden");
}

async function handleUpdateProfile() {
  const btn  = el("profileSaveBtn");
  const name = el("profileName").value.trim();
  _setProfileMessage("profileError",   "", true);
  _setProfileMessage("profileSuccess", "", false);
  if (!name) {
    _setProfileMessage("profileError", "Name must not be empty.", true);
    return;
  }
  btn.disabled = true;
  btn.textContent = "Saving…";
  try {
    const resp = await fetch(`${API_BASE}/auth/update-profile`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token: _authToken, name }),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || "Update failed.");
    _currentUser = data.user;
    _saveSession(_authToken, _currentUser);
    _updateUserUI();
    _setProfileMessage("profileSuccess", "Name updated successfully.", false);
  } catch (err) {
    _setProfileMessage("profileError", err.message, true);
  } finally {
    btn.disabled = false;
    btn.textContent = "Save Name";
  }
}

async function handleChangePassword() {
  const btn     = el("profilePassBtn");
  const oldPass = el("profileOldPass").value;
  const newPass = el("profileNewPass").value;
  _setProfileMessage("profileError",   "", true);
  _setProfileMessage("profileSuccess", "", false);
  if (!oldPass || !newPass) {
    _setProfileMessage("profileError", "Please enter both current and new password.", true);
    return;
  }
  btn.disabled = true;
  btn.textContent = "Changing…";
  try {
    const resp = await fetch(`${API_BASE}/auth/change-password`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token: _authToken, old_password: oldPass, new_password: newPass }),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || "Password change failed.");
    _setProfileMessage("profileSuccess", "Password changed successfully.", false);
    el("profileOldPass").value = "";
    el("profileNewPass").value = "";
  } catch (err) {
    _setProfileMessage("profileError", err.message, true);
  } finally {
    btn.disabled = false;
    btn.textContent = "Change Password";
  }
}

async function handleDeleteAccount() {
  const btn  = el("profileDeleteBtn");
  const pass = el("profileDeletePass").value;
  _setProfileMessage("profileError",   "", true);
  _setProfileMessage("profileSuccess", "", false);
  if (!pass) {
    _setProfileMessage("profileError", "Please enter your current password to confirm deletion.", true);
    return;
  }
  if (!confirm("This will permanently delete your account and all your data. This cannot be undone. Continue?")) {
    return;
  }
  btn.disabled = true;
  btn.textContent = "Deleting…";
  try {
    const resp = await fetch(`${API_BASE}/auth/delete-account`, {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token: _authToken, password: pass }),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || "Account deletion failed.");
    // Deletion succeeded — clear session and return to auth screen
    _saveSession(null, null);
    hideProfileModal();
    showAuth();
  } catch (err) {
    _setProfileMessage("profileError", err.message, true);
    btn.disabled = false;
    btn.textContent = "Delete Account";
  }
}

function continueAsGuest() {
  _saveSession(null, null);
  _currentUser = null;
  _updateUserUI();
  showApp();
}

function toggleUserMenu() {
  const dropdown = el("userDropdown");
  const btn      = el("userMenuBtn");
  const isOpen   = !dropdown.classList.contains("hidden");
  dropdown.classList.toggle("hidden", isOpen);
  btn.setAttribute("aria-expanded", String(!isOpen));
}

function showApp() {
  hide("authOverlay");
  show("appRoot");
}

function showAuth() {
  show("authOverlay");
  hide("appRoot");
  showAuthScreen("login");
}

/* ══════════════════════════════════════════════
   PWA / Service Worker
══════════════════════════════════════════════ */

function initPWA() {
  // Register service worker
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("./sw.js").catch(() => { /* silent */ });
  }

  // Capture the beforeinstallprompt event for the install banner
  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    _deferredInstallPrompt = e;
    show("installBanner");
  });

  const installBtn   = document.getElementById("installBtn");
  const dismissBtn   = document.getElementById("dismissInstall");

  if (installBtn) {
    installBtn.addEventListener("click", async () => {
      if (!_deferredInstallPrompt) return;
      _deferredInstallPrompt.prompt();
      const { outcome } = await _deferredInstallPrompt.userChoice;
      if (outcome === "accepted") hide("installBanner");
      _deferredInstallPrompt = null;
    });
  }
  if (dismissBtn) {
    dismissBtn.addEventListener("click", () => {
      hide("installBanner");
      sessionStorage.setItem("kala-install-dismissed", "1");
    });
  }

  // Hide banner if already dismissed this session
  if (sessionStorage.getItem("kala-install-dismissed")) hide("installBanner");
}

/* ══════════════════════════════════════════════
   Keyboard shortcuts & click-outside
══════════════════════════════════════════════ */

document.addEventListener("click", (e) => {
  // Close user dropdown on outside click
  const menu = document.getElementById("userMenu");
  if (menu && !menu.contains(e.target)) {
    const dd = document.getElementById("userDropdown");
    if (dd && !dd.classList.contains("hidden")) {
      dd.classList.add("hidden");
      document.getElementById("userMenuBtn")?.setAttribute("aria-expanded", "false");
    }
  }
});

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    // Close theme panel
    const panel = document.getElementById("themePanel");
    if (panel?.classList.contains("open")) toggleThemePanel();
    // Close user dropdown
    const dd = document.getElementById("userDropdown");
    if (dd && !dd.classList.contains("hidden")) {
      dd.classList.add("hidden");
      document.getElementById("userMenuBtn")?.setAttribute("aria-expanded", "false");
    }
    // Close profile modal
    const profileModal = document.getElementById("profileModalOverlay");
    if (profileModal && !profileModal.classList.contains("hidden")) {
      hideProfileModal();
    }
  }
  // Ctrl/Cmd+Enter to run analysis
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
    const analyseBtn = document.getElementById("analyseBtn");
    if (analyseBtn && !analyseBtn.disabled) runDeepAnalysis();
  }
});

// Enter key in auth forms
["loginEmail", "loginPassword"].forEach(id => {
  document.getElementById(id)?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") handleLogin();
  });
});
["registerName", "registerEmail", "registerPassword"].forEach(id => {
  document.getElementById(id)?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") handleRegister();
  });
});
["forgotEmail"].forEach(id => {
  document.getElementById(id)?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") handleForgotPassword();
  });
});
["resetToken", "resetPassword"].forEach(id => {
  document.getElementById(id)?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") handleResetPassword();
  });
});

/* ══════════════════════════════════════════════
   ANALYSIS  (core — unchanged logic)
══════════════════════════════════════════════ */

async function runDeepAnalysis() {
  const text = el("artText").value.trim();
  if (!text) { setStatus("Please enter some text first.", true); return; }

  const domain     = el("artDomain").value;
  const artistName = el("artistName").value.trim() || null;
  const model      = el("ollamaModel").value.trim() || "llama3";

  setStatus("Analysing…");
  el("analyseBtn").disabled = true;

  try {
    const resp = await fetch(`${API_BASE}/deep-analysis`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, art_domain: domain, artist_name: artistName, model }),
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: resp.statusText }));
      const msg = Array.isArray(err.detail)
        ? err.detail.map(d => d.message || d.msg || JSON.stringify(d)).join("; ")
        : (err.detail || "Unknown error");
      throw new Error(msg);
    }

    const data = await resp.json();
    _lastResponse = data;
    renderAll(data);
    setStatus("");
    show("resultsPanel");
    switchTab("overview");

  } catch (err) {
    setStatus("Error: " + err.message, true);
  } finally {
    el("analyseBtn").disabled = false;
  }
}

function clearAll() {
  el("artText").value    = "";
  el("artistName").value = "";
  hide("resultsPanel");
  setStatus("");
  _lastResponse = null;
}

/* ──────────────────────────────────────────────
   Tab switching
────────────────────────────────────────────── */
function switchTab(tabId) {
  document.querySelectorAll(".tab").forEach(t => {
    const active = t.dataset.tab === tabId;
    t.classList.toggle("active", active);
    t.setAttribute("aria-selected", String(active));
  });
  document.querySelectorAll(".tab-pane").forEach(p => {
    p.classList.toggle("hidden", p.id !== `tab-${tabId}`);
    p.classList.toggle("active", p.id === `tab-${tabId}`);
  });
}

/* ──────────────────────────────────────────────
   Render: all sections
────────────────────────────────────────────── */
function renderAll(data) {
  renderOverview(data);
  renderCraft(data.craft || {});
  renderSignal(data.signal || {});
  renderCompose(data.composition || {});
  renderFlow(data.flow || {});
  renderCustody(data.custody || {});
  renderTemporal(data.temporal || {});
  el("rawJson").textContent = JSON.stringify(data, null, 2);
}

/* ── Overview ──────────────────────────────── */
function renderOverview(data) {
  const genome      = data.art_genome    || {};
  const existential = data.existential   || {};
  const arc         = genome.emotional_arc || {};

  if (data.narrative && !data.narrative.startsWith("[LLM unavailable")) {
    el("narrativeText").textContent = data.narrative;
    show("narrativeSection");
  } else {
    hide("narrativeSection");
  }

  el("overviewGenome").innerHTML = dl([
    ["Form",          genome.form_type          || "—"],
    ["Rhyme density", fmt2(genome.rhyme_density)],
    ["Complexity",    fmt2(genome.complexity_score)],
    ["Creative risk", fmt2(genome.creative_risk_index)],
    ["Symmetry",      genome.symmetry_score >= 1 ? "Yes" : "No"],
    ["Cognitive load",fmt2(genome.cognitive_load)],
  ]);

  const scores = arc.line_scores || [];
  el("emotionalArcViz").innerHTML = `
    <div class="arc-container">
      <div class="arc-line" aria-label="Emotional arc visualisation">
        ${scores.map(s => arcBar(s)).join("")}
      </div>
      <div class="arc-legend">
        <span>Start</span>
        <span>Direction: <strong>${arc.arc_direction || "—"}</strong></span>
        <span>End</span>
      </div>
    </div>
    ${dl([["Mean valence", fmt2(arc.mean_valence)]])}
  `;

  const cr = existential.creation_reason || {};
  const sv = existential.survival        || {};
  const ne = existential.emotional_necessity || {};
  el("overviewExistential").innerHTML = dl([
    ["Created for",     cr.primary_reason        || "—"],
    ["Survival-driven", sv.is_survival_driven ? "Yes" : "No"],
    ["Necessity score", fmt2(ne.necessity_score)],
    ["Necessity label", ne.necessity_label        || "—"],
  ]);

  const irr   = existential.human_irreducibility || {};
  const lines = irr.irreducible_lines || [];
  const idx   = irr.irreducibility_index || 0;
  let content = `<div class="score-bar-wrap">
      <div class="score-bar"><div class="score-bar-fill" style="width:${(idx*100).toFixed(0)}%"></div></div>
      <span class="score-label">${fmt2(idx)}</span>
    </div>`;
  if (lines.length) {
    content += `<div class="tag-row" style="margin-top:.75rem">`
      + lines.map(l => `<span class="tag accent">${esc(l)}</span>`).join("")
      + `</div>`;
  } else {
    content += `<p style="color:var(--text-muted);font-size:.85rem;margin-top:.5rem">No irreducible lines detected.</p>`;
  }
  el("irreducibleZones").innerHTML = content;
}

/* ── Craft ──────────────────────────────────── */
function renderCraft(craft) {
  const ph  = craft.phonetics   || {};
  const mf  = craft.meter_flow  || {};
  const bp  = craft.breath_points || {};
  const ld  = craft.line_density || {};
  const sd  = craft.semantic_drift || {};

  el("craftPhonetics").innerHTML = dl([
    ["Alliteration",  fmt2(ph.alliteration_score)],
    ["Assonance",     fmt2(ph.assonance_score)],
    ["Consonance",    fmt2(ph.consonance_score)],
    ["Harsh sounds",  fmt2(ph.harsh_sound_density)],
    ["Soft sounds",   fmt2(ph.soft_sound_density)],
  ]);

  el("craftMeter").innerHTML = dl([
    ["Dominant meter",   mf.dominant_meter  || "—"],
    ["Meter regularity", fmt2(mf.meter_regularity)],
    ["Stress patterns",  (mf.stress_patterns || []).join(", ") || "—"],
  ]);

  const breathPos = bp.breath_positions || [];
  el("craftBreath").innerHTML = breathPos.length
    ? `<div class="tag-row">${breathPos.map(b => `<span class="tag">${esc(b)}</span>`).join("")}</div>`
    : `<p style="color:var(--text-muted);font-size:.85rem">No prominent breath points detected.</p>`;

  const densities = ld.line_densities || [];
  el("craftDensity").innerHTML = densities.length
    ? `<div class="tag-row">${densities.map(d =>
        `<span class="tag">${esc(d.line ? d.line.slice(0, 24) : "—")} <em style="color:var(--accent)">${fmt2(d.density)}</em></span>`
      ).join("")}</div>`
    : `<p style="color:var(--text-muted);font-size:.85rem">—</p>`;

  const drift = sd.drift_score !== undefined
    ? `<div class="score-bar-wrap" style="margin-bottom:.5rem">
        <div class="score-bar"><div class="score-bar-fill" style="width:${((sd.drift_score||0)*100).toFixed(0)}%"></div></div>
        <span class="score-label">${fmt2(sd.drift_score)}</span>
      </div>
      ${dl([["Direction", sd.drift_direction || "—"]])}`
    : `<p style="color:var(--text-muted);font-size:.85rem">—</p>`;
  el("craftDrift").innerHTML = drift;
}

/* ── Signal ─────────────────────────────────── */
function renderSignal(signal) {
  const mem = signal.memorability || {};
  const lon = signal.longevity    || {};
  const res = signal.resonance    || {};

  el("signalMemorability").innerHTML = dl([
    ["Score",         scoreBar(mem.memorability_score)],
    ["Hook density",  fmt2(mem.hook_density)],
    ["Refrain count", mem.refrain_count !== undefined ? mem.refrain_count : "—"],
    ["Notes",         (mem.memorability_notes || []).join(" ") || "—"],
  ]);

  el("signalLongevity").innerHTML = dl([
    ["Score",          scoreBar(lon.longevity_score)],
    ["Timeless words", lon.timeless_word_count !== undefined ? lon.timeless_word_count : "—"],
    ["Trendy words",   lon.trendy_word_count   !== undefined ? lon.trendy_word_count   : "—"],
    ["Notes",          (lon.longevity_notes || []).join(" ") || "—"],
  ]);

  el("signalResonance").innerHTML = dl([
    ["Viral potential",  scoreBar(res.viral_potential)],
    ["Love resonance",   scoreBar(res.love_resonance)],
    ["Memory resonance", scoreBar(res.memory_resonance)],
    ["Note",             res.resonance_note || "—"],
  ]);
}

/* ── Compose ────────────────────────────────── */
function renderCompose(comp) {
  const ms  = comp.musical_structure || {};
  const cs  = comp.chord_suggestions || {};
  const tp  = comp.tempo             || {};
  const arr = comp.arrangement       || {};

  const sections = ms.sections || [];
  el("composeSections").innerHTML = sections.length
    ? sections.map(s => `
        <div class="section-block">
          <span class="section-role role-${s.role}">${s.role}</span>
          <span class="section-lines">${(s.lines || []).map(l => esc(l.slice(0,40))).join(" / ")}</span>
        </div>`).join("")
    : `<p style="color:var(--text-muted);font-size:.85rem">—</p>`;

  const prims = (cs.primary_progressions || []).map(p => `${p.progression} — <em>${p.feel}</em>`).join("<br>");
  el("composeChords").innerHTML = dl([
    ["Scale quality", cs.scale_quality || "—"],
    ["Scale name",    cs.scale_name    || "—"],
    ["Primary",       prims || "—"],
    ["Key options",   (cs.key_note_suggestions || []).join(", ") || "—"],
  ]);

  el("composeTempo").innerHTML = dl([
    ["BPM range",  tp.bpm_range ? tp.bpm_range.join("–") : "—"],
    ["Feel",       tp.feel || "—"],
    ["Time sig",   (tp.time_signature_suggestions || []).join("; ") || "—"],
  ]);

  el("composeArrangement").innerHTML = `
    <div class="tag-row">${(arr.palette || []).map(i => `<span class="tag">${esc(i)}</span>`).join("")}</div>
    <p style="color:var(--text-muted);font-size:.82rem;margin-top:.5rem">${esc(arr.density_guidance || "")}</p>
  `;
}

/* ── Flow ───────────────────────────────────── */
function renderFlow(flow) {
  const rd  = flow.readiness                || {};
  const md  = flow.metadata                 || {};
  const lj  = flow.listener_journey        || {};
  const fs  = flow.format_suitability      || {};
  const asp = flow.artist_statement_prompts || {};

  const checks = rd.checks || [];
  el("flowReadiness").innerHTML = `
    <div style="margin-bottom:.5rem">
      ${dl([["Ready", rd.is_ready ? "✓ Yes" : "Not yet"], ["Score", fmt2(rd.readiness_score)]])}
    </div>
    ${checks.map(c => `
      <div class="check-item">
        <span class="check-icon ${c.passed ? "pass" : "fail"}">${c.passed ? "✓" : "○"}</span>
        <div>
          <strong style="font-size:.82rem">${esc(c.check.replace(/_/g," "))}</strong>
          <p class="check-note">${esc(c.note)}</p>
        </div>
      </div>`).join("")}
  `;

  el("flowMetadata").innerHTML = `
    <div class="tag-row" style="margin-bottom:.5rem">
      ${(md.mood_tags || []).map(t => `<span class="tag accent">${esc(t)}</span>`).join("")}
    </div>
    ${dl([
      ["Genre hints",  (md.genre_hints || []).join(", ")           || "—"],
      ["Length",       md.length_category                          || "—"],
      ["Title words",  (md.suggested_title_words || []).join(", ") || "—"],
    ])}
  `;

  const stages = lj.journey_stages || [];
  el("flowJourney").innerHTML = `
    ${dl([["Overall", lj.overall_journey || "—"], ["Intimacy", lj.intimacy_level || "—"]])}
    <div style="margin-top:.5rem">
      ${stages.map(s => `
        <div class="ancestor-card">
          <h4>${esc(s.lines_range)}: ${esc(s.emotional_state)}</h4>
          <p class="exemplars">${esc(s.narrative)}</p>
        </div>`).join("")}
    </div>
  `;

  const fmtScores = fs.format_scores || {};
  const primary   = fs.primary_format || "—";
  el("flowFormat").innerHTML = `
    <p style="font-size:.9rem;margin-bottom:.5rem"><strong>${esc(primary)}</strong></p>
    ${Object.entries(fmtScores).map(([k, v]) => `
      <div class="score-bar-wrap" style="margin-bottom:.3rem">
        <span style="font-size:.78rem;color:var(--text-muted);min-width:80px">${esc(k)}</span>
        <div class="score-bar"><div class="score-bar-fill" style="width:${(v*100).toFixed(0)}%"></div></div>
        <span class="score-label">${fmt2(v)}</span>
      </div>`).join("")}
  `;

  const allPrompts = [...(asp.core_prompts || []), ...(asp.tailored_prompts || [])];
  el("flowPrompts").innerHTML = allPrompts.length
    ? allPrompts.map(p => `<div class="prompt-item">${esc(p)}</div>`).join("")
    : `<p style="color:var(--text-muted);font-size:.85rem">—</p>`;
}

/* ── Custody ────────────────────────────────── */
function renderCustody(cust) {
  const fp  = cust.fingerprint      || {};
  const cr  = cust.custody_record   || {};
  const lin = cust.lineage           || {};
  const leg = cust.legacy_annotation || {};

  const fpc = fp.fingerprint_components || {};
  el("custodyFingerprint").innerHTML = `
    <dt>Identity hash</dt>
    <dd style="font-family:monospace;font-size:.72rem;word-break:break-all">${esc((fp.identity_hash || "").slice(0,16) + "…")}</dd>
    ${dl([
      ["Form",     fpc.form          || "—"],
      ["Arc",      fpc.arc_direction || "—"],
      ["Symmetry", fpc.symmetry      || "—"],
      ["Refrain",  fpc.has_refrain   ? "Yes" : "No"],
      ["Rhyme",    fmt2(fpc.rhyme_density)],
    ])}
  `;

  el("custodyRecord").innerHTML = dl([
    ["Version", cr.version         || "—"],
    ["Artist",  cr.declared_artist  || "—"],
    ["Context", cr.creation_context || "—"],
    ["Form",    (cr.art_genome_summary || {}).form_type || "—"],
    ["Note",    cr.record_note       || "—"],
  ]);

  const traditions = lin.detected_traditions || [];
  el("custodyLineage").innerHTML = `
    <p style="font-size:.82rem;color:var(--text-muted);margin-bottom:.5rem">Primary: <strong>${esc(lin.primary_tradition || "—")}</strong></p>
    ${traditions.map(t => `
      <div class="ancestor-card">
        <h4>${esc(t.tradition)} <span style="color:var(--text-dim);font-weight:400">(${fmt2(t.confidence)})</span></h4>
        <p class="exemplars">${esc(t.description || "")}</p>
      </div>`).join("")}
    <p style="font-size:.78rem;color:var(--text-dim);margin-top:.4rem">${esc(lin.lineage_note || "")}</p>
  `;

  el("custodyLegacy").innerHTML = dl([
    ["Identity",  leg.artistic_identity  || "—"],
    ["Intent",    leg.emotional_intent   || "—"],
    ["Context",   leg.creation_context   || "—"],
    ["Tradition", leg.formal_tradition   || "—"],
  ]);
}

/* ── Temporal ───────────────────────────────── */
function renderTemporal(temp) {
  const tm  = temp.temporal_meaning         || {};
  const ep  = temp.ephemeral_classification || {};
  const anc = temp.creative_ancestry        || {};
  const cp  = temp.cultural_preservation    || {};

  el("temporalMeaning").innerHTML = dl([
    ["Anchoring",       tm.temporal_anchoring  || "—"],
    ["Temporal words",  tm.temporal_word_count  !== undefined ? tm.temporal_word_count  : "—"],
    ["Timeless words",  tm.timeless_word_count  !== undefined ? tm.timeless_word_count  : "—"],
    ["Cultural spec.",  tm.cultural_specificity || "—"],
    ["Specific words",  (tm.cultural_specific_words || []).join(", ") || "none"],
  ]);

  el("temporalEphemeral").innerHTML = `
    <div class="score-bar-wrap" style="margin-bottom:.5rem">
      <div class="score-bar"><div class="score-bar-fill" style="width:${((ep.ephemeral_score||0)*100).toFixed(0)}%"></div></div>
      <span class="score-label">${fmt2(ep.ephemeral_score)}</span>
    </div>
    ${dl([["Is ephemeral", ep.is_ephemeral ? "Yes" : "No"]])}
    <div class="tag-row" style="margin-top:.4rem">
      ${(ep.indicators || []).map(i => `<span class="tag">${esc(i)}</span>`).join("")}
    </div>
    <p style="font-size:.78rem;color:var(--text-dim);margin-top:.5rem">${esc(ep.ephemeral_note || "")}</p>
  `;

  const ancestors = anc.ancestors || [];
  el("temporalAncestry").innerHTML = `
    <p style="font-size:.82rem;color:var(--text-muted);margin-bottom:.5rem">Primary: <strong>${esc(anc.primary_ancestor || "—")}</strong></p>
    ${ancestors.map(a => `
      <div class="ancestor-card">
        <h4>${esc(a.tradition)}</h4>
        <p class="exemplars">${esc((a.exemplars || []).join(", "))}</p>
        <p class="exemplars" style="margin-top:.2rem">${esc(a.inheritance || "")}</p>
      </div>`).join("")}
    <p style="font-size:.78rem;color:var(--text-dim);margin-top:.4rem">${esc(anc.ancestry_note || "")}</p>
  `;

  const priority = cp.preservation_priority || "—";
  const pColor   = priority === "high" ? "var(--accent)"
                 : priority === "moderate" ? "var(--positive)"
                 : "var(--text-muted)";
  el("temporalPreservation").innerHTML = `
    <p style="font-size:1rem;font-weight:700;color:${pColor};margin-bottom:.4rem">${esc(priority.toUpperCase())}</p>
    ${dl([
      ["Medium",  cp.transmission_medium || "—"],
      ["Context", cp.cultural_context    || "—"],
    ])}
    <div class="tag-row" style="margin-top:.4rem">
      ${(cp.preservation_reasons || []).map(r => `<span class="tag">${esc(r)}</span>`).join("")}
    </div>
  `;
}

/* ──────────────────────────────────────────────
   Copy raw JSON
────────────────────────────────────────────── */
function copyRaw() {
  if (!_lastResponse) return;
  navigator.clipboard.writeText(JSON.stringify(_lastResponse, null, 2))
    .then(() => setStatus("Copied to clipboard."))
    .catch(() => setStatus("Copy failed — try selecting and copying manually.", true));
}

/* ──────────────────────────────────────────────
   Helpers
────────────────────────────────────────────── */
function el(id) { return document.getElementById(id); }
function show(id) { el(id)?.classList.remove("hidden"); }
function hide(id) { el(id)?.classList.add("hidden"); }

function setStatus(msg, isError = false) {
  const s = el("statusMsg");
  if (!s) return;
  s.textContent = msg;
  s.className = "status-msg" + (isError ? " error" : "");
}

function esc(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function fmt2(v) {
  if (v === null || v === undefined || v === "") return "—";
  const n = parseFloat(v);
  return isNaN(n) ? String(v) : n.toFixed(2);
}

function dl(pairs) {
  return pairs.map(([k, v]) =>
    `<dt>${esc(k)}</dt><dd>${v !== null && v !== undefined ? v : "—"}</dd>`
  ).join("");
}

function scoreBar(score) {
  const pct = Math.min(Math.max((parseFloat(score) || 0) * 100, 0), 100).toFixed(0);
  return `<span class="score-bar-wrap" style="display:inline-flex;align-items:center;gap:4px;min-width:80px">
    <span class="score-bar" style="flex:1;height:5px;background:var(--border);border-radius:3px;overflow:hidden">
      <span class="score-bar-fill" style="display:block;height:100%;width:${pct}%;background:var(--accent);border-radius:3px"></span>
    </span>
    <span style="font-size:.78rem;color:var(--text-muted)">${fmt2(score)}</span>
  </span>`;
}

function arcBar(score) {
  const s          = parseFloat(score) || 0;
  const neutral_px = 24;
  const h          = Math.round(neutral_px + s * neutral_px);
  const clamp      = Math.min(Math.max(h, 4), 48);
  const hue        = Math.round(240 + s * 60); // blue → warm
  return `<div class="arc-bar" style="height:${clamp}px;background:hsl(${hue},65%,55%)"></div>`;
}

/* ══════════════════════════════════════════════
   Initialisation
══════════════════════════════════════════════ */

document.addEventListener("DOMContentLoaded", () => {
  loadSavedTheme();
  initPWA();
  _loadSession();
  _updateUserUI();

  // If a valid session exists, skip auth screen
  if (_authToken && _currentUser) {
    showApp();
  } else {
    showAuth();
  }
});

/* ══════════════════════════════════════════════
   VISUAL STUDIO
══════════════════════════════════════════════ */

// Studio mode switcher
function switchStudio(mode) {
  const textStudio = el("textStudio");
  const visualStudio = el("visualStudio");
  const textBtn = el("textStudioBtn");
  const visualBtn = el("visualStudioBtn");
  if (mode === "visual") {
    textStudio.style.display = "none";
    visualStudio.style.display = "block";
    textBtn.classList.remove("active");
    visualBtn.classList.add("active");
    if (!_paintInitDone) initPaintCanvas();
    if (!_logoInitDone) initLogoCanvas();
  } else {
    textStudio.style.display = "";
    visualStudio.style.display = "none";
    textBtn.classList.add("active");
    visualBtn.classList.remove("active");
  }
}

function switchVisualTab(tab) {
  document.querySelectorAll(".visual-tab").forEach(t => t.classList.remove("active"));
  document.querySelectorAll(".visual-pane").forEach(p => p.classList.add("hidden"));
  document.querySelector(`[data-vtab="${tab}"]`).classList.add("active");
  el(`vpane-${tab}`).classList.remove("hidden");
}

// ── Paint / Sketch Canvas ──────────────────────────────────────────────────

let _paintInitDone = false;
let _paintCtx = null;
let _paintCanvas = null;
let _painting = false;
let _paintTool = "pencil";
let _paintSize = 6;
let _paintOpacity = 1;
let _paintColor = "#7c5af1";
let _paintFill = "#ffffff";
let _paintHistory = [];
let _paintStartX = 0;
let _paintStartY = 0;
let _paintSnapshot = null;

function initPaintCanvas() {
  _paintCanvas = el("paintCanvas");
  _paintCtx = _paintCanvas.getContext("2d");
  _paintCtx.fillStyle = "#ffffff";
  _paintCtx.fillRect(0, 0, _paintCanvas.width, _paintCanvas.height);
  _paintHistory.push(_paintCtx.getImageData(0, 0, _paintCanvas.width, _paintCanvas.height));

  _paintCanvas.addEventListener("mousedown", paintStart);
  _paintCanvas.addEventListener("mousemove", paintMove);
  _paintCanvas.addEventListener("mouseup", paintEnd);
  _paintCanvas.addEventListener("mouseleave", paintEnd);
  _paintCanvas.addEventListener("touchstart", e => { e.preventDefault(); paintStart(e.touches[0]); }, { passive: false });
  _paintCanvas.addEventListener("touchmove", e => { e.preventDefault(); paintMove(e.touches[0]); }, { passive: false });
  _paintCanvas.addEventListener("touchend", e => { e.preventDefault(); paintEnd(); }, { passive: false });
  _paintInitDone = true;
}

function _paintPos(evt) {
  const r = _paintCanvas.getBoundingClientRect();
  const scaleX = _paintCanvas.width / r.width;
  const scaleY = _paintCanvas.height / r.height;
  return { x: (evt.clientX - r.left) * scaleX, y: (evt.clientY - r.top) * scaleY };
}

function paintStart(evt) {
  _painting = true;
  const { x, y } = _paintPos(evt);
  _paintStartX = x; _paintStartY = y;
  _paintSnapshot = _paintCtx.getImageData(0, 0, _paintCanvas.width, _paintCanvas.height);
  if (_paintTool === "pencil" || _paintTool === "brush" || _paintTool === "eraser") {
    _paintCtx.beginPath();
    _paintCtx.moveTo(x, y);
  }
}

function paintMove(evt) {
  if (!_painting) return;
  const { x, y } = _paintPos(evt);
  _paintCtx.globalAlpha = _paintOpacity;
  if (_paintTool === "eraser") {
    _paintCtx.globalCompositeOperation = "destination-out";
    _paintCtx.lineWidth = _paintSize * 2;
    _paintCtx.lineTo(x, y); _paintCtx.stroke();
    return;
  }
  _paintCtx.globalCompositeOperation = "source-over";
  _paintCtx.strokeStyle = _paintColor;
  _paintCtx.fillStyle = _paintFill;
  if (_paintTool === "pencil") {
    _paintCtx.lineWidth = _paintSize;
    _paintCtx.lineCap = "round";
    _paintCtx.lineJoin = "round";
    _paintCtx.lineTo(x, y); _paintCtx.stroke();
  } else if (_paintTool === "brush") {
    _paintCtx.lineWidth = _paintSize * 2.5;
    _paintCtx.lineCap = "round";
    _paintCtx.lineJoin = "round";
    _paintCtx.lineTo(x, y); _paintCtx.stroke();
  } else if (_paintTool === "line" || _paintTool === "rect" || _paintTool === "circle") {
    _paintCtx.putImageData(_paintSnapshot, 0, 0);
    _paintCtx.globalAlpha = _paintOpacity;
    _paintCtx.lineWidth = _paintSize;
    _paintCtx.strokeStyle = _paintColor;
    _paintCtx.fillStyle = _paintFill;
    _paintCtx.beginPath();
    if (_paintTool === "line") {
      _paintCtx.moveTo(_paintStartX, _paintStartY);
      _paintCtx.lineTo(x, y);
      _paintCtx.stroke();
    } else if (_paintTool === "rect") {
      _paintCtx.rect(_paintStartX, _paintStartY, x - _paintStartX, y - _paintStartY);
      _paintCtx.fill(); _paintCtx.stroke();
    } else {
      const rx = Math.abs(x - _paintStartX) / 2, ry = Math.abs(y - _paintStartY) / 2;
      _paintCtx.ellipse(_paintStartX + (x - _paintStartX) / 2, _paintStartY + (y - _paintStartY) / 2, rx, ry, 0, 0, Math.PI * 2);
      _paintCtx.fill(); _paintCtx.stroke();
    }
  }
}

function paintEnd() {
  if (!_painting) return;
  _painting = false;
  _paintCtx.globalAlpha = 1;
  _paintCtx.globalCompositeOperation = "source-over";
  _paintCtx.closePath();
  _paintHistory.push(_paintCtx.getImageData(0, 0, _paintCanvas.width, _paintCanvas.height));
  if (_paintHistory.length > 25) _paintHistory.shift();
}

function selectPaintTool(tool) {
  _paintTool = tool;
  document.querySelectorAll("[id^='tool-']").forEach(b => b.classList.remove("active"));
  const btn = el(`tool-${tool}`);
  if (btn) btn.classList.add("active");
}
function updatePaintSize(v) { _paintSize = parseInt(v); el("paintSizeLabel").textContent = v; }
function updatePaintOpacity(v) { _paintOpacity = parseInt(v) / 100; el("paintOpacityLabel").textContent = v + "%"; }
document.addEventListener("DOMContentLoaded", () => {
  const pc = el("paintColor"); if (pc) pc.addEventListener("input", e => { _paintColor = e.target.value; });
  const pf = el("paintFill"); if (pf) pf.addEventListener("input", e => { _paintFill = e.target.value; });
});
function undoPaint() {
  if (_paintHistory.length <= 1) return;
  _paintHistory.pop();
  _paintCtx.putImageData(_paintHistory[_paintHistory.length - 1], 0, 0);
}
function clearPaintCanvas() {
  _paintCtx.fillStyle = "#ffffff";
  _paintCtx.fillRect(0, 0, _paintCanvas.width, _paintCanvas.height);
  _paintHistory = [_paintCtx.getImageData(0, 0, _paintCanvas.width, _paintCanvas.height)];
}
function downloadCanvas(canvasId, name) {
  const c = el(canvasId);
  const a = document.createElement("a");
  a.download = name + ".png";
  a.href = c.toDataURL("image/png");
  a.click();
}

// ── Photo Editor ───────────────────────────────────────────────────────────

let _photoOriginalImage = null;
let _photoRotation = 0;
let _photoFlipH = false;
let _photoFlipV = false;

function handlePhotoDrop(e) {
  e.preventDefault();
  const file = e.dataTransfer.files[0];
  if (file && file.type.startsWith("image/")) loadPhotoFile(file);
}

function loadPhotoFile(file) {
  if (!file) return;
  const reader = new FileReader();
  reader.onload = ev => {
    const img = new Image();
    img.onload = () => {
      _photoOriginalImage = img;
      _photoRotation = 0; _photoFlipH = false; _photoFlipV = false;
      el("photoPreview").src = ev.target.result;
      el("photoPreviewWrap").classList.remove("hidden");
      el("photoUploadZone").classList.add("has-image");
      el("photoFilterPanel").classList.remove("hidden");
      applyPhotoFilters();
    };
    img.src = ev.target.result;
  };
  reader.readAsDataURL(file);
}

function applyPhotoFilters() {
  if (!_photoOriginalImage) return;
  const brightness = el("fBrightness").value;
  const contrast   = el("fContrast").value;
  const saturation = el("fSaturation").value;
  const hue        = el("fHue").value;
  const blur       = el("fBlur").value;
  const sepia      = el("fSepia").value;
  const grayscale  = el("fGrayscale").value;
  const invert     = el("fInvert").value;

  el("brightnessVal").textContent = brightness + "%";
  el("contrastVal").textContent   = contrast + "%";
  el("saturationVal").textContent = saturation + "%";
  el("hueVal").textContent        = hue + "°";
  el("blurVal").textContent       = blur + "px";
  el("sepiaVal").textContent      = sepia + "%";
  el("grayscaleVal").textContent  = grayscale + "%";
  el("invertVal").textContent     = invert + "%";

  const filterStr = `brightness(${brightness}%) contrast(${contrast}%) saturate(${saturation}%) hue-rotate(${hue}deg) blur(${blur}px) sepia(${sepia}%) grayscale(${grayscale}%) invert(${invert}%)`;
  el("photoPreview").style.filter = filterStr;

  // Render to canvas for download
  const img = _photoOriginalImage;
  const canvas = el("photoCanvas");
  canvas.width = img.naturalWidth;
  canvas.height = img.naturalHeight;
  const ctx = canvas.getContext("2d");
  ctx.filter = filterStr;
  ctx.save();
  ctx.translate(canvas.width / 2, canvas.height / 2);
  if (_photoFlipH) ctx.scale(-1, 1);
  if (_photoFlipV) ctx.scale(1, -1);
  ctx.rotate(_photoRotation * Math.PI / 180);
  ctx.drawImage(img, -img.naturalWidth / 2, -img.naturalHeight / 2);
  ctx.restore();
}

function resetPhotoFilters() {
  ["fBrightness","fContrast","fSaturation"].forEach(id => el(id).value = 100);
  ["fHue","fBlur","fSepia","fGrayscale","fInvert"].forEach(id => el(id).value = 0);
  _photoRotation = 0; _photoFlipH = false; _photoFlipV = false;
  applyPhotoFilters();
}
function flipPhoto(axis) {
  if (axis === "h") _photoFlipH = !_photoFlipH;
  else _photoFlipV = !_photoFlipV;
  applyPhotoFilters();
}
function rotatePhoto(deg) {
  _photoRotation = (_photoRotation + deg) % 360;
  applyPhotoFilters();
}

// ── Video Editor ───────────────────────────────────────────────────────────

let _videoAnnotations = [];

function loadVideoFile(file) {
  if (!file) return;
  const url = URL.createObjectURL(file);
  const vid = el("videoPlayer");
  vid.src = url;
  el("videoUploadZone").classList.add("has-video");
  el("videoPlayerSection").classList.remove("hidden");
}
function setVideoSpeed(v) { el("videoPlayer").playbackRate = parseFloat(v); }
function snapVideoFrame() {
  const vid = el("videoPlayer");
  const c = document.createElement("canvas");
  c.width = vid.videoWidth; c.height = vid.videoHeight;
  c.getContext("2d").drawImage(vid, 0, 0);
  const a = document.createElement("a");
  a.download = "kala-frame.png"; a.href = c.toDataURL("image/png"); a.click();
}
function addVideoAnnotation() {
  const input = el("annotationInput");
  const text = input.value.trim();
  if (!text) return;
  const vid = el("videoPlayer");
  const t = isNaN(vid.currentTime) ? 0 : vid.currentTime;
  const mins = String(Math.floor(t / 60)).padStart(2, "0");
  const secs = String(Math.floor(t % 60)).padStart(2, "0");
  const ts = `${mins}:${secs}`;
  _videoAnnotations.push({ ts, t, text });
  _videoAnnotations.sort((a, b) => a.t - b.t);
  renderAnnotationList();
  input.value = "";
}
function renderAnnotationList() {
  const list = el("annotationList");
  list.innerHTML = _videoAnnotations.map((a, i) =>
    `<div class="annotation-item">
      <span class="annotation-time">${esc(a.ts)}</span>
      <span class="annotation-text">${esc(a.text)}</span>
      <button class="annotation-del" onclick="deleteAnnotation(${i})" aria-label="Delete">✕</button>
    </div>`
  ).join("");
}
function deleteAnnotation(i) { _videoAnnotations.splice(i, 1); renderAnnotationList(); }
function exportAnnotations() {
  const blob = new Blob([JSON.stringify(_videoAnnotations, null, 2)], { type: "application/json" });
  const a = document.createElement("a"); a.download = "kala-annotations.json";
  a.href = URL.createObjectURL(blob); a.click();
}

// ── Logo Maker ─────────────────────────────────────────────────────────────

let _logoInitDone = false;
let _logoShapes = [];

function initLogoCanvas() {
  _logoInitDone = true;
  renderLogo();
}
function addLogoShape(type) {
  _logoShapes.push({ type, color: el("logoShapeColor").value, x: 300, y: 200, r: 60 });
  renderLogo();
}
function clearLogo() { _logoShapes = []; renderLogo(); }
function renderLogo() {
  const c = el("logoCanvas"); if (!c) return;
  const ctx = c.getContext("2d");
  const bg = el("logoBgColor").value;
  ctx.fillStyle = bg; ctx.fillRect(0, 0, c.width, c.height);

  _logoShapes.forEach(s => {
    ctx.fillStyle = s.color;
    ctx.beginPath();
    if (s.type === "circle") {
      ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
    } else if (s.type === "rect") {
      ctx.rect(s.x - s.r, s.y - s.r, s.r * 2, s.r * 2);
    } else if (s.type === "star") {
      drawStar(ctx, s.x, s.y, 5, s.r, s.r * 0.45);
    } else if (s.type === "hex") {
      drawPolygon(ctx, s.x, s.y, s.r, 6);
    }
    ctx.fill();
  });

  const text  = el("logoText") ? el("logoText").value : "";
  const fsize = parseInt(el("logoFontSize") ? el("logoFontSize").value : 72) || 72;
  const font  = el("logoFont") ? el("logoFont").value : "Inter, sans-serif";
  const bold  = el("logoBold") && el("logoBold").checked ? "bold " : "";
  const ital  = el("logoItalic") && el("logoItalic").checked ? "italic " : "";
  const tx    = parseInt(el("logoTextX") ? el("logoTextX").value : 300);
  const ty    = parseInt(el("logoTextY") ? el("logoTextY").value : 200);
  ctx.font = `${ital}${bold}${fsize}px ${font}`;
  ctx.fillStyle = el("logoTextColor") ? el("logoTextColor").value : "#7c5af1";
  ctx.textAlign = "center"; ctx.textBaseline = "middle";
  if (text) ctx.fillText(text, tx, ty);
}
function drawStar(ctx, cx, cy, spikes, outerR, innerR) {
  let rot = (Math.PI / 2) * 3, step = Math.PI / spikes;
  ctx.moveTo(cx, cy - outerR);
  for (let i = 0; i < spikes; i++) {
    ctx.lineTo(cx + Math.cos(rot) * outerR, cy + Math.sin(rot) * outerR); rot += step;
    ctx.lineTo(cx + Math.cos(rot) * innerR, cy + Math.sin(rot) * innerR); rot += step;
  }
  ctx.lineTo(cx, cy - outerR); ctx.closePath();
}
function drawPolygon(ctx, cx, cy, r, sides) {
  ctx.moveTo(cx + r * Math.cos(0), cy + r * Math.sin(0));
  for (let i = 1; i <= sides; i++) {
    const a = (i * 2 * Math.PI) / sides;
    ctx.lineTo(cx + r * Math.cos(a), cy + r * Math.sin(a));
  }
  ctx.closePath();
}
function downloadLogoSVG() {
  const c = el("logoCanvas");
  const text  = el("logoText").value;
  const fsize = el("logoFontSize").value;
  const font  = el("logoFont").value.split(",")[0].replace(/'/g, "");
  const color = el("logoTextColor").value;
  const bg    = el("logoBgColor").value;
  const tx    = el("logoTextX").value;
  const ty    = el("logoTextY").value;
  const bold  = el("logoBold").checked ? "bold" : "normal";
  const ital  = el("logoItalic").checked ? "italic" : "normal";
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${c.width}" height="${c.height}">
  <rect width="100%" height="100%" fill="${esc(bg)}"/>
  <text x="${tx}" y="${ty}" font-family="${esc(font)}" font-size="${fsize}" fill="${esc(color)}" font-weight="${bold}" font-style="${ital}" text-anchor="middle" dominant-baseline="middle">${esc(text)}</text>
</svg>`;
  const a = document.createElement("a");
  a.download = "kala-logo.svg";
  a.href = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
  a.click();
}

// ── Visual Analysis via /visual endpoint ───────────────────────────────────

async function analyseVisualWork(mode) {
  const mediumMap = { paint: el("paintMedium")?.value || "painting", photo: "photo", video: "video", logo: "logo" };
  const descMap   = { paint: "paintDesc", photo: "photoDesc", video: "videoDesc", logo: "logoDesc" };
  const resMap    = { paint: "paintAnalysisResult", photo: "photoAnalysisResult", video: "videoAnalysisResult", logo: "logoAnalysisResult" };

  const desc = el(descMap[mode])?.value.trim();
  const resultEl = el(resMap[mode]);
  if (!desc) { resultEl.innerHTML = '<p style="color:var(--negative);font-size:.83rem">Please add a description first.</p>'; resultEl.classList.remove("hidden"); return; }

  resultEl.innerHTML = '<p style="color:var(--text-muted);font-size:.83rem">Analysing…</p>';
  resultEl.classList.remove("hidden");

  const palette = mode === "paint" ? (el("paintPalette")?.value || "").split(",").map(s => s.trim()).filter(Boolean) : [];
  const body = { description: desc, medium: mediumMap[mode] };
  if (palette.length) body.color_palette = palette;

  try {
    const resp = await fetch(`${_BASE_URL}/visual`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!resp.ok) { const e = await resp.json().catch(() => ({})); throw new Error(e.detail || resp.statusText); }
    const data = await resp.json();
    resultEl.innerHTML = renderVisualAnalysis(data);
  } catch (err) {
    resultEl.innerHTML = `<p style="color:var(--negative);font-size:.83rem">Analysis error: ${esc(String(err.message || err))}</p>`;
  }
}

function renderVisualAnalysis(d) {
  const tag = (t) => `<span class="tag">${esc(t)}</span>`;
  const tags = (arr) => Array.isArray(arr) ? arr.map(tag).join("") : "";

  const colourCard = d.colour && d.colour.palette_size > 0 ? `
    <div class="visual-card">
      <h4>Colour</h4>
      <p><strong>${esc(d.colour.colour_harmony || "—")}</strong> harmony · ${esc(d.colour.dominant_temperature || "—")} · ${esc(d.colour.saturation || "—")}</p>
      <p style="margin-top:.3rem;font-size:.78rem;color:var(--text-muted)">${esc(d.colour.insight || "")}</p>
    </div>` : "";

  const compCard = `
    <div class="visual-card">
      <h4>Composition</h4>
      <p>${esc(d.composition.balance || "—")}</p>
      <div class="tag-list">${tags(d.composition.detected_elements)}</div>
    </div>`;

  const styleCard = `
    <div class="visual-card">
      <h4>Style</h4>
      <p><strong>${esc(d.style.primary_style || "—")}</strong> <span style="color:var(--text-muted);font-size:.78rem">(${esc(d.style.detection_confidence)} confidence)</span></p>
      <div class="tag-list">${tags(d.style.style_influences)}</div>
    </div>`;

  const emoCard = `
    <div class="visual-card">
      <h4>Emotion &amp; Intent</h4>
      <p>${esc(d.emotion.primary_register || "—")} · ${esc(d.intent.primary_intent || "—")}</p>
      <div class="tag-list">${tags(d.emotion.secondary_registers)}</div>
    </div>`;

  const preserveCard = `
    <div class="visual-card">
      <h4>Preservation</h4>
      ${(d.preservation.digital || []).slice(0, 2).map(r => `<p style="font-size:.78rem">💾 ${esc(r)}</p>`).join("")}
    </div>`;

  return `
    <p style="font-size:.83rem;color:var(--text-muted);margin:.5rem 0 .3rem">${esc(d.summary || "")}</p>
    <div class="visual-analysis-grid">
      ${compCard}${styleCard}${emoCard}${colourCard}${preserveCard}
    </div>`;
}
