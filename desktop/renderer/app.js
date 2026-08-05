const connPill = document.getElementById("connPill");
const wanPill = document.getElementById("wanPill");
const statusLine = document.getElementById("statusLine");
const ringWrap = document.getElementById("ringWrap");
const stateBadge = document.getElementById("stateBadge");
const transcript = document.getElementById("transcript");
const btnMin = document.getElementById("btnMin");
const btnClose = document.getElementById("btnClose");
const timerChip = document.getElementById("timerChip");
const timerLabel = document.getElementById("timerLabel");
const timerCount = document.getElementById("timerCount");
const canvas = document.getElementById("waveCanvas");
const ctx = canvas.getContext("2d");

const MAX_LINES = 40;
let socket = null;
let retryMs = 800;
let uiState = "idle";
let raf = 0;
let t0 = performance.now();
let activeTimer = null;
let timerTick = null;

const STATE_LABELS = {
  idle: "STANDBY",
  listening: "LISTEN",
  thinking: "THINK",
  speaking: "SPEAK",
  error: "FAULT",
};

const ORB_LABELS = [
  "SYSTEM",
  "COMMS",
  "AUDIO",
  "MEMORY",
  "NET",
  "TOOLS",
  "POWER",
  "CORE",
];

function formatCountdown(msLeft) {
  const total = Math.max(0, Math.ceil(msLeft / 1000));
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function clearTimerUi() {
  activeTimer = null;
  if (timerTick) {
    clearInterval(timerTick);
    timerTick = null;
  }
  timerChip.classList.add("hidden");
  timerCount.textContent = "--:--";
}

function startTimerUi(evt) {
  activeTimer = {
    id: evt.timer_id,
    endsAt: Number(evt.ends_at) * 1000,
    label: (evt.label || "TIMER").toUpperCase(),
  };
  timerLabel.textContent = activeTimer.label.slice(0, 14) || "TIMER";
  timerChip.classList.remove("hidden");

  const tick = () => {
    if (!activeTimer) return;
    const left = activeTimer.endsAt - Date.now();
    timerCount.textContent = formatCountdown(left);
    if (left <= 0) timerCount.textContent = "00:00";
  };
  tick();
  if (timerTick) clearInterval(timerTick);
  timerTick = setInterval(tick, 250);
}

function setConn(state, label) {
  connPill.className = `conn ${state}`;
  connPill.textContent = label;
}

function setWan(online) {
  if (!wanPill) return;
  wanPill.textContent = online ? "WAN Online" : "WAN Lower modules";
  wanPill.dataset.state = online ? "online" : "offline";
}

function setUiState(state) {
  uiState = state || "idle";
  ringWrap.dataset.state = uiState;
  stateBadge.textContent = STATE_LABELS[uiState] || uiState.toUpperCase();
}

function setStatus(text, state) {
  statusLine.style.animation = "none";
  void statusLine.offsetWidth;
  statusLine.style.animation = "";
  statusLine.textContent = text || "—";
  if (state) setUiState(state);
}

function addLine(role, text) {
  const row = document.createElement("div");
  row.className = `line ${role}`;
  row.innerHTML = `<span class="role">${role}</span><span class="text"></span>`;
  row.querySelector(".text").textContent = text;
  transcript.appendChild(row);
  while (transcript.children.length > MAX_LINES) {
    transcript.removeChild(transcript.firstChild);
  }
  transcript.scrollTop = transcript.scrollHeight;
}

function energyProfile(state) {
  switch (state) {
    case "speaking":
      return { speed: 2.8, amp: 1, glow: 1.2, spin: 1.6 };
    case "listening":
      return { speed: 1.6, amp: 0.65, glow: 1.0, spin: 1.1 };
    case "thinking":
      return { speed: 2.2, amp: 0.5, glow: 1.1, spin: 1.8 };
    case "error":
      return { speed: 0.9, amp: 0.35, glow: 0.75, spin: 0.5 };
    default:
      return { speed: 0.85, amp: 0.35, glow: 0.9, spin: 0.55 };
  }
}

function rgba(rgb, alpha) {
  return `rgba(${rgb[0]}, ${rgb[1]}, ${rgb[2]}, ${alpha})`;
}

function drawSegmentedRing(cx, cy, r0, r1, segments, gap, rotation, rgb, alpha, activeIndex) {
  const step = (Math.PI * 2) / segments;
  const halfGap = gap / 2;
  for (let i = 0; i < segments; i++) {
    const a0 = rotation + i * step + halfGap;
    const a1 = rotation + (i + 1) * step - halfGap;
    const lit = activeIndex < 0 || i === activeIndex || (activeIndex >= 0 && Math.abs(i - activeIndex) % segments <= 1);
    ctx.beginPath();
    ctx.arc(cx, cy, r1, a0, a1);
    ctx.arc(cx, cy, r0, a1, a0, true);
    ctx.closePath();
    const boost = lit ? 1 : 0.35;
    const grad = ctx.createRadialGradient(cx, cy, r0, cx, cy, r1);
    grad.addColorStop(0, rgba(rgb, alpha * 0.15 * boost));
    grad.addColorStop(0.5, rgba(rgb, alpha * 0.55 * boost));
    grad.addColorStop(1, rgba(rgb, alpha * 0.25 * boost));
    ctx.fillStyle = grad;
    ctx.fill();
    ctx.strokeStyle = rgba(rgb, alpha * (lit ? 0.85 : 0.3));
    ctx.lineWidth = 1;
    ctx.stroke();
  }
}

function drawCoreOrb(now) {
  // Complex segmented orb inspired by JARVIS OS radial cores (original design).
  const w = canvas.width;
  const h = canvas.height;
  const cx = w / 2;
  const cy = h * 0.46;
  const { speed, amp, glow, spin } = energyProfile(uiState);
  const t = (now - t0) / 1000;
  const isError = uiState === "error";
  const rgb = isError ? [255, 120, 120] : [70, 190, 255];
  const rgbHot = isError ? [255, 190, 190] : [170, 235, 255];
  const rgbMetal = isError ? [90, 50, 55] : [40, 70, 95];
  const a = (x) => x * glow;

  ctx.clearRect(0, 0, w, h);

  // Ambient plate
  const plate = ctx.createRadialGradient(cx, cy, 20, cx, cy, 180);
  plate.addColorStop(0, rgba(rgb, a(0.18)));
  plate.addColorStop(0.55, rgba(rgb, a(0.06)));
  plate.addColorStop(1, "rgba(0,0,0,0)");
  ctx.fillStyle = plate;
  ctx.beginPath();
  ctx.arc(cx, cy, 180, 0, Math.PI * 2);
  ctx.fill();

  // Outer decorative ticks
  ctx.save();
  ctx.translate(cx, cy);
  ctx.rotate(t * 0.15 * spin);
  for (let i = 0; i < 96; i++) {
    const ang = (i / 96) * Math.PI * 2;
    const long = i % 8 === 0;
    const r0 = long ? 158 : 164;
    const r1 = long ? 176 : 170;
    ctx.beginPath();
    ctx.moveTo(Math.cos(ang) * r0, Math.sin(ang) * r0);
    ctx.lineTo(Math.cos(ang) * r1, Math.sin(ang) * r1);
    ctx.strokeStyle = rgba(rgbHot, a(long ? 0.55 : 0.18));
    ctx.lineWidth = long ? 2 : 1;
    ctx.stroke();
  }
  ctx.restore();

  // Thin guide rings
  for (const r of [172, 150, 128, 106, 84, 62, 42]) {
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.strokeStyle = rgba(rgb, a(0.12 + (r % 40) * 0.001));
    ctx.lineWidth = 1;
    ctx.stroke();
  }

  const rotA = t * 0.35 * spin;
  const rotB = -t * 0.55 * spin;
  const rotC = t * 0.8 * spin;
  const pulse = 0.55 + Math.sin(t * speed * 2) * 0.2 * amp;
  const active = Math.floor((t * speed * 2) % 24);

  // Outer heavy segmented ring
  drawSegmentedRing(cx, cy, 132, 148, 24, 0.04, rotA, rgb, a(0.7 * pulse), active % 24);

  // Mid chevron-style ring (fewer larger plates)
  drawSegmentedRing(cx, cy, 108, 126, 12, 0.08, rotB, rgbHot, a(0.55), Math.floor(active / 2) % 12);

  // Inner dense segments
  drawSegmentedRing(cx, cy, 86, 102, 36, 0.03, rotC, rgb, a(0.45), active % 36);

  // Nested hex-ish cutouts via arcs
  ctx.save();
  ctx.translate(cx, cy);
  ctx.rotate(rotA * 0.5);
  for (let i = 0; i < 6; i++) {
    const ang = (i / 6) * Math.PI * 2;
    ctx.beginPath();
    ctx.arc(Math.cos(ang) * 70, Math.sin(ang) * 70, 18, 0, Math.PI * 2);
    ctx.strokeStyle = rgba(rgbHot, a(0.25));
    ctx.lineWidth = 1.2;
    ctx.stroke();
  }
  ctx.restore();

  // Energy spokes
  ctx.save();
  ctx.translate(cx, cy);
  ctx.rotate(-rotB);
  for (let i = 0; i < 8; i++) {
    const ang = (i / 8) * Math.PI * 2;
    const len = 48 + Math.sin(t * speed * 3 + i) * 10 * amp;
    ctx.beginPath();
    ctx.moveTo(Math.cos(ang) * 28, Math.sin(ang) * 28);
    ctx.lineTo(Math.cos(ang) * len, Math.sin(ang) * len);
    ctx.strokeStyle = rgba(rgbHot, a(0.2 + (i % 2) * 0.15));
    ctx.lineWidth = 1.5;
    ctx.stroke();
  }
  ctx.restore();

  // Side labels around orb
  ctx.save();
  ctx.translate(cx, cy);
  ctx.font = "600 9px Orbitron, sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  for (let i = 0; i < ORB_LABELS.length; i++) {
    const ang = -Math.PI / 2 + (i / ORB_LABELS.length) * Math.PI * 2 + rotA * 0.15;
    const lr = 188;
    const lx = Math.cos(ang) * lr;
    const ly = Math.sin(ang) * lr;
    const highlight = Math.floor((t * speed + i) % ORB_LABELS.length) === i;
    ctx.fillStyle = rgba(rgbHot, a(highlight ? 0.85 : 0.35));
    ctx.fillText(ORB_LABELS[i], lx, ly);
    // connector dash
    ctx.beginPath();
    ctx.moveTo(Math.cos(ang) * 176, Math.sin(ang) * 176);
    ctx.lineTo(Math.cos(ang) * 168, Math.sin(ang) * 168);
    ctx.strokeStyle = rgba(rgb, a(0.3));
    ctx.stroke();
  }
  ctx.restore();

  // Metallic hub
  const hub = ctx.createRadialGradient(cx - 8, cy - 10, 2, cx, cy, 40);
  hub.addColorStop(0, rgba(rgbHot, a(0.55)));
  hub.addColorStop(0.4, rgba(rgb, a(0.35)));
  hub.addColorStop(0.75, rgba(rgbMetal, a(0.65)));
  hub.addColorStop(1, rgba(rgbMetal, a(0.9)));
  ctx.beginPath();
  ctx.arc(cx, cy, 36, 0, Math.PI * 2);
  ctx.fillStyle = hub;
  ctx.fill();
  ctx.strokeStyle = rgba(rgbHot, a(0.8));
  ctx.lineWidth = 2;
  ctx.stroke();

  // Inner core pulse
  const coreR = 16 + Math.sin(t * speed * 4) * 3 * amp;
  const core = ctx.createRadialGradient(cx, cy, 1, cx, cy, coreR + 8);
  core.addColorStop(0, rgba(rgbHot, a(0.95)));
  core.addColorStop(0.5, rgba(rgb, a(0.45)));
  core.addColorStop(1, "rgba(0,0,0,0)");
  ctx.beginPath();
  ctx.arc(cx, cy, coreR + 8, 0, Math.PI * 2);
  ctx.fillStyle = core;
  ctx.fill();
  ctx.beginPath();
  ctx.arc(cx, cy, coreR * 0.45, 0, Math.PI * 2);
  ctx.fillStyle = rgba(rgbHot, a(0.9));
  ctx.fill();

  // Sweep scanner wedge
  const sweep = t * 1.4 * spin;
  ctx.save();
  ctx.translate(cx, cy);
  ctx.rotate(sweep);
  ctx.beginPath();
  ctx.moveTo(0, 0);
  ctx.arc(0, 0, 148, -0.15, 0.55);
  ctx.closePath();
  const wedge = ctx.createRadialGradient(0, 0, 10, 0, 0, 148);
  wedge.addColorStop(0, rgba(rgbHot, a(0.25)));
  wedge.addColorStop(1, "rgba(0,0,0,0)");
  ctx.fillStyle = wedge;
  ctx.globalAlpha = 0.65;
  ctx.fill();
  ctx.globalAlpha = 1;
  ctx.beginPath();
  ctx.moveTo(0, 0);
  ctx.lineTo(Math.cos(0.2) * 148, Math.sin(0.2) * 148);
  ctx.strokeStyle = rgba(rgbHot, a(0.55));
  ctx.lineWidth = 2;
  ctx.stroke();
  ctx.restore();

  // State-specific overlays
  if (uiState === "listening") {
    for (let i = 0; i < 3; i++) {
      const rr = 50 + i * 22 + Math.sin(t * 3 + i) * 6 * amp;
      ctx.beginPath();
      ctx.arc(cx, cy, rr, 0, Math.PI * 2);
      ctx.strokeStyle = rgba(rgbHot, a(0.12));
      ctx.lineWidth = 2;
      ctx.stroke();
    }
  }

  if (uiState === "thinking") {
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(t * 2);
    for (let i = 0; i < 5; i++) {
      const ang = (i / 5) * Math.PI * 2;
      ctx.beginPath();
      ctx.arc(Math.cos(ang) * 118, Math.sin(ang) * 118, 4, 0, Math.PI * 2);
      ctx.fillStyle = rgba(rgbHot, a(0.8));
      ctx.fill();
    }
    ctx.restore();
  }

  if (uiState === "speaking") {
    for (let i = 0; i < 16; i++) {
      const ang = (i / 16) * Math.PI * 2 + t;
      const mag = 150 + Math.abs(Math.sin(t * 10 + i)) * 18 * amp;
      ctx.beginPath();
      ctx.moveTo(cx + Math.cos(ang) * 150, cy + Math.sin(ang) * 150);
      ctx.lineTo(cx + Math.cos(ang) * mag, cy + Math.sin(ang) * mag);
      ctx.strokeStyle = rgba(rgbHot, a(0.35));
      ctx.lineWidth = 2;
      ctx.stroke();
    }
  }

  // Center monogram
  ctx.font = "700 11px Orbitron, sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillStyle = rgba(rgbHot, a(0.9));
  ctx.fillText("J", cx, cy - 1);

  // Bottom caption ring text
  ctx.font = "600 8px Orbitron, sans-serif";
  ctx.fillStyle = rgba(rgb, a(0.45));
  ctx.fillText(STATE_LABELS[uiState] || "CORE", cx, cy + 198);

  raf = requestAnimationFrame(drawCoreOrb);
}

