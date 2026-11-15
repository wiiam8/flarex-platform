"use strict";
const $ = (s, r = document) => r.querySelector(s), $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const S = { meta: null, inv: [], presets: [], story: null, sel: [], q: "", family: "all", fuel: "all", heat: null, weights: null,
  sc: { environment: "lunar", concern: "suppression", gravity: "lunar", fuel: "any", oxygen_pct: 30, pressure_psi: 10.2 },
  chat: [], ai: null, model: "", ds: "flex", group: null, chartInv: "all" };
const NAV = [["home", "Home"], ["explorer", "Investigations"], ["compare", "Compare"], ["simulator", "Mission simulator"], ["charts", "Data & coverage"], ["copilot", "AI copilot"], ["earth", "Earth applications"], ["timeline", "Why it matters"]];

function toast(m) { const t = document.createElement("div"); t.className = "toast"; t.setAttribute("role", "alert"); t.textContent = m; document.body.appendChild(t); setTimeout(() => t.remove(), 5000); }
async function api(path, body) {
  const r = await fetch(path, body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : undefined);
  if (!r.ok) { let m = r.statusText; try { const j = await r.json(); m = Array.isArray(j.detail) ? j.detail.map(x => x.msg).join("; ") : (j.detail || m); } catch (e) {} toast(m); throw new Error(m); }
  return r.json();
}
const pct = r => r ? `${(r[0] * 100).toFixed(0)}–${(r[1] * 100).toFixed(0)}%` : null;
const psi = r => r ? `${r[0].toFixed(1)}–${r[1].toFixed(1)} psi` : null;
const nr = v => v == null || v === "" ? '<span class="nr">Not reported</span>' : esc(v);
const head = (eyebrow, title, desc) => `<div class="pagehead"><div class="wrap"><div class="eyebrow">${esc(eyebrow)}</div><h1>${esc(title)}</h1><p>${esc(desc)}</p></div></div>`;
const wrap = h => `<div class="wrap" style="padding-top:24px">${h}</div>`;
const sourceLinks = r => r.links.map(l => `<a href="${esc(l.url)}" target="_blank" rel="noopener">${esc(l.label)} ↗</a>`).join(" · ") + (r.doi ? ` · <a href="https://doi.org/${esc(r.doi)}" target="_blank" rel="noopener">DOI ${esc(r.doi)} ↗</a>` : "");

