/**
 * KalaOS Studio — Frontend Application
 *
 * Communicates with the KalaOS backend (default: http://localhost:8000).
 * Uses the POST /deep-analysis endpoint for the primary Full Analysis flow.
 * All results are rendered in-page; no data is sent anywhere else.
 *
 * No build step required — plain ES2020 JavaScript.
 *
 * To point the UI at a different backend, set the global before this script
 * loads:
 *   <script>window.KALA_API_BASE = "https://your-backend.example.com";</script>
 */

/* ──────────────────────────────────────────────
   Configuration
────────────────────────────────────────────── */
const API_BASE = (typeof window !== "undefined" && window.KALA_API_BASE) || "http://localhost:8000";

/* ──────────────────────────────────────────────
   State
────────────────────────────────────────────── */
let _lastResponse = null;

/* ──────────────────────────────────────────────
   Core: run deep analysis
────────────────────────────────────────────── */
async function runDeepAnalysis() {
  const text = el("artText").value.trim();
  if (!text) {
    setStatus("Please enter some text first.", true);
    return;
  }

  const domain      = el("artDomain").value;
  const artistName  = el("artistName").value.trim() || null;
  const model       = el("ollamaModel").value.trim() || "llama3";

  setStatus("Analysing…");
  el("analyseBtn").disabled = true;

  try {
    const resp = await fetch(`${API_BASE}/deep-analysis`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text,
        art_domain:      domain,
        artist_name:     artistName,
        model:           model,
      }),
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

/* ──────────────────────────────────────────────
   Clear
────────────────────────────────────────────── */
function clearAll() {
  el("artText").value = "";
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

  // Narrative
  if (data.narrative && !data.narrative.startsWith("[LLM unavailable")) {
    el("narrativeText").textContent = data.narrative;
    show("narrativeSection");
  } else {
    hide("narrativeSection");
  }

  // Genome
  el("overviewGenome").innerHTML = dl([
    ["Form",          genome.form_type          || "—"],
    ["Rhyme density", fmt2(genome.rhyme_density)],
    ["Complexity",    fmt2(genome.complexity_score)],
    ["Creative risk", fmt2(genome.creative_risk_index)],
    ["Symmetry",      genome.symmetry_score >= 1 ? "Yes" : "No"],
    ["Cognitive load",fmt2(genome.cognitive_load)],
  ]);

  // Emotional arc sparkline
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

  // Existential
  const cr = existential.creation_reason || {};
  const sv = existential.survival        || {};
  const ne = existential.emotional_necessity || {};
  el("overviewExistential").innerHTML = dl([
    ["Created for",     cr.primary_reason        || "—"],
    ["Survival-driven", sv.is_survival_driven ? "Yes" : "No"],
    ["Necessity score", fmt2(ne.necessity_score)],
    ["Necessity label", ne.necessity_label        || "—"],
  ]);

  // Human-irreducible zones
  const irr = existential.human_irreducibility || {};
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
    ["Dominant meter",  mf.dominant_meter  || "—"],
    ["Meter regularity",fmt2(mf.meter_regularity)],
    ["Stress patterns", (mf.stress_patterns || []).join(", ") || "—"],
  ]);

  // Breath points
  const breathPos = bp.breath_positions || [];
  el("craftBreath").innerHTML = breathPos.length
    ? `<div class="tag-row">${breathPos.map(b => `<span class="tag">${esc(b)}</span>`).join("")}</div>`
    : `<p style="color:var(--text-muted);font-size:.85rem">No prominent breath points detected.</p>`;

  // Line density
  const densities = ld.line_densities || [];
  el("craftDensity").innerHTML = densities.length
    ? `<div class="tag-row">${densities.map(d =>
        `<span class="tag">${esc(d.line ? d.line.slice(0, 24) : "—")} <em style="color:var(--accent)">${fmt2(d.density)}</em></span>`
      ).join("")}</div>`
    : `<p style="color:var(--text-muted);font-size:.85rem">—</p>`;

  // Semantic drift
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
    ["Score",      scoreBar(mem.memorability_score)],
    ["Hook density", fmt2(mem.hook_density)],
    ["Refrain count", mem.refrain_count !== undefined ? mem.refrain_count : "—"],
    ["Notes",      (mem.memorability_notes || []).join(" ") || "—"],
  ]);

  el("signalLongevity").innerHTML = dl([
    ["Score",      scoreBar(lon.longevity_score)],
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

  // Sections
  const sections = ms.sections || [];
  el("composeSections").innerHTML = sections.length
    ? sections.map(s => `
        <div class="section-block">
          <span class="section-role role-${s.role}">${s.role}</span>
          <span class="section-lines">${(s.lines || []).map(l => esc(l.slice(0,40))).join(" / ")}</span>
        </div>`).join("")
    : `<p style="color:var(--text-muted);font-size:.85rem">—</p>`;

  // Chords
  const prims = (cs.primary_progressions || []).map(p => `${p.progression} — <em>${p.feel}</em>`).join("<br>");
  el("composeChords").innerHTML = dl([
    ["Scale quality",  cs.scale_quality || "—"],
    ["Scale name",     cs.scale_name    || "—"],
    ["Primary",        prims || "—"],
    ["Key options",    (cs.key_note_suggestions || []).join(", ") || "—"],
  ]);

  el("composeTempo").innerHTML = dl([
    ["BPM range",   tp.bpm_range ? tp.bpm_range.join("–") : "—"],
    ["Feel",        tp.feel || "—"],
    ["Time sig",    (tp.time_signature_suggestions || []).join("; ") || "—"],
  ]);

  // Arrangement
  el("composeArrangement").innerHTML = `
    <div class="tag-row">${(arr.palette || []).map(i => `<span class="tag">${esc(i)}</span>`).join("")}</div>
    <p style="color:var(--text-muted);font-size:.82rem;margin-top:.5rem">${esc(arr.density_guidance || "")}</p>
  `;
}

/* ── Flow ───────────────────────────────────── */
function renderFlow(flow) {
  const rd  = flow.readiness                  || {};
  const md  = flow.metadata                   || {};
  const lj  = flow.listener_journey           || {};
  const fs  = flow.format_suitability         || {};
  const asp = flow.artist_statement_prompts   || {};

  // Readiness checks
  const checks = rd.checks || [];
  el("flowReadiness").innerHTML = `
    <div style="margin-bottom:.5rem">
      ${dl([["Ready",  rd.is_ready ? "✓ Yes" : "Not yet"],
             ["Score",  fmt2(rd.readiness_score)]])}
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
      ["Genre hints",   (md.genre_hints || []).join(", ")    || "—"],
      ["Length",        md.length_category                   || "—"],
      ["Title words",   (md.suggested_title_words || []).join(", ") || "—"],
    ])}
  `;

  // Journey stages
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

  // Format
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

  // Statement prompts
  const allPrompts = [
    ...(asp.core_prompts     || []),
    ...(asp.tailored_prompts || []),
  ];
  el("flowPrompts").innerHTML = allPrompts.length
    ? allPrompts.map(p => `<div class="prompt-item">${esc(p)}</div>`).join("")
    : `<p style="color:var(--text-muted);font-size:.85rem">—</p>`;
}

/* ── Custody ────────────────────────────────── */
function renderCustody(cust) {
  const fp  = cust.fingerprint     || {};
  const cr  = cust.custody_record  || {};
  const lin = cust.lineage         || {};
  const leg = cust.legacy_annotation || {};

  const fpc = fp.fingerprint_components || {};
  el("custodyFingerprint").innerHTML = `
    <dt>Identity hash</dt>
    <dd style="font-family:monospace;font-size:.72rem;word-break:break-all">${esc((fp.identity_hash || "").slice(0,16) + "…")}</dd>
    ${dl([
      ["Form",        fpc.form         || "—"],
      ["Arc",         fpc.arc_direction || "—"],
      ["Symmetry",    fpc.symmetry     || "—"],
      ["Refrain",     fpc.has_refrain  ? "Yes" : "No"],
      ["Rhyme",       fmt2(fpc.rhyme_density)],
    ])}
  `;

  el("custodyRecord").innerHTML = dl([
    ["Version",       cr.version        || "—"],
    ["Artist",        cr.declared_artist || "—"],
    ["Context",       cr.creation_context || "—"],
    ["Form",          (cr.art_genome_summary || {}).form_type || "—"],
    ["Note",          cr.record_note     || "—"],
  ]);

  // Lineage
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
    ["Identity",      leg.artistic_identity  || "—"],
    ["Intent",        leg.emotional_intent   || "—"],
    ["Context",       leg.creation_context   || "—"],
    ["Tradition",     leg.formal_tradition   || "—"],
  ]);
}

