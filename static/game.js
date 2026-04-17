const SIZE = 4;
const TOKEN_KEY = "csod_access_token";
const BEST_LOCAL_KEY = "csod2048_best_local";

const boardEl = document.getElementById("board");
const scoreEl = document.getElementById("scoreVal");
const bestEl = document.getElementById("bestVal");
const userLine = document.getElementById("userLine");
const authMsg = document.getElementById("authMsg");
const pauseLayer = document.getElementById("pauseLayer");
const overlay = document.getElementById("overlay");
const overlayTitle = document.getElementById("overlayTitle");
const btnNew = document.getElementById("btnNew");
const leaderList = document.getElementById("leaderList");
const sessionGate = document.getElementById("sessionGate");
const sessionGateMsg = document.getElementById("sessionGateMsg");
const appShell = document.getElementById("appShell");

let grid = [];
let score = 0;
let bestLocal = Number(localStorage.getItem(BEST_LOCAL_KEY) || "0");
let paused = false;
let gameOver = false;
/** Highest score this round (since New game); sent to server only on game over or page unload. */
let sessionMaxScore = 0;
let cells = [];

function setSessionGateMessage(text) {
  if (sessionGateMsg) sessionGateMsg.textContent = text;
}

function showAppShell() {
  if (sessionGate) sessionGate.hidden = true;
  if (appShell) appShell.hidden = false;
}

function getToken() {
  return sessionStorage.getItem(TOKEN_KEY);
}

function setToken(t) {
  sessionStorage.setItem(TOKEN_KEY, t);
}

async function api(path, opts = {}) {
  const headers = { ...(opts.headers || {}) };
  const tok = getToken();
  if (tok) headers.Authorization = `Bearer ${tok}`;
  const r = await fetch(path, { ...opts, headers });
  if (!r.ok) {
    const err = await r.text();
    throw new Error(`${r.status} ${r.statusText}: ${err || ""}`);
  }
  const ct = r.headers.get("content-type");
  if (ct && ct.includes("application/json")) return r.json();
  return null;
}

async function exchangeFromQuery() {
  const params = new URLSearchParams(window.location.search);
  // CSOD docs use ?code=; some Cornerstone custom pages use ?authCode= instead.
  const code = params.get("code") || params.get("authCode");
  const state = params.get("state");
  if (!code || !state) return false;

  authMsg.textContent = "Signing you in…";
  const data = await api("/api/auth/token", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code, state }),
  });
  setToken(data.access_token);
  const clean = new URL(window.location.href);
  clean.searchParams.delete("code");
  clean.searchParams.delete("authCode");
  clean.searchParams.delete("state");
  clean.searchParams.delete("sessionId");
  window.history.replaceState({}, "", clean.toString());
  return true;
}

async function loadUser() {
  const tok = getToken();
  if (!tok) {
    userLine.hidden = true;
    authMsg.textContent =
      "Open this page from your Cornerstone custom page (authorization required).";
    return null;
  }
  try {
    const me = await api("/api/me");
    userLine.textContent = `Signed in as ${me.user_name} (user id: ${me.user_id})`;
    userLine.hidden = false;
    authMsg.textContent = "";
    return me;
  } catch (e) {
    const msg = String(e.message || e);
    const unauthorized = /\b401\b/.test(msg) || /\b403\b/.test(msg);
    if (unauthorized) {
      sessionStorage.removeItem(TOKEN_KEY);
    }
    userLine.hidden = true;
    authMsg.textContent = unauthorized
      ? "Session expired or invalid. Re-open the page from Cornerstone."
      : `Profile could not be loaded (${msg.slice(0, 200)}). Check Console / Network → /api/me.`;
    console.error("/api/me failed:", e);
    return null;
  }
}

async function loadLeaderboard() {
  try {
    const data = await api("/api/leaderboard");
    leaderList.innerHTML = "";
    const entries = data.entries || [];
    if (!entries.length) {
      const li = document.createElement("li");
      li.textContent = "No scores yet.";
      leaderList.appendChild(li);
      return;
    }
    entries.forEach((row, i) => {
      const li = document.createElement("li");
      li.innerHTML = `${i + 1}. ${escapeHtml(row.user_name)} — <span class="leader-score">${row.best_score}</span>`;
      leaderList.appendChild(li);
    });
  } catch (e) {
    console.error("Leaderboard request failed:", e);
    leaderList.innerHTML = "<li>Could not load leaderboard.</li>";
  }
}

