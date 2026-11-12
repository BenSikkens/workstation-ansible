"use strict";
const $ = (id) => document.getElementById(id);
let status = null;
let config = { links: [], info: "", log_lines: 300 };
let jobOffset = 0, jobTimer = null, jobWatching = 0;

function el(tag, props, ...kids) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (k === "class") node.className = v;
    else if (k === "text") node.textContent = v;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v);
  }
  for (const kid of kids) if (kid) node.append(kid);
  return node;
}

async function api(path, opts) {
  const res = await fetch(path, opts);
  if (res.status === 401) {
    document.body.textContent = "Not signed in. Run `homelab gui` in a terminal, or use the Homelab launcher.";
    throw new Error("401");
  }
  return res;
}

async function post(verb, scope) {
  const res = await api("/api/action", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Homelab-GUI": "1" },
    body: JSON.stringify({ verb, scope }),
  });
  const body = await res.json();
  if (!res.ok) { alert(body.error || "Failed"); return; }
  watchJob(verb, scope);
}

const VERBS = { up: "Starting", down: "Stopping" };

function confirmStop(scope, title) {
  return confirm(scope === "all" ? "Stop everything that is installed?" : `Stop ${title}?`);
}

function renderGroups() {
  const box = $("groups");
  box.replaceChildren();
  const busy = status.busy;
  for (const g of status.groups) {
    const units = el("ul", { class: "units" });
    for (const u of g.units) {
      units.append(el("li", {},
        el("span", { class: "dot " + u.state.replace(/\s/g, "-") }),
        el("span", { class: "unit-name", text: u.owner === "system" ? u.name : `${u.name} · ${u.owner}` }),
        el("span", { class: "unit-state", text: u.state })));
    }
    const links = el("div", { class: "links" });
    for (const l of config.links.filter((x) => x.group === g.id)) {
      links.append(el("a", { class: "link", href: l.url, target: "_blank", rel: "noopener", text: l.name + " ↗" }));
    }
    const start = el("button", { class: "btn primary", text: "Start", onclick: () => post("up", g.id) });
    const stop = el("button", { class: "btn danger", text: "Stop", onclick: () => confirmStop(g.id, g.title) && post("down", g.id) });
    start.disabled = stop.disabled = busy;
    box.append(el("article", { class: "card" },
      el("div", { class: "card-head" }, el("h2", { text: g.title }), el("span", { class: "pill " + g.state, text: g.state })),
      units, links, el("div", { class: "actions" }, start, stop)));
  }
  if (status.missing.length) {
    box.append(el("p", { class: "missing", text: "Not installed: " + status.missing.join(", ") }));
  }
  $("start-all").disabled = $("stop-all").disabled = busy || !status.groups.length;
}

function renderNotes() {
  $("notes").replaceChildren(...status.notes.map((n) => el("div", { class: "note", text: n })));
}

function renderUnitPicker() {
  const sel = $("log-unit");
  const previous = sel.value;
  const options = [];
  for (const g of status.groups) {
    for (const u of g.units) {
      if (u.state === "not installed") continue;
      options.push({ value: JSON.stringify([u.owner, u.name]), label: `${g.title} · ${u.name}${u.owner === "system" ? "" : " (" + u.owner + ")"}` });
    }
  }
  const same = [...sel.options].map((o) => o.value).join("|") === options.map((o) => o.value).join("|");
  if (same) return;
  sel.replaceChildren(...options.map((o) => el("option", { value: o.value, text: o.label })));
  if (options.some((o) => o.value === previous)) sel.value = previous;
  if (sel.value) refreshLogs();
}

async function refreshStatus() {
  try {
    const res = await api("/api/status");
    status = await res.json();
  } catch (e) { return; }
  renderNotes(); renderGroups(); renderUnitPicker();
  $("updated").textContent = "Updated " + new Date(status.at * 1000).toLocaleTimeString();
}

async function refreshLogs() {
  const raw = $("log-unit").value;
  if (!raw) return;
  const [owner, unit] = JSON.parse(raw);
  const q = new URLSearchParams({ owner, unit, lines: String(config.log_lines) });
  const out = $("log-output");
  const res = await api("/api/logs?" + q);
  const atBottom = out.scrollHeight - out.scrollTop - out.clientHeight < 40;
  out.textContent = (await res.text()) || "(no log lines)";
  if (atBottom) out.scrollTop = out.scrollHeight;
}

function watchJob(verb, scope) {
  jobOffset = 0;
  const token = ++jobWatching;
  $("job").hidden = false;
  $("job-title").textContent = `${VERBS[verb]} ${scope === "all" ? "everything" : scope}`;
  $("job-output").textContent = "";
  $("job-state").className = "pill degraded";
  $("job-state").textContent = "running";
  clearTimeout(jobTimer);
  if (status) { status.busy = true; renderGroups(); }
  const tick = async () => {
    if (token !== jobWatching) return;
    const res = await api("/api/job?offset=" + jobOffset);
    const j = await res.json();
    const out = $("job-output");
    if (j.output) { out.textContent += j.output; out.scrollTop = out.scrollHeight; }
    jobOffset = j.offset;
    if (j.running) { jobTimer = setTimeout(tick, 700); return; }
    $("job-state").className = "pill " + (j.rc === 0 ? "running" : "failed");
    $("job-state").textContent = j.rc === 0 ? "done" : "exit " + j.rc;
    refreshStatus();
  };
  tick();
}

function renderInfo() {
  $("info").hidden = !config.info;
  $("info-output").textContent = config.info;
}

async function init() {
  $("start-all").addEventListener("click", () => post("up", "all"));
  $("stop-all").addEventListener("click", () => confirmStop("all", "") && post("down", "all"));
  $("job-close").addEventListener("click", () => { $("job").hidden = true; });
  $("log-unit").addEventListener("change", refreshLogs);
  $("log-refresh").addEventListener("click", refreshLogs);
  const res = await api("/api/config");
  config = await res.json();
  renderInfo();
  await refreshStatus();
  // Pick up a job that is already running (page reload, or started in another tab).
  const j = await (await api("/api/job?offset=0")).json();
  if (j.running) watchJob(j.verb, j.scope);
  setInterval(() => { if (!document.hidden) refreshStatus(); }, 5000);
  setInterval(() => { if (!document.hidden && $("log-follow").checked) refreshLogs(); }, 3000);
}

init();