/* ---------- charts (plain SVG, no external libraries) ---------- */
function heatSVG(d, marker, compact) {
  const W = 760, strip = d.o2_only_n ? 50 : 0, H = (compact ? 320 : 400) + strip, L = 54, R = 14, T = 14, B = 44, pw = W - L - R, ph = H - T - B - strip;
  const ox = d.o2_edges, py = d.p_edges, nx = ox.length - 1, ny = py.length - 1, cw = pw / nx, ch = ph / ny, pmax = py[ny];
  const mx = Math.max(1, ...d.counts.flat()), X = o => L + o / 100 * pw, Y = p => T + ph - p / pmax * ph;
  let s = `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="Heatmap of ${d.plotted} tests by initial oxygen and pressure. ${d.in_zone} tests fall inside the Moon-base reference zone.">`;
  s += `<rect x="${L}" y="${T}" width="${pw}" height="${ph}" fill="#060b14" stroke="#1b2a44"/>`;
  d.counts.forEach((row, i) => row.forEach((v, j) => { if (v) s += `<rect x="${(L + j * cw).toFixed(1)}" y="${(T + ph - (i + 1) * ch).toFixed(1)}" width="${cw.toFixed(1)}" height="${ch.toFixed(1)}" fill="rgba(90,176,255,${(.2 + .8 * Math.sqrt(v / mx)).toFixed(2)})"><title>${v} tests · O2 ${ox[j]}–${ox[j + 1]}% · ${py[i]}–${py[i + 1]} psi</title></rect>`; }));
  for (let o = 0; o <= 100; o += 20) s += `<text x="${X(o)}" y="${T + ph + 16}" fill="#93a3bd" font-size="11" text-anchor="middle">${o}%</text>`;
  for (let p = 0; p <= pmax; p += 12) s += `<text x="${L - 8}" y="${Y(p) + 4}" fill="#93a3bd" font-size="11" text-anchor="end">${p}</text>`;
  s += `<text x="${L + pw / 2}" y="${T + ph + 34}" fill="#cfe0ff" font-size="12" text-anchor="middle">Initial oxygen (% of atmosphere)</text><text transform="translate(14 ${T + ph / 2}) rotate(-90)" fill="#cfe0ff" font-size="12" text-anchor="middle">Pressure (psi)</text>`;
  const zx = X(d.zone.o2_pct), zy = Y(d.zone.pressure_psi);
  s += `<rect class="zone-box" x="${zx}" y="${zy}" width="${X(100) - zx}" height="${T + ph - zy}" fill="rgba(252,61,33,.1)" stroke="#fc3d21" stroke-width="2" stroke-dasharray="6 4"/><text x="${zx + 8}" y="${Math.max(zy + 16, T + 16)}" fill="#ff8d7b" font-size="12" font-weight="700">Moon-base zone: ≥${d.zone.o2_pct}% O₂, ≤${d.zone.pressure_psi} psi · ${d.in_zone} tests</text>`;
  if (marker && marker.oxygen_pct != null && marker.pressure_psi != null) {
    const mxp = X(Math.min(marker.oxygen_pct, 100)), myp = Y(Math.min(marker.pressure_psi, pmax));
    s += `<g><circle class="pulse" cx="${mxp}" cy="${myp}" r="8" fill="none" stroke="#fff" stroke-width="1.5"/><circle cx="${mxp}" cy="${myp}" r="8" fill="none" stroke="#fff" stroke-width="2.5"/><path d="M${mxp - 12} ${myp}h24M${mxp} ${myp - 12}v24" stroke="#fff" stroke-width="1.5"/><text x="${mxp + 12}" y="${myp - 10}" fill="#fff" font-size="12" font-weight="700">Your scenario</text></g>`;
  }
  if (strip) {
    const y0 = T + ph + B, smx = Math.max(1, ...d.o2_only);
    s += `<text x="${L}" y="${y0 - 2}" fill="#93a3bd" font-size="11">${d.o2_only_n} tests report oxygen but no pressure (solid fuels and others), so they cannot be placed above</text>`;
    d.o2_only.forEach((v, j) => { if (v) { const h = 6 + 28 * v / smx; s += `<rect x="${(L + j * cw).toFixed(1)}" y="${(y0 + 38 - h).toFixed(1)}" width="${(cw - 2).toFixed(1)}" height="${h.toFixed(1)}" fill="#8ea0c0"><title>${v} tests · O2 ${ox[j]}–${ox[j + 1]}% · no pressure</title></rect>`; } });
  }
  return s + "</svg>";
}
function scatterSVG(d) {
  const W = 760, H = 380, L = 62, R = 20, T = 16, B = 48, pw = W - L - R, ph = H - T - B, pts = d.points;
  const xs = pts.map(p => p.x), ys = pts.map(p => p.y), x0 = Math.floor(Math.min(...xs) - 1), x1 = Math.ceil(Math.max(...xs) + 1), y1 = Math.max(...ys) * 1.1 || 1;
  const X = v => L + (v - x0) / (x1 - x0) * pw, Y = v => T + ph - v / y1 * ph, d0 = pts.map(p => p.d0).filter(v => v != null), dmin = Math.min(...d0, 0), dmax = Math.max(...d0, 1);
  const col = e => ({ Extinction: "#5ab0ff", SE: "#35d07f", FT: "#f4b740" }[e] || "#a8b4cc");
  let s = `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(d.title)}, ${d.n} comparable tests"><rect x="${L}" y="${T}" width="${pw}" height="${ph}" fill="#060b14" stroke="#1b2a44"/>`;
  for (let i = 0; i <= 4; i++) { const v = y1 * i / 4; s += `<line x1="${L}" x2="${L + pw}" y1="${Y(v)}" y2="${Y(v)}" stroke="#16233a"/><text x="${L - 8}" y="${Y(v) + 4}" fill="#93a3bd" font-size="11" text-anchor="end">${v.toFixed(v < 10 ? 1 : 0)}</text>`; }
  const step = Math.max(1, Math.round((x1 - x0) / 8)); for (let v = x0; v <= x1; v += step) s += `<text x="${X(v)}" y="${T + ph + 16}" fill="#93a3bd" font-size="11" text-anchor="middle">${v}%</text>`;
  s += `<text x="${L + pw / 2}" y="${H - 8}" fill="#cfe0ff" font-size="12" text-anchor="middle">${esc(d.xlabel)}</text><text transform="translate(14 ${T + ph / 2}) rotate(-90)" fill="#cfe0ff" font-size="12" text-anchor="middle">${esc(d.ylabel)}</text>`;
  pts.forEach(p => { const r = p.d0 != null ? 3 + 6 * (p.d0 - dmin) / (dmax - dmin || 1) : 5; s += `<circle cx="${X(p.x).toFixed(1)}" cy="${Y(p.y).toFixed(1)}" r="${r.toFixed(1)}" fill="${col(p.end)}" fill-opacity=".7" stroke="#fff" stroke-opacity=".5"><title>${esc(p.id)} · O2 ${p.x.toFixed(1)}% · ${p.y} · ${esc(p.src)}</title></circle>`; });
  return s + "</svg>";
}