let lastSfxState = "";

function playSfx(name) {
  try {
    if (window.jarvisSfx && typeof window.jarvisSfx[name] === "function") {
      window.jarvisSfx[name]();
    }
  } catch (_) {
    /* ignore audio failures */
  }
}

function playStateSfx(state) {
  if (!state || state === lastSfxState) return;
  lastSfxState = state;
  if (state === "listening") playSfx("listen");
  else if (state === "thinking") playSfx("think");
  else if (state === "speaking") playSfx("speak");
  else if (state === "error") playSfx("error");
}

function handleEvent(evt) {
  switch (evt.type) {
    case "ready":
      setStatus('Online — say "hey jarvis" to begin.', "idle");
      lastSfxState = "idle";
      playSfx("boot");
      break;
    case "status":
      setStatus(evt.detail || evt.state || "", evt.state || "idle");
      playStateSfx(evt.state || "idle");
      break;
    case "transcript":
      addLine(evt.role || "system", evt.text || "");
      break;
    case "wake":
      setStatus(`Wake word detected (score=${Number(evt.score || 0).toFixed(2)})`, "listening");
      lastSfxState = "listening";
      playSfx("wake");
      break;
    case "timer":
      if (evt.action === "start") {
        startTimerUi(evt);
        addLine("system", evt.announcement || `Timer ${evt.seconds || "?"}s`);
        playSfx("timerStart");
      } else if (evt.action === "done") {
        clearTimerUi();
        playSfx("timerDone");
      }
      break;
    case "error":
      setStatus(evt.message || "Error", "error");
      addLine("system", evt.message || "Error");
      lastSfxState = "error";
      playSfx("error");
      break;
    case "network":
      setWan(!!evt.online);
      break;
    default:
      break;
  }
}