function escapeHtml(s) {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

async function flushScoreToServer() {
  const tok = getToken();
  if (!tok || sessionMaxScore <= 0) return;
  try {
    await api("/api/scores", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ score: sessionMaxScore }),
    });
    await loadLeaderboard();
  } catch (e) {
    console.warn("Score save failed:", e);
  }
}

/** Used on refresh/close; best-effort while the page unloads. */
function flushScoreOnPageHide() {
  const tok = getToken();
  if (!tok || sessionMaxScore <= 0) return;
  const url = new URL("/api/scores", window.location.origin).href;
  fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${tok}`,
    },
    body: JSON.stringify({ score: sessionMaxScore }),
    keepalive: true,
  }).catch(() => {});
}

window.addEventListener("pagehide", flushScoreOnPageHide);

function emptyGrid() {
  return Array.from({ length: SIZE * SIZE }, () => 0);
}

function idx(r, c) {
  return r * SIZE + c;
}

function moveLine(line) {
  const tiles = line.filter((x) => x !== 0);
  const out = [];
  let pts = 0;
  for (let i = 0; i < tiles.length; i++) {
    if (i < tiles.length - 1 && tiles[i] === tiles[i + 1]) {
      const v = tiles[i] * 2;
      pts += v;
      out.push(v);
      i++;
    } else {
      out.push(tiles[i]);
    }
  }
  while (out.length < SIZE) out.push(0);
  return { line: out, pts };
}

function gridsEqual(a, b) {
  for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) return false;
  return true;
}

function applyMoveLeft(g) {
  const next = g.slice();
  let pts = 0;
  for (let r = 0; r < SIZE; r++) {
    const row = [g[idx(r, 0)], g[idx(r, 1)], g[idx(r, 2)], g[idx(r, 3)]];
    const { line, pts: p } = moveLine(row);
    pts += p;
    for (let c = 0; c < SIZE; c++) next[idx(r, c)] = line[c];
  }
  return { next, pts, changed: !gridsEqual(g, next) };
}

function applyMoveRight(g) {
  const next = g.slice();
  let pts = 0;
  for (let r = 0; r < SIZE; r++) {
    const row = [g[idx(r, 3)], g[idx(r, 2)], g[idx(r, 1)], g[idx(r, 0)]];
    const { line, pts: p } = moveLine(row);
    pts += p;
    for (let c = 0; c < SIZE; c++) next[idx(r, SIZE - 1 - c)] = line[c];
  }
  return { next, pts, changed: !gridsEqual(g, next) };
}

function applyMoveUp(g) {
  const next = g.slice();
  let pts = 0;
  for (let c = 0; c < SIZE; c++) {
    const col = [g[idx(0, c)], g[idx(1, c)], g[idx(2, c)], g[idx(3, c)]];
    const { line, pts: p } = moveLine(col);
    pts += p;
    for (let r = 0; r < SIZE; r++) next[idx(r, c)] = line[r];
  }
  return { next, pts, changed: !gridsEqual(g, next) };
}

function applyMoveDown(g) {
  const next = g.slice();
  let pts = 0;
  for (let c = 0; c < SIZE; c++) {
    const col = [g[idx(3, c)], g[idx(2, c)], g[idx(1, c)], g[idx(0, c)]];
    const { line, pts: p } = moveLine(col);
    pts += p;
    for (let r = 0; r < SIZE; r++) next[idx(SIZE - 1 - r, c)] = line[r];
  }
  return { next, pts, changed: !gridsEqual(g, next) };
}

function move(dir) {
  if (paused || gameOver) return;

  const ops = {
    left: applyMoveLeft,
    right: applyMoveRight,
    up: applyMoveUp,
    down: applyMoveDown,
  };
  const { next, pts, changed } = ops[dir](grid);
  if (!changed) return;

  grid = next;
  score += pts;
  sessionMaxScore = Math.max(sessionMaxScore, score);
  if (score > bestLocal) {
    bestLocal = score;
    localStorage.setItem(BEST_LOCAL_KEY, String(bestLocal));
  }
  updateHud();

  addRandomTile();
  if (!canMove()) {
    gameOver = true;
    overlayTitle.textContent = `Game over — ${score} points`;
    overlay.hidden = false;
    sessionMaxScore = Math.max(sessionMaxScore, score);
    flushScoreToServer();
    return;
  }
  render();
}

function canMove() {
  if (grid.some((v) => v === 0)) return true;
  for (let r = 0; r < SIZE; r++) {
    for (let c = 0; c < SIZE; c++) {
      const v = grid[idx(r, c)];
      if (c < SIZE - 1 && v === grid[idx(r, c + 1)]) return true;
      if (r < SIZE - 1 && v === grid[idx(r + 1, c)]) return true;
    }
  }
  return false;
}

function addRandomTile() {
  const empty = [];
  for (let i = 0; i < grid.length; i++) if (grid[i] === 0) empty.push(i);
  if (!empty.length) return;
  const spot = empty[Math.floor(Math.random() * empty.length)];
  grid[spot] = Math.random() < 0.9 ? 2 : 4;
}

function newGame() {
  grid = emptyGrid();
  score = 0;
  sessionMaxScore = 0;
  gameOver = false;
  overlay.hidden = true;
  addRandomTile();
  addRandomTile();
  updateHud();
  render();
  boardEl.focus();
}

function updateHud() {
  scoreEl.textContent = String(score);
  bestEl.textContent = String(Math.max(bestLocal, score));
}

function render() {
  for (let i = 0; i < cells.length; i++) {
    const v = grid[i];
    cells[i].dataset.v = String(v);
    cells[i].textContent = v === 0 ? "" : String(v);
  }
}

function buildBoardDom() {
  boardEl.innerHTML = "";
  cells = [];
  for (let i = 0; i < SIZE * SIZE; i++) {
    const cell = document.createElement("div");
    cell.className = "cell";
    cell.dataset.v = "0";
    boardEl.appendChild(cell);
    cells.push(cell);
  }
}

function updatePauseUi() {
  const hide = !paused;
  pauseLayer.hidden = hide;
}

function setPaused(p) {
  paused = p;
  updatePauseUi();
}

function onVisibilityOrFocus() {
  const docHidden = document.visibilityState === "hidden";
  const lostFocus = typeof document.hasFocus === "function" && !document.hasFocus();
  setPaused(docHidden || lostFocus);
}

window.addEventListener("blur", onVisibilityOrFocus);
window.addEventListener("focus", onVisibilityOrFocus);
document.addEventListener("visibilitychange", onVisibilityOrFocus);

boardEl.addEventListener("click", () => boardEl.focus());

boardEl.addEventListener("keydown", (e) => {
  const key = e.key;
  if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"].includes(key)) {
    e.preventDefault();
    if (key === "ArrowLeft") move("left");
    if (key === "ArrowRight") move("right");
    if (key === "ArrowUp") move("up");
    if (key === "ArrowDown") move("down");
  }
});

let touchStart = null;

function pointerStart(ev) {
  const p = ev.touches ? ev.touches[0] : ev;
  touchStart = { x: p.clientX, y: p.clientY };
}

function pointerEnd(ev) {
  if (!touchStart) return;
  const p = ev.changedTouches ? ev.changedTouches[0] : ev;
  const dx = p.clientX - touchStart.x;
  const dy = p.clientY - touchStart.y;
  touchStart = null;
  const min = 24;
  if (Math.abs(dx) < min && Math.abs(dy) < min) return;
  if (Math.abs(dx) > Math.abs(dy)) {
    move(dx > 0 ? "right" : "left");
  } else {
    move(dy > 0 ? "down" : "up");
  }
}

boardEl.addEventListener("touchstart", pointerStart, { passive: true });
boardEl.addEventListener("touchend", pointerEnd);
boardEl.addEventListener("mousedown", pointerStart);
boardEl.addEventListener("mouseup", pointerEnd);

btnNew.addEventListener("click", () => {
  newGame();
});

async function boot() {
  setSessionGateMessage("Signing in…");
  try {
    await exchangeFromQuery();
  } catch (e) {
    authMsg.textContent = "Could not complete sign-in. Re-open from Cornerstone.";
    console.error(e);
  }

  setSessionGateMessage("Loading profile…");
  if (getToken()) {
    try {
      const rawUserinfo = await api("/api/me/raw");
      console.log(
        "[CSOD userinfo] GET /services/api/oauth2/userinfo — full JSON:",
        rawUserinfo
      );
    } catch (e) {
      console.warn("[CSOD userinfo raw] failed:", e);
    }
  }
  await loadUser();

  setSessionGateMessage("Preparing leaderboard…");
  if (getToken()) {
    try {
      await api("/api/leaderboard/sync-name", { method: "POST" });
    } catch (e) {
      console.warn("Leaderboard display name sync:", e);
    }
  }
  await loadLeaderboard();

  showAppShell();
  buildBoardDom();
  newGame();
  boardEl.focus();
  onVisibilityOrFocus();
}

boot();