/* ---------- views ---------- */
const V = {};
V.home = async () => {
  const m = S.meta, f = m.by_investigation, gasOnly = f.CFIG.in_zone + f.FLAMEDESIGN.in_zone === m.tests_in_zone;
  $("#view").innerHTML = `<section class="hero"><div class="wrap"><div class="eyebrow">NASA Space Apps Challenge 2026 · Flame in Freefall</div>
  <h1>Fire in freefall. Know where the evidence ends.</h1>
  <p class="lead">FLARE-X turns NASA's microgravity combustion tests into explainable, mission-relevant fire-safety evidence, and shows exactly where the data runs out.</p>
  <div class="row"><a class="btn" href="#/simulator" id="go-moon">Run the Moon-base scenario</a><a class="btn ghost" href="#/charts">See the coverage map</a></div>
  <div class="stats"><div class="stat"><b data-n="${m.tests}">0</b><span>Tests parsed</span></div><div class="stat"><b data-n="${m.tables}">0</b><span>PSI tables</span></div><div class="stat"><b data-n="${m.investigations}">0</b><span>Investigations</span></div><div class="stat"><b data-n="${m.tests_in_zone}" class="hl">0</b><span>In the Moon-base zone (of ${m.tests_with_o2_and_pressure})</span></div></div></div></section>
  ${wrap(`<h2 class="t">What the data says about a Moon base</h2><div class="grid g3">
   <div class="card"><div class="big">${m.tests_in_zone}<span class="mut" style="font-size:16px"> / ${m.tests_with_o2_and_pressure}</span></div><p>tests with both oxygen and pressure fall inside the planned Moon-base atmosphere (≥30% O₂, ≤10.2 psi). ${gasOnly ? "All of them are gas flames (CFI-G " + f.CFIG.in_zone + ", Flame Design " + f.FLAMEDESIGN.in_zone + ")." : ""}</p></div>
   <div class="card"><div class="big">${f.FLEX.closest_psi_at_o2_ge_30} psi</div><p>is the closest FLEX gets: ${f.FLEX.o2_ge_30} droplet tests at 30% O₂ or more, none at or below 10.2 psi. FLEX is the main suppression dataset.</p></div>
   <div class="card"><div class="big">${m.solid.with_pressure}</div><p>of ${m.solid.tests} solid-fuel tests (BASS-II, Saffire) report a pressure, and oxygen tops out at ${m.solid.max_o2_pct}%. The materials that matter most have the least condition data.</p></div></div>
   <h2 class="t mt2">Explore</h2><div class="grid g4">
   ${[["simulator", "Mission simulator", "Pick a scenario, rank the evidence, export a PDF briefing."], ["charts", "Data & coverage", "Oxygen × pressure map and charts of comparable tests only."], ["copilot", "AI copilot", "Ask questions answered from the data, with checked citations."], ["earth", "Earth applications", "How space fire safety reached smoke detectors and firefighter gear."]].map(x => `<a class="card" href="#/${x[0]}"><h3>${x[1]}</h3><p>${x[2]}</p></a>`).join("")}</div>`)}`;
  $$(".stat b").forEach(b => { const n = +b.dataset.n; if (matchMedia("(prefers-reduced-motion:reduce)").matches) { b.textContent = n.toLocaleString(); return; } const t0 = performance.now(); (function tick(t) { const k = Math.min(1, (t - t0) / 800); b.textContent = Math.round(n * (1 - Math.pow(1 - k, 3))).toLocaleString(); if (k < 1) requestAnimationFrame(tick); })(t0); });
  $("#go-moon").onclick = () => applyPreset("moon");
};

const invCard = r => { const s = r.stats; return `<article class="card" id="inv-${r.id}"><div class="between"><div><span class="badge b-neutral">${esc(r.fuel_class || "fuel not reported")}</span> <span class="xs mut">${esc(r.psi)}</span></div>
 <label class="row xs" style="margin:0"><input type="checkbox" data-cmp="${r.id}" ${S.sel.includes(r.id) ? "checked" : ""}> Compare</label></div>
 <h3 class="mt" style="margin-top:10px">${esc(r.name)}</h3><div class="xs mut">${esc(r.family)}${r.hardware ? " · " + esc(r.hardware) : ""}</div>
 <div class="chips"><span class="chip">${s.tests ? s.tests + " tests listed" : r.table_rows + " table rows"}</span><span class="chip">O₂ ${pct(s.o2_range) || "not reported"}</span><span class="chip">${psi(s.p_psi_range) || "pressure not reported"}</span>${r.direct.map(o => `<span class="chip" style="border-color:var(--grn)">${esc(o)}</span>`).join("")}${r.indirect.map(o => `<span class="chip" style="border-color:var(--amb)">${esc(o)} (indirect)</span>`).join("")}</div>
 <p class="sm">${esc(r.note)}</p><p class="xs mut"><b>Limitation:</b> ${esc(r.limitation)}</p>
 <details><summary>Sources & provenance</summary><p class="xs">${sourceLinks(r)}</p><p class="xs mut">Table file${r.tables.length > 1 ? "s" : ""}: ${r.tables.map(esc).join("; ")} · SHA-256 ${r.sha256.map(esc).join(", ")}… · retrieved ${esc(r.retrieved)}</p></details></article>`; };