async function connect() {
  const url = await window.jarvis.getWsUrl();
  setConn("", "Connecting");
  try {
    socket = new WebSocket(url);
  } catch (err) {
    setConn("offline", "Offline");
    setStatus("Waiting for Python bridge…", "idle");
    scheduleRetry();
    return;
  }

  socket.addEventListener("open", () => {
    retryMs = 800;
    setConn("online", "Connected");
    setStatus('Linked — say "hey jarvis" when ready.', "idle");
    playSfx("connected");
  });

  socket.addEventListener("message", (msg) => {
    try {
      handleEvent(JSON.parse(msg.data));
    } catch (_) {
      /* ignore */
    }
  });

  socket.addEventListener("close", () => {
    setConn("offline", "Offline");
    setStatus("Bridge disconnected — retrying…", "error");
    playSfx("offline");
    scheduleRetry();
  });

  socket.addEventListener("error", () => {
    try {
      socket.close();
    } catch (_) {
      /* ignore */
    }
  });
}

function scheduleRetry() {
  setTimeout(connect, retryMs);
  retryMs = Math.min(retryMs * 1.5, 5000);
}

btnMin.addEventListener("click", () => {
  playSfx("click");
  window.jarvis.minimize();
});
btnClose.addEventListener("click", () => {
  playSfx("click");
  window.jarvis.close();
});

window.jarvis.onPythonExit((code) => {
  setConn("offline", "Offline");
  setStatus(`Python exited (${code}).`, "error");
  playSfx("error");
});

raf = requestAnimationFrame(drawCoreOrb);
connect();