/* ── Temporal ───────────────────────────────── */
function renderTemporal(temp) {
  const tm  = temp.temporal_meaning         || {};
  const ep  = temp.ephemeral_classification || {};
  const anc = temp.creative_ancestry        || {};
  const cp  = temp.cultural_preservation    || {};

  el("temporalMeaning").innerHTML = dl([
    ["Anchoring",       tm.temporal_anchoring      || "—"],
    ["Temporal words",  tm.temporal_word_count      !== undefined ? tm.temporal_word_count  : "—"],
    ["Timeless words",  tm.timeless_word_count      !== undefined ? tm.timeless_word_count  : "—"],
    ["Cultural spec.",  tm.cultural_specificity     || "—"],
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

  // Ancestry
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
  const priorityColour = priority === "high" ? "var(--accent)"
                       : priority === "moderate" ? "var(--positive)"
                       : "var(--text-muted)";
  el("temporalPreservation").innerHTML = `
    <p style="font-size:1rem;font-weight:700;color:${priorityColour};margin-bottom:.4rem">${esc(priority.toUpperCase())}</p>
    ${dl([
      ["Medium",   cp.transmission_medium  || "—"],
      ["Context",  cp.cultural_context     || "—"],
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
function show(id) { el(id).classList.remove("hidden"); }
function hide(id) { el(id).classList.add("hidden"); }

function setStatus(msg, isError = false) {
  const s = el("statusMsg");
  s.textContent = msg;
  s.className = "status-msg" + (isError ? " error" : "");
}

/** Escape HTML special chars */
function esc(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** Format a number to 2dp */
function fmt2(v) {
  if (v === null || v === undefined || v === "") return "—";
  const n = parseFloat(v);
  return isNaN(n) ? String(v) : n.toFixed(2);
}

/** Render a <dl> from an array of [key, value] pairs (values may contain raw HTML) */
function dl(pairs) {
  return pairs.map(([k, v]) =>
    `<dt>${esc(k)}</dt><dd>${v !== null && v !== undefined ? v : "—"}</dd>`
  ).join("");
}

/** Inline score bar (returns HTML string) */
function scoreBar(score) {
  const pct = Math.min(Math.max((parseFloat(score) || 0) * 100, 0), 100).toFixed(0);
  return `<span class="score-bar-wrap" style="display:inline-flex;align-items:center;gap:4px;min-width:80px">
    <span class="score-bar" style="flex:1;height:5px;background:var(--border);border-radius:3px;overflow:hidden">
      <span class="score-bar-fill" style="display:block;height:100%;width:${pct}%;background:var(--accent);border-radius:3px"></span>
    </span>
    <span style="font-size:.78rem;color:var(--text-muted)">${fmt2(score)}</span>
  </span>`;
}

/** Single arc bar element (returns HTML string) */
function arcBar(score) {
  const s = parseFloat(score) || 0;
  // height: 4px (neutral, 0) … 48px (max)
  const neutral_px = 24;
  const h = Math.round(neutral_px + s * neutral_px);
  const clamped = Math.max(4, Math.min(48, h));
  const col = s > 0.05 ? "var(--positive)" : s < -0.05 ? "var(--negative)" : "var(--neutral)";
  return `<div class="arc-bar" style="height:${clamped}px;background:${col}" title="${fmt2(s)}"></div>`;
}