V.explorer = async () => {
  const fam = ["all", ...new Set(S.inv.map(r => r.family))];
  $("#view").innerHTML = head("Research explorer", "Investigations", "Every record shows what its public table actually contains. Ranges are computed from the files; anything missing says Not reported.") + wrap(`
  <div class="form"><label>Search<input type="search" id="q" value="${esc(S.q)}" placeholder="name, PSI id, material…"></label>
  <label>Family<select id="fam">${fam.map(f => `<option ${S.family === f ? "selected" : ""} value="${esc(f)}">${f === "all" ? "All families" : esc(f)}</option>`).join("")}</select></label>
  <label>Fuel class<select id="fuel">${["all", "solid", "liquid", "gas"].map(f => `<option ${S.fuel === f ? "selected" : ""} value="${f}">${f === "all" ? "Any" : f}</option>`).join("")}</select></label>
  <div><a class="btn sm" href="#/compare" id="cmpbtn">Compare selected (${S.sel.length})</a></div></div><div class="grid g2 mt" id="invgrid"></div>`);
  const draw = () => { const q = S.q.toLowerCase(), l = S.inv.filter(r => (S.family === "all" || r.family === S.family) && (S.fuel === "all" || r.fuel_class === S.fuel) && (!q || (r.name + r.psi + r.id + r.note + r.stats.fuels.join(" ")).toLowerCase().includes(q)));
    $("#invgrid").innerHTML = l.map(invCard).join("") || '<p class="mut">No investigations match.</p>';
    $$("[data-cmp]").forEach(c => c.onchange = () => { const id = c.dataset.cmp, i = S.sel.indexOf(id); if (i > -1) S.sel.splice(i, 1); else if (S.sel.length < 3) S.sel.push(id); else { c.checked = false; toast("Compare up to 3 investigations."); } $("#cmpbtn").textContent = `Compare selected (${S.sel.length})`; }); };
  $("#q").oninput = e => { S.q = e.target.value; draw(); }; $("#fam").onchange = e => { S.family = e.target.value; draw(); }; $("#fuel").onchange = e => { S.fuel = e.target.value; draw(); }; draw();
};

V.compare = async () => {
  const rs = S.sel.map(id => S.inv.find(r => r.id === id)).filter(Boolean);
  const F = [["Family", r => r.family], ["Fuel class", r => r.fuel_class], ["Hardware", r => r.hardware], ["Objective", r => [...r.direct, ...r.indirect.map(x => x + " (indirect)")].join(", ") || null],
    ["Tests listed", r => r.stats.tests || null], ["Oxygen range", r => pct(r.stats.o2_range)], ["Pressure range", r => psi(r.stats.p_psi_range)], ["Suppressant", r => r.suppressant],
    ["What the table lists", r => r.note], ["Limitation", r => r.limitation], ["Source table(s)", r => r.tables.join("; ")]];
  let body = `<div class="card"><p>Pick at least two investigations in <a href="#/explorer">Investigations</a>, or start with a classic contrast:</p><div class="row"><button class="btn sm" id="p1">FLEX vs BASS-II</button><button class="btn sm ghost" id="p2">CFI-G vs Flame Design</button><button class="btn sm ghost" id="p3">SAME vs FLEX</button></div></div>`;
  if (rs.length >= 2) {
    let filled = 0, rows = F.map(([lab, fn]) => { const v = rs.map(fn), known = v.filter(x => x != null && x !== ""); filled += known.length;
      const st = !known.length ? "missing" : known.length < v.length ? "partial" : new Set(known.map(String)).size === 1 ? "same" : "differs";
      return `<tr><th>${lab}</th>${v.map(x => `<td class="${st}">${nr(x)}</td>`).join("")}</tr>`; }).join("");
    body = `<div class="ov"><table><thead><tr><th></th>${rs.map(r => `<th>${esc(r.name)}<br><span class="xs">${esc(r.psi)}</span></th>`).join("")}</tr></thead><tbody>${rows}</tbody></table></div>
    <p class="sm mut mt">Metadata completeness: <b>${Math.round(100 * filled / (F.length * rs.length))}%</b>. Green = same, amber = differs, grey = not reported. Two “Not reported” cells are never treated as a match, and a shared parameter does not make two tests directly comparable.</p>`;
  }
  $("#view").innerHTML = head("Experiment intelligence", "Compare investigations", "Side-by-side conditions, with missing fields kept visible instead of silently filled.") + wrap(body);
  const pick = (a, b) => { S.sel = [a, b]; V.compare(); }; if ($("#p1")) { $("#p1").onclick = () => pick("FLEX", "BASSII"); $("#p2").onclick = () => pick("CFIG", "FLAMEDESIGN"); $("#p3").onclick = () => pick("SAME", "FLEX"); }
};

function applyPreset(id) { const p = S.presets.find(x => x.id === id); if (!p) return; S.sc = { environment: p.environment, concern: p.concern, gravity: p.gravity, fuel: p.fuel, oxygen_pct: p.oxygen_pct, pressure_psi: p.pressure_psi }; S.presetNote = p.note; S.presetId = id; }
const rankCard = (x, i) => { const m = x.matches; return `<article class="card"><div class="between"><div><span class="xs mut">#${i + 1} · ${esc(x.psi)} · ${esc(x.family)}</span><h3>${esc(x.name)}</h3></div><div class="row"><span class="badge b-${x.evidence}">${x.evidence}</span><span class="badge b-neutral">${esc(x.band)}</span></div></div>
 <div class="xs mut">Score on available dimensions ${Math.round(x.score * 100)}%</div><div class="bar"><i style="width:${Math.round(x.score * 100)}%"></i></div><div class="xs mut">Data coverage ${Math.round(x.coverage * 100)}% of weight</div><div class="bar cov"><i style="width:${Math.round(x.coverage * 100)}%"></i></div>
 <div class="chips">${m.both != null ? `<span class="chip">${m.both} tests near both O₂ & pressure</span>` : ""}${m.in_zone ? `<span class="chip" style="border-color:var(--red);color:#ffb3a6">${m.in_zone} inside Moon-base zone</span>` : ""}${x.missing.length ? `<span class="chip">missing: ${x.missing.join(", ")}</span>` : ""}</div>
 <details><summary>Why this score</summary><ul class="clean xs">${x.dims.map(d => `<li><b>${d.name}</b> (weight ${d.weight}): ${d.value == null ? `not scored: ${esc(d.note)}` : d.value.toFixed(1)}</li>`).join("")}</ul></details></article>`; };
V.simulator = async () => {
  if (!S.presets.length) S.presets = await api("/api/presets");
  if (!S.heat) S.heat = await api("/api/heatmap?inv=all");
  const c = S.sc, opt = (v, cur, l) => `<option value="${v}" ${cur === v ? "selected" : ""}>${l}</option>`;
  $("#view").innerHTML = head("Habitat relevance engine", "Mission simulator", "Choose a scenario. FLARE-X ranks the investigations whose documented conditions match, and lists what has no direct evidence. It ranks relevance, never safety.") + wrap(`
  <div class="row" role="group" aria-label="Scenario presets"><span class="xs mut">PRESETS</span>${S.presets.map(p => `<button class="chip ${S.presetId === p.id ? "on" : ""}" data-p="${p.id}">${esc(p.label)}</button>`).join("")}</div>
  <p class="xs mut" id="pnote">${esc(S.presetNote || "Presets fill the form; every field stays editable.")}</p>
  <div class="form card"><label>Environment<select id="f-env">${opt("spacecraft", c.environment, "Spacecraft / station")}${opt("lunar", c.environment, "Lunar habitat")}${opt("mars", c.environment, "Mars habitat")}${opt("rover", c.environment, "Pressurized rover")}</select></label>
  <label>Concern<select id="f-con">${opt("suppression", c.concern, "Suppression")}${opt("prevention", c.concern, "Material flammability")}${opt("detection", c.concern, "Smoke detection")}${opt("gas-phase", c.concern, "Gas-phase combustion")}</select></label>
  <label>Gravity<select id="f-g">${opt("micro", c.gravity, "Microgravity")}${opt("lunar", c.gravity, "Lunar")}${opt("mars", c.gravity, "Mars")}${opt("normal", c.gravity, "Normal (1 g)")}</select></label>
  <label>Fuel class<select id="f-fuel">${opt("any", c.fuel, "Not specified")}${opt("solid", c.fuel, "Solid")}${opt("liquid", c.fuel, "Liquid")}${opt("gas", c.fuel, "Gas")}</select></label>
  <label>Oxygen % (blank = unset)<input type="number" id="f-o2" min="0" max="100" step="0.5" value="${c.oxygen_pct ?? ""}"></label>
  <label>Pressure psi (blank = unset)<input type="number" id="f-p" min="0.1" max="100" step="0.1" value="${c.pressure_psi ?? ""}"></label></div>
  <details class="mt"><summary>Adjust scoring weights</summary><div class="form mt">${[["oxygen", .25], ["pressure", .2], ["fuel", .2], ["gravity", .15], ["objective", .1], ["measurement", .1]].map(([k, v]) => `<label>${k} <span id="wv-${k}">${(S.weights || {})[k] ?? v}</span><input type="range" min="0" max="1" step="0.05" value="${(S.weights || {})[k] ?? v}" data-w="${k}"></label>`).join("")}</div></details>
  <div id="simout" class="mt" aria-live="polite"></div>`);
  $$("[data-p]").forEach(b => b.onclick = () => { applyPreset(b.dataset.p); V.simulator(); });
  let t; const read = () => { const num = id => { const v = $(id).value.trim(); return v === "" ? null : +v; }; S.presetId = null;
    S.sc = { environment: $("#f-env").value, concern: $("#f-con").value, gravity: $("#f-g").value, fuel: $("#f-fuel").value, oxygen_pct: num("#f-o2"), pressure_psi: num("#f-p") }; clearTimeout(t); t = setTimeout(run, 300); };
  $$(".form select, .form input[type=number]").forEach(el => el.oninput = read);
  $$("[data-w]").forEach(el => el.oninput = () => { S.weights = S.weights || { oxygen: .25, pressure: .2, fuel: .2, gravity: .15, objective: .1, measurement: .1 }; S.weights[el.dataset.w] = +el.value; $("#wv-" + el.dataset.w).textContent = el.value; clearTimeout(t); t = setTimeout(run, 300); });
  run();
};
async function run() {
  const out = $("#simout"); if (!out) return;
  let r; try { r = await api("/api/rank", { ...S.sc, weights: S.weights }); } catch (e) { return; }
  S.rank = r; const shown = r.results.slice(0, 8);
  out.innerHTML = (r.mismatch ? `<div class="warnbar" role="alert">${esc(r.mismatch)}</div>` : "") + `<div class="split"><div><h2 class="t">Ranked evidence</h2><p class="xs mut">Order: evidence type (Direct, Indirect, Gap), then score on the dimensions that could be scored. ${r.results.length - shown.length} lower-relevance records hidden.</p><div class="grid" style="gap:12px">${shown.map(rankCard).join("")}</div></div>
  <div class="sticky"><h2 class="t">Where the tests sit</h2><div class="card">${heatSVG(S.heat, S.sc, true)}<p class="xs mut">Each cell counts tests by initial oxygen and pressure. The white cross is your scenario; the red box is the planned Moon-base atmosphere.</p></div>
  <h2 class="t mt2">Research gaps</h2><div class="card"><ul class="clean sm">${r.gaps.map(g => `<li>${esc(g)}</li>`).join("") || "<li>None detected for this scenario.</li>"}</ul></div>
  <div class="mt"><button class="btn" id="pdf">Download PDF evidence briefing</button> <span class="xs mut" id="pdfmsg"></span></div></div></div>`;
  $("#pdf").onclick = async () => { const b = $("#pdf"); b.disabled = true; $("#pdfmsg").textContent = "Building…";
    try { const res = await fetch("/api/briefing.pdf", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ...S.sc, weights: S.weights }) }); if (!res.ok) throw new Error("PDF failed"); const url = URL.createObjectURL(await res.blob()); const a = document.createElement("a"); a.href = url; a.download = "flarex_briefing.pdf"; document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 2000); $("#pdfmsg").textContent = "Downloaded."; }
    catch (e) { toast("Could not build the PDF briefing."); $("#pdfmsg").textContent = ""; } b.disabled = false; };
}

V.charts = async () => {
  const [groups] = await Promise.all([api(`/api/charts/groups?dataset=${S.ds}`)]); const heat = await api(`/api/heatmap?inv=${S.chartInv}`);
  $("#view").innerHTML = head("Data & coverage", "What the tests actually cover", "Computed live from the 22 NASA PSI tables. The map shows where evidence exists; the scatter charts only compare tests that share fuel, atmosphere family and pressure.") + wrap(`
  <h2 class="t">Oxygen × pressure coverage map</h2><div class="row"><span class="xs mut">SHOW</span>${["all", ...heat.investigations].map(i => `<button class="chip ${S.chartInv === i ? "on" : ""}" data-ci="${i}">${i === "all" ? "All investigations" : i}</button>`).join("")}</div>
  <div class="card mt">${heatSVG(heat, null, false)}<p class="sm">${heat.plotted} tests are plotted; ${heat.in_zone} fall inside the Moon-base zone. Solid-fuel tables are missing from the grid because they report no pressure.</p></div>
  <h2 class="t mt2">Comparable tests only</h2><div class="row"><span class="xs mut">DATASET</span><button class="chip ${S.ds === "flex" ? "on" : ""}" data-ds="flex">FLEX (droplets)</button><button class="chip ${S.ds === "cfig" ? "on" : ""}" data-ds="cfig">CFI-G (gas flames)</button></div>
  <p class="xs mut mt">Pick a group. Tests are grouped by fuel and atmosphere family and pressure (±0.05 atm) so only like is compared with like. Groups under ${groups.min_points} tests are not charted.</p>
  <div class="chips" id="grp">${groups.groups.map(g => `<button class="chip ${S.group === g.key ? "on" : ""}" data-g="${esc(g.key)}" ${g.chartable ? "" : "disabled style='opacity:.45;cursor:not-allowed'"} title="${g.chartable ? "" : "Too few comparable tests"}">${esc(g.label)} · n=${g.n}</button>`).join("")}</div>
  <div class="card" id="scat"><p class="mut">Select a group above.</p></div>
  <h2 class="t mt2">Data-quality flags found while parsing</h2><div class="card"><ul class="clean sm">${Object.entries(groups.flags).map(([k, v]) => `<li><b>${esc(k)}</b>: ${Object.entries(v).map(([a, b]) => `${esc(a.replace(/_/g, " "))} (${b})`).join(", ")}</li>`).join("")}</ul><p class="xs mut">Flagged rows are kept and labelled, not silently fixed. Units: mmHg and bar converted to atm, then psi.</p></div>`);
  $$("[data-ci]").forEach(b => b.onclick = () => { S.chartInv = b.dataset.ci; V.charts(); });
  $$("[data-ds]").forEach(b => b.onclick = () => { S.ds = b.dataset.ds; S.group = null; V.charts(); });
  const show = async key => { S.group = key; $$("[data-g]").forEach(b => b.classList.toggle("on", b.dataset.g === key));
    try { const d = await api(`/api/charts/series?dataset=${S.ds}&key=${encodeURIComponent(key)}`); $("#scat").innerHTML = `<h3>${esc(d.title)}</h3><p class="xs mut">${esc(d.group)} · ${d.n} tests</p>${scatterSVG(d)}<p class="xs mut">${esc(d.note)}</p>`; } catch (e) {} };
  $$("[data-g]").forEach(b => { if (!b.disabled) b.onclick = () => show(b.dataset.g); }); const first = S.group || (groups.groups.find(g => g.chartable) || {}).key; if (first) show(first);
};

const SUGG = ["How many tests fall in the Moon-base zone?", "Which investigations studied suppression?", "What oxygen levels did FLEX test?", "Is there data on solid fuels at low pressure?", "Which studies measured smoke or dust?"];
const cites = t => esc(t).replace(/\[([A-Za-z0-9_\-]+)\]/g, '<span class="cite">$1</span>');
V.copilot = async () => {
  S.ai = await api("/api/ai/status"); if (!S.model) S.model = S.ai.default || "";
  $("#view").innerHTML = head("Evidence-grounded assistant", "AI copilot", "Answers come from retrieved evidence and computed facts only. Every citation is checked; unverifiable ones are removed. It runs on your local Ollama model, and works without one.") + wrap(`
  <div class="row between"><span class="pill"><span class="dot ${S.ai.available ? "on" : ""}"></span>${S.ai.available ? "Ollama connected" : S.ai.hosted ? "Hosted demo: retrieval-only answers (live AI runs locally with Ollama)" : "Ollama not running: retrieval-only mode"}</span>
  ${S.ai.available && S.ai.models.length ? `<label class="row" style="margin:0">Model <select id="mdl" style="width:auto;margin:0">${S.ai.models.map(m => `<option ${m === S.model ? "selected" : ""}>${esc(m)}</option>`).join("")}</select></label>` : ""}</div>
  ${S.ai.available || S.ai.hosted ? "" : `<p class="xs mut">To enable AI answers: install Ollama, run <code>ollama pull llama3.1:8b</code>, keep <code>ollama serve</code> running, then reload.</p>`}
  <div class="row mt">${SUGG.map(q => `<button class="chip" data-q="${esc(q)}">${esc(q)}</button>`).join("")}</div>
  <div class="card mt"><div class="chat" id="chat" aria-live="polite">${S.chat.length ? "" : '<p class="mut">Ask a question about the loaded NASA tables. The current simulator scenario is passed along as context.</p>'}</div>
  <div class="row mt"><input type="text" id="ask" placeholder="Ask about the data…" style="flex:1;margin:0" aria-label="Question"><button class="btn" id="send">Ask</button></div></div>`);
  const draw = () => { $("#chat").innerHTML = S.chat.map(m => m.role === "u" ? `<div class="msg u">${esc(m.text)}</div>` : `<div class="msg a">${cites(m.text)}${(m.warnings || []).map(w => `<div class="xs" style="color:var(--amb);margin-top:8px">⚠ ${esc(w)}</div>`).join("")}
    ${m.sources && m.sources.length ? `<details><summary>${m.sources.length} evidence items · ${m.mode === "llm" ? "answered by " + esc(m.model) : m.mode === "refusal" ? "no evidence found" : "retrieval only"}</summary><ul class="clean xs">${m.sources.map(s => `<li><span class="cite">${esc(s.id)}</span> ${esc(s.text)} <span class="mut">(${esc(s.source)})</span></li>`).join("")}</ul></details>` : ""}</div>`).join(""); $("#chat").scrollTop = 1e9; }; draw();
  const send = async q => { q = (q || $("#ask").value).trim(); if (!q) return; $("#ask").value = ""; S.chat.push({ role: "u", text: q }); S.chat.push({ role: "a", text: "Thinking…", pending: true }); draw();
    try { const r = await api("/api/copilot", { question: q, scenario: S.sc, model: S.model || null }); S.chat.pop(); S.chat.push({ role: "a", text: r.text, sources: r.sources, warnings: r.warnings, mode: r.mode, model: r.model }); }
    catch (e) { S.chat.pop(); S.chat.push({ role: "a", text: "The question could not be answered. Please try again.", warnings: [] }); } draw(); };
  $("#send").onclick = () => send(); $("#ask").onkeydown = e => { if (e.key === "Enter") send(); }; $$("[data-q]").forEach(b => b.onclick = () => send(b.dataset.q)); if ($("#mdl")) $("#mdl").onchange = e => S.model = e.target.value;
};

V.earth = async () => {
  $("#view").innerHTML = head("Beyond the Moon", "Earth applications", "Space fire safety has repeatedly come home. These stories come from NASA's spinoff pages; the links to our data are thematic connections, not claims of direct derivation.") + wrap(`<div class="grid g2">${S.story.earth.map(e => `<article class="card"><div class="between"><span class="badge b-neutral">${esc(e.era)}</span></div><h3 class="mt" style="margin-top:10px">${esc(e.title)}</h3><p>${esc(e.summary)}</p>
   <p class="sm"><b class="hl">In FLARE-X:</b> ${esc(e.connection)}</p><div class="chips">${e.links_to.map(id => `<button class="chip" data-inv="${id}">Open ${esc((S.inv.find(r => r.id === id) || {}).name || id)}</button>`).join("")}</div><a class="btn sm ghost" href="${esc(e.url)}" target="_blank" rel="noopener">Read the NASA story ↗</a></article>`).join("")}</div>`);
  $$("[data-inv]").forEach(b => b.onclick = () => { S.q = b.dataset.inv; S.family = "all"; S.fuel = "all"; location.hash = "#/explorer"; });
};
V.timeline = async () => {
  $("#view").innerHTML = head("The reason this exists", "Why fire safety in space matters", "Three real incidents and one near-future problem. The context comes from NASA's incident pages; the data connections are ours.") + wrap(`<div class="tl">${S.story.timeline.map(e => `<div class="ev"><div class="yr">${esc(e.year)}</div><h3>${esc(e.title)}</h3><p>${esc(e.text)}</p><p class="sm"><b class="hl">Why it matters here:</b> ${esc(e.why)}</p><div class="row"><a class="btn sm ghost" href="${esc(e.url)}" target="_blank" rel="noopener">NASA source ↗</a><a class="btn sm" href="#/${e.view}">Explore in FLARE-X →</a></div></div>`).join("")}</div>`);
};

/* ---------- router ---------- */
async function route() {
  const name = (location.hash.replace(/^#\//, "") || "home").split("?")[0], fn = V[name] || V.home;
  $("#nav").innerHTML = NAV.map(([k, l]) => `<a href="#/${k}" class="${k === name ? "on" : ""}" ${k === name ? 'aria-current="page"' : ""}>${l}</a>`).join("");
  try { await fn(); } catch (e) { $("#view").innerHTML = wrap(`<div class="warnbar">Something went wrong loading this page. ${esc(e.message || "")}</div>`); }
  window.scrollTo(0, 0);
}
(async function init() {
  try { [S.meta, S.inv, S.story, S.presets] = await Promise.all([api("/api/meta"), api("/api/investigations"), api("/api/story"), api("/api/presets")]); }
  catch (e) { $("#view").innerHTML = wrap('<div class="warnbar">Could not reach the FLARE-X backend. Start it with <code>python run.py</code> and reload.</div>'); return; }
  $("#foot-res").innerHTML = "NASA resources: " + S.meta.resources.map(r => `<a href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.label)}</a>`).join(" · ");
  window.addEventListener("hashchange", route); route();
})();
