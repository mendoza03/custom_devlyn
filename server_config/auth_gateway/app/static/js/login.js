let currentStream = null;
let flowId = null;
let livenessSessionId = null;
let livenessRunning = false;
let faceDetector = null;
let baselineMetrics = null;
let motionCanvas = null;
let motionContext = null;
let previousMotionFrame = null;
let runMode = "idle"; // idle | start | retry | running
let currentAction = window.__LOGIN_MODE__ === "check_out" ? "check_out" : "check_in";

let mediaRecorder = null;
let mediaRecorderChunks = [];
let mediaRecorderMimeType = "video/webm";
let cachedTelemetry = null;
let cachedProbeImage = null;
let cachedVideoBase64 = null;

const NEXT_URL = window.__NEXT_URL__ || "/odoo";
const NEXT_LOGOUT_URL = window.__NEXT_LOGOUT_URL__ || "";
const TRUSTED_LOGOUT_LOGIN = String(window.__TRUSTED_LOGOUT_LOGIN__ || "").trim();
const TRUSTED_LOGOUT_TS = String(window.__TRUSTED_LOGOUT_TS__ || "").trim();
const TRUSTED_LOGOUT_SIG = String(window.__TRUSTED_LOGOUT_SIG__ || "").trim();
const AUTH_CHANNEL = window.__AUTH_CHANNEL__ || "standard";

const CHALLENGE_TIMEOUT_MS = 9000;
const CHALLENGE_POLL_MS = 250;
const LIVENESS_DEBUG = (() => {
  try {
    return window.localStorage?.getItem("liveness_debug") === "1";
  } catch {
    return false;
  }
})();

function debugLog(...args) {
  if (!LIVENESS_DEBUG) return;
  // eslint-disable-next-line no-console
  console.debug("[liveness]", ...args);
}

function makeLocalId(prefix) {
  if (window.crypto?.randomUUID) {
    return `${prefix}-${window.crypto.randomUUID()}`;
  }
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function isCheckOutAction(action) {
  return action === "check_out";
}

function flowTitle(action) {
  return isCheckOutAction(action) ? "Marcar salida biométrica" : "Acceso biométrico";
}

function flowSubtitle(action) {
  return isCheckOutAction(action)
    ? "Completa la verificación para registrar tu salida"
    : "Completa la verificación para continuar";
}

function hasTrustedCheckOutContext() {
  return isCheckOutAction(currentAction)
    && Boolean(TRUSTED_LOGOUT_LOGIN && TRUSTED_LOGOUT_TS && TRUSTED_LOGOUT_SIG && NEXT_LOGOUT_URL);
}

function trustedLogoutPayload() {
  if (!hasTrustedCheckOutContext()) {
    return {};
  }
  return {
    trusted_logout_login: TRUSTED_LOGOUT_LOGIN,
    trusted_logout_ts: Number(TRUSTED_LOGOUT_TS),
    trusted_logout_sig: TRUSTED_LOGOUT_SIG,
  };
}

function setLivenessHeader(action) {
  const titleEl = document.querySelector("#step-liveness .auth-header h1");
  const subtitleEl = document.querySelector("#step-liveness .auth-header p");
  if (titleEl) titleEl.textContent = flowTitle(action);
  if (subtitleEl) subtitleEl.textContent = flowSubtitle(action);
}

function setStep(id) {
  document.querySelectorAll(".step").forEach((el) => el.classList.remove("active"));
  document.getElementById(id).classList.add("active");
}

function setStatus(msg) {
  document.getElementById("status").textContent = msg;
}

function setCredentialButtonMode(mode) {
  const loginBtn = document.getElementById("btn-start");
  const checkoutBtn = document.getElementById("btn-checkout");
  if (!loginBtn && !checkoutBtn) {
    return;
  }

  if (mode === "loading") {
    if (loginBtn) loginBtn.disabled = true;
    if (checkoutBtn) checkoutBtn.disabled = true;
    if (isCheckOutAction(currentAction)) {
      if (checkoutBtn) checkoutBtn.textContent = "Validando...";
      if (loginBtn) loginBtn.textContent = "Iniciar sesión";
    } else {
      if (loginBtn) loginBtn.textContent = "Validando...";
      if (checkoutBtn) checkoutBtn.textContent = "Marcar salida";
    }
    return;
  }

  if (loginBtn) {
    loginBtn.disabled = false;
    loginBtn.textContent = "Iniciar sesión";
  }
  if (checkoutBtn) {
    checkoutBtn.disabled = false;
    checkoutBtn.textContent = "Marcar salida";
  }
}

function setLivePrompt(msg) {
  const badge = document.getElementById("livePromptBadge");
  if (badge) {
    badge.textContent = msg;
  }
}

function promptForChallenge(text) {
  const normalized = String(text || "").toLowerCase();
  if (normalized.includes("calibr")) {
    return "Mira al frente para calibrar";
  }
  if (normalized.includes("quiet")) {
    return "Permanece quieto";
  }
  if (normalized.includes("circular") || normalized.includes("círculo") || normalized.includes("circulo")) {
    return "Gira la cabeza en círculo";
  }
  if (normalized.includes("presiona")) {
    return 'Presiona "Comenzar prueba"';
  }
  if (normalized.includes("reintent")) {
    return 'Presiona "Reintentar"';
  }
  if (normalized.includes("proces")) {
    return "Procesando...";
  }
  if (normalized.includes("complet")) {
    return "Prueba completada";
  }
  return text;
}

function setChallenge(text) {
  const challengeText = document.getElementById("challengeText");
  if (challengeText) {
    challengeText.textContent = text;
  }
  setLivePrompt(promptForChallenge(text));
}

function setProgress(ratio) {
  const safe = Math.max(0, Math.min(1, ratio));
  const progress = document.getElementById("challengeProgress");
  if (progress) {
    progress.style.width = `${Math.round(safe * 100)}%`;
  }
}

function clearChallengeLog() {
  const log = document.getElementById("challengeLog");
  if (log) {
    log.innerHTML = "";
  }
}

function clearCredentialLog() {
  const log = document.getElementById("credLog");
  if (log) {
    log.innerHTML = "";
  }
}

function showCredentialError(text) {
  clearCredentialLog();
  const log = document.getElementById("credLog");
  if (!log) {
    return;
  }
  const item = document.createElement("li");
  item.textContent = text;
  item.classList.add("fail");
  log.appendChild(item);
}

function appendChallengeLog(text, kind = "") {
  const log = document.getElementById("challengeLog");
  if (!log) {
    return;
  }
  const item = document.createElement("li");
  item.textContent = text;
  if (kind) {
    item.classList.add(kind);
  }
  log.appendChild(item);
}

function setPrimaryButtonMode(mode) {
  const btn = document.getElementById("btn-liveness-start");
  if (!btn) {
    return;
  }
  runMode = mode;
  if (mode === "retry") {
    btn.textContent = "Reintentar";
    return;
  }
  if (mode === "running") {
    btn.textContent = "Procesando...";
    return;
  }
  btn.textContent = "Comenzar prueba";
}

function stopCamera() {
  if (!currentStream) {
    return;
  }
  currentStream.getTracks().forEach((track) => track.stop());
  currentStream = null;
  document.getElementById("camera").srcObject = null;
}

function isLocalhostHost() {
  const host = window.location.hostname;
  return host === "localhost" || host === "127.0.0.1" || host === "::1";
}

function buildCameraErrorMessage(error) {
  if (!window.isSecureContext && !isLocalhostHost()) {
    return "En móviles la cámara requiere HTTPS. Abre esta URL con HTTPS para permitir acceso.";
  }
  if (error?.name === "NotAllowedError") {
    return "Permiso de cámara denegado. Habilítalo en el navegador y reintenta.";
  }
  if (error?.name === "NotFoundError") {
    return "No se detectó cámara disponible en este dispositivo.";
  }
  if (error?.name === "NotReadableError") {
    return "La cámara está ocupada por otra app. Cierra otras apps de cámara e intenta de nuevo.";
  }
  return `No se pudo activar la cámara: ${error?.message || "error desconocido"}`;
}

async function getUserMediaWithFallback(deviceId = null) {
  const candidates = [];
  const hd = { width: { ideal: 1280 }, height: { ideal: 720 } };
  if (deviceId) {
    candidates.push({ video: { deviceId: { exact: deviceId }, ...hd }, audio: false });
    candidates.push({ video: { deviceId: { exact: deviceId } }, audio: false });
  }
  candidates.push({ video: { facingMode: { ideal: "user" }, ...hd }, audio: false });
  candidates.push({ video: { facingMode: { ideal: "user" } }, audio: false });
  candidates.push({ video: { facingMode: "user", ...hd }, audio: false });
  candidates.push({ video: { facingMode: "user" }, audio: false });
  candidates.push({ video: true, audio: false });

  let lastError = null;
  for (const constraints of candidates) {
    try {
      return await navigator.mediaDevices.getUserMedia(constraints);
    } catch (error) {
      lastError = error;
    }
  }
  throw lastError || new Error("No se pudo inicializar la cámara");
}

async function listCameras() {
  if (!navigator.mediaDevices?.enumerateDevices) {
    throw new Error("El navegador no soporta enumeración de cámaras");
  }
  const devices = await navigator.mediaDevices.enumerateDevices();
  const cameras = devices.filter((device) => device.kind === "videoinput");
  const select = document.getElementById("cameraSelect");
  select.innerHTML = "";
  cameras.forEach((camera, idx) => {
    const option = document.createElement("option");
    option.value = camera.deviceId;
    option.textContent = camera.label || `Cámara ${idx + 1}`;
    select.appendChild(option);
  });
  return cameras;
}

async function startCamera(deviceId = null) {
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new Error("Este navegador/bloqueo de seguridad no permite acceso a cámara.");
  }

  stopCamera();
  currentStream = await getUserMediaWithFallback(deviceId);
  const video = document.getElementById("camera");
  video.srcObject = currentStream;
  video.setAttribute("playsinline", "true");
  video.muted = true;
  try {
    await video.play();
  } catch {
    // Some mobile browsers may delay autoplay; metadata callback below covers this path.
  }
  await new Promise((resolve) => {
    if (video.readyState >= 2) {
      resolve();
      return;
    }
    const timer = window.setTimeout(resolve, 1200);
    video.onloadedmetadata = () => {
      window.clearTimeout(timer);
      resolve();
    };
  });
  resetMotionBuffer();
}

async function prepareCamera() {
  const cameras = await listCameras();
  const selected = document.getElementById("cameraSelect").value || null;
  await startCamera(selected);
  return cameras.length;
}

function resetMotionBuffer() {
  previousMotionFrame = null;
  motionCanvas = document.createElement("canvas");
  motionCanvas.width = 96;
  motionCanvas.height = 72;
  motionContext = motionCanvas.getContext("2d", { willReadFrequently: true });
}

function readMotionScores(includeTop = false) {
  const video = document.getElementById("camera");
  if (!motionContext || !video.videoWidth || !video.videoHeight) {
    return { mean: 0, top: 0 };
  }

  motionContext.drawImage(video, 0, 0, motionCanvas.width, motionCanvas.height);
  const { data } = motionContext.getImageData(0, 0, motionCanvas.width, motionCanvas.height);
  if (!previousMotionFrame) {
    previousMotionFrame = new Uint8ClampedArray(data);
    return { mean: 0, top: 0 };
  }

  let totalDiff = 0;
  let channelSamples = 0;
  const diffs = includeTop ? [] : null;
  for (let i = 0; i < data.length; i += 16) {
    const dr = Math.abs(data[i] - previousMotionFrame[i]);
    const dg = Math.abs(data[i + 1] - previousMotionFrame[i + 1]);
    const db = Math.abs(data[i + 2] - previousMotionFrame[i + 2]);
    totalDiff += dr + dg + db;
    channelSamples += 3;
    if (diffs) {
      diffs.push((dr + dg + db) / 3);
    }
  }

  previousMotionFrame = new Uint8ClampedArray(data);
  const mean = channelSamples ? totalDiff / channelSamples : 0;
  if (!diffs || diffs.length === 0) {
    return { mean, top: mean };
  }

  diffs.sort((a, b) => b - a);
  const k = Math.max(12, Math.floor(diffs.length * 0.1));
  let topSum = 0;
  for (let j = 0; j < k; j += 1) {
    topSum += diffs[j];
  }
  const top = k ? topSum / k : mean;
  return { mean, top };
}

function readMotionScore() {
  return readMotionScores(false).mean;
}

async function ensureFaceDetector() {
  if (faceDetector !== null) {
    return faceDetector;
  }
  if (!("FaceDetector" in window)) {
    faceDetector = false;
    return false;
  }
  try {
    faceDetector = new window.FaceDetector({ fastMode: true, maxDetectedFaces: 1 });
    return faceDetector;
  } catch {
    faceDetector = false;
    return false;
  }
}

async function readFaceMetrics() {
  if (!faceDetector) {
    return null;
  }
  const video = document.getElementById("camera");
  if (!video.videoWidth || !video.videoHeight) {
    return null;
  }

  try {
    const faces = await faceDetector.detect(video);
    if (!faces?.length) {
      return null;
    }
    const box = faces[0].boundingBox;
    return {
      centerX: (box.x + box.width / 2) / video.videoWidth,
      centerY: (box.y + box.height / 2) / video.videoHeight,
      area: (box.width * box.height) / (video.videoWidth * video.videoHeight),
      width: box.width / video.videoWidth,
      height: box.height / video.videoHeight,
    };
  } catch {
    return null;
  }
}

function delay(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

async function calibrateBaseline(timeoutMs = 8000) {
  const start = Date.now();
  while (Date.now() - start <= timeoutMs) {
    const metrics = await readFaceMetrics();
    if (metrics) {
      return metrics;
    }
    await delay(CHALLENGE_POLL_MS);
  }
  return null;
}

function buildChallenges() {
  if (faceDetector && baselineMetrics) {
    const orbitState = {
      samples: [],
      quadrants: new Set(),
      startPoint: null,
    };

    return [
      {
        text: "Mantén la cabeza quieta y centrada.",
        requiredHits: 5,
        evaluate: async () => {
          const metrics = await readFaceMetrics();
          if (!metrics) {
            return { ok: false, detail: "No se detecta rostro en cámara." };
          }

          const offsetX = metrics.centerX - baselineMetrics.centerX;
          const offsetY = metrics.centerY - baselineMetrics.centerY;
          const offset = Math.hypot(offsetX, offsetY);
          const areaDelta = baselineMetrics.area
            ? Math.abs(metrics.area - baselineMetrics.area) / baselineMetrics.area
            : 0;
          const motion = readMotionScore();
          const stable = offset <= 0.06 && areaDelta <= 0.2 && motion < 8;
          return stable
            ? { ok: true }
            : { ok: false, detail: "Quédate quieto y centrado unos segundos." };
        },
      },
      {
        text: "Mueve la cabeza en forma circular sin salir del cuadro.",
        requiredHits: 1,
        timeoutMs: 14000,
        evaluate: async () => {
          const metrics = await readFaceMetrics();
          if (!metrics) {
            return { ok: false, detail: "No se detecta rostro en cámara." };
          }

          const dx = metrics.centerX - baselineMetrics.centerX;
          const dy = metrics.centerY - baselineMetrics.centerY;
          const radius = Math.hypot(dx, dy);
          const faceScale = Math.max(
            0,
            Math.min(
              1,
              Math.min(
                Number(baselineMetrics.width || 0) || 0,
                Number(baselineMetrics.height || 0) || 0
              )
            )
          );
          const minRadius = Math.max(0.01, Math.min(0.025, faceScale * 0.08 || 0.01));

          if (radius < minRadius) {
            return { ok: false, detail: "Amplía un poco el círculo con la cabeza." };
          }
          if (radius > 0.24) {
            return { ok: false, detail: "Haz el círculo más corto para no salir del encuadre." };
          }

          if (!orbitState.startPoint) {
            orbitState.startPoint = { dx, dy };
          }
          orbitState.samples.push({ dx, dy, radius });

          if (dx >= 0 && dy < 0) orbitState.quadrants.add("q1");
          if (dx < 0 && dy < 0) orbitState.quadrants.add("q2");
          if (dx < 0 && dy >= 0) orbitState.quadrants.add("q3");
          if (dx >= 0 && dy >= 0) orbitState.quadrants.add("q4");

          const enoughCoverage = orbitState.quadrants.size >= 3;
          const enoughSamples = orbitState.samples.length >= 10;
          if (enoughCoverage && enoughSamples) {
            return { ok: true };
          }

          return {
            ok: false,
            detail: `Sigue el movimiento circular (${orbitState.quadrants.size}/3 zonas cubiertas).`,
          };
        },
      },
    ];
  }

  const fallbackState = { strongMotionHits: 0, baselineMean: [], baselineTop: [] };

  function percentile(values, p) {
    if (!values?.length) return 0;
    const sorted = [...values].sort((a, b) => a - b);
    const idx = Math.min(sorted.length - 1, Math.max(0, Math.floor(p * (sorted.length - 1))));
    return sorted[idx];
  }

  function computeAdaptiveThresholds() {
    if (fallbackState.baselineMean.length < 3 || fallbackState.baselineTop.length < 3) {
      return { mean: 8, top: 8 };
    }
    const meanP90 = percentile(fallbackState.baselineMean, 0.9);
    const topP90 = percentile(fallbackState.baselineTop, 0.9);

    return {
      mean: Math.max(1.6, Math.min(8.0, meanP90 + 1.2)),
      top: Math.max(6.0, Math.min(60.0, topP90 + 4.0)),
    };
  }

  return [
    {
      text: "Mantén la cabeza quieta por unos segundos.",
      requiredHits: 6,
      evaluate: async () => {
        const motion = readMotionScores(true);
        if (motion.mean < 6) {
          fallbackState.baselineMean.push(motion.mean);
          fallbackState.baselineTop.push(motion.top);
          if (fallbackState.baselineMean.length > 32) fallbackState.baselineMean.shift();
          if (fallbackState.baselineTop.length > 32) fallbackState.baselineTop.shift();
          debugLog("fallback baseline sample", motion);
          return { ok: true };
        }
        return { ok: false, detail: "Quédate quieto y centrado." };
      },
    },
    {
      text: "Mueve la cabeza en círculo frente a la cámara.",
      requiredHits: 1,
      timeoutMs: 14000,
      evaluate: async () => {
        const motion = readMotionScores(true);
        const thresholds = computeAdaptiveThresholds();
        const hit = motion.mean > thresholds.mean || motion.top > thresholds.top;
        if (hit) {
          fallbackState.strongMotionHits += 1;
        }
        const requiredHits = 10;
        debugLog("fallback motion", { motion, thresholds, hits: fallbackState.strongMotionHits });
        if (fallbackState.strongMotionHits >= requiredHits) {
          return { ok: true };
        }
        return {
          ok: false,
          detail: `Haz un círculo continuo con la cabeza, manteniéndote visible. (${fallbackState.strongMotionHits}/${requiredHits})`,
        };
      },
    },
  ];
}

async function executeChallenge(challenge, idx, total) {
  const challengeNumber = idx + 1;
  const timeoutMs = challenge.timeoutMs || CHALLENGE_TIMEOUT_MS;
  let consecutiveHits = 0;
  let lastDetail = "";
  const startAt = Date.now();

  setChallenge(`${challengeNumber}/${total}. ${challenge.text}`);
  setProgress(0);

  while (Date.now() - startAt <= timeoutMs) {
    const elapsed = Date.now() - startAt;
    setProgress(elapsed / timeoutMs);

    const result = await challenge.evaluate();
    if (result.ok) {
      consecutiveHits += 1;
      if (consecutiveHits >= challenge.requiredHits) {
        setProgress(1);
        appendChallengeLog(`Paso ${challengeNumber} completado.`, "ok");
        return true;
      }
    } else {
      consecutiveHits = 0;
      lastDetail = result.detail || "";
    }

    await delay(CHALLENGE_POLL_MS);
  }

  appendChallengeLog(
    `Paso ${challengeNumber} no completado: ${lastDetail || "tiempo agotado"}. Puedes reintentar.`,
    "fail"
  );
  return false;
}

function setButtonsForIdle() {
  const btn = document.getElementById("btn-liveness-start");
  if (btn) {
    btn.disabled = false;
  }
}

function setButtonsForRunning() {
  const btn = document.getElementById("btn-liveness-start");
  if (btn) {
    btn.disabled = true;
  }
}

function getNetworkTelemetry() {
  const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
  if (!connection) {
    return {};
  }
  return {
    network_type: connection.effectiveType || connection.type || null,
    downlink: typeof connection.downlink === "number" ? connection.downlink : null,
    rtt: typeof connection.rtt === "number" ? connection.rtt : null,
  };
}

async function getGeolocationTelemetry() {
  if (!navigator.geolocation) {
    return { geo_permission_granted: false, lat: null, lon: null, accuracy: null };
  }
  return new Promise((resolve) => {
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        resolve({
          geo_permission_granted: true,
          lat: pos.coords.latitude,
          lon: pos.coords.longitude,
          accuracy: pos.coords.accuracy,
        });
      },
      () => {
        resolve({
          geo_permission_granted: false,
          lat: null,
          lon: null,
          accuracy: null,
        });
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0,
      }
    );
  });
}

async function collectTelemetry() {
  const geo = await getGeolocationTelemetry();
  return {
    user_agent: navigator.userAgent || "",
    ...getNetworkTelemetry(),
    ...geo,
  };
}

function normalizeBase64Payload(value) {
  if (!value) {
    return null;
  }
  const raw = String(value).trim();
  let clean = raw;
  const lower = raw.toLowerCase();
  const base64Marker = ";base64,";
  const markerIndex = lower.indexOf(base64Marker);
  if (markerIndex >= 0) {
    clean = raw.slice(markerIndex + base64Marker.length);
  } else if (lower.startsWith("data:") && raw.includes(",")) {
    clean = raw.slice(raw.lastIndexOf(",") + 1);
  }
  const compact = clean.replace(/\s+/g, "");
  if (!compact) {
    return null;
  }
  const missing = compact.length % 4;
  if (!missing) {
    return compact;
  }
  return compact + "=".repeat(4 - missing);
}

function captureProbeImageBase64() {
  const video = document.getElementById("camera");
  if (!video || !video.videoWidth || !video.videoHeight) {
    return null;
  }
  const canvas = document.createElement("canvas");
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
  const dataUrl = canvas.toDataURL("image/jpeg", 0.85);
  return normalizeBase64Payload(dataUrl);
}

function canRecordVideo() {
  return Boolean(window.MediaRecorder && currentStream);
}

function preferredRecorderMime() {
  const candidates = [
    "video/webm;codecs=vp9,opus",
    "video/webm;codecs=vp8,opus",
    "video/webm",
  ];
  if (!window.MediaRecorder || !window.MediaRecorder.isTypeSupported) {
    return "video/webm";
  }
  return candidates.find((c) => window.MediaRecorder.isTypeSupported(c)) || "video/webm";
}

function startVideoRecording() {
  mediaRecorder = null;
  mediaRecorderChunks = [];
  mediaRecorderMimeType = "video/webm";
  if (!canRecordVideo()) {
    return false;
  }
  try {
    mediaRecorderMimeType = preferredRecorderMime();
    mediaRecorder = new MediaRecorder(currentStream, { mimeType: mediaRecorderMimeType });
    mediaRecorder.ondataavailable = (ev) => {
      if (ev.data && ev.data.size > 0) {
        mediaRecorderChunks.push(ev.data);
      }
    };
    mediaRecorder.start();
    return true;
  } catch (error) {
    debugLog("media recorder not available", error);
    mediaRecorder = null;
    mediaRecorderChunks = [];
    return false;
  }
}

async function stopVideoRecordingAsBase64() {
  if (!mediaRecorder) {
    return null;
  }
  const recorder = mediaRecorder;
  mediaRecorder = null;

  if (recorder.state !== "inactive") {
    await new Promise((resolve) => {
      recorder.onstop = resolve;
      recorder.stop();
    });
  }

  if (!mediaRecorderChunks.length) {
    return null;
  }

  const blob = new Blob(mediaRecorderChunks, { type: mediaRecorderMimeType || "video/webm" });
  mediaRecorderChunks = [];
  const dataUrl = await new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(new Error("No se pudo convertir el video a base64"));
    reader.readAsDataURL(blob);
  });
  return normalizeBase64Payload(dataUrl);
}

async function sendLocalFailure(reason, rawPayload = {}) {
  const username = document.getElementById("username")?.value?.trim() || "";
  if (!username) {
    return;
  }
  try {
    await fetch("/api/v1/local-failure", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username,
        action: currentAction,
        auth_channel: AUTH_CHANNEL,
        reason,
        telemetry: cachedTelemetry || (await collectTelemetry()),
        probe_image_base64: cachedProbeImage || null,
        video_base64: cachedVideoBase64 || null,
        raw_payload: rawPayload || {},
      }),
    });
  } catch (error) {
    debugLog("local failure emit failed", error);
  }
}

async function startLocalFlow(action, options = {}) {
  clearCredentialLog();
  setStatus("");
  currentAction = action;
  setLivenessHeader(currentAction);

  const trustedCheckOut = Boolean(options.skipCredentials)
    && isCheckOutAction(currentAction)
    && hasTrustedCheckOutContext();
  const usernameInput = document.getElementById("username");
  const passwordInput = document.getElementById("password");

  if (trustedCheckOut && usernameInput) {
    usernameInput.value = TRUSTED_LOGOUT_LOGIN;
  }
  const username = usernameInput?.value?.trim() || "";
  const password = trustedCheckOut ? "" : (passwordInput?.value || "");

  if (!username || (!trustedCheckOut && !password)) {
    showCredentialError("Usuario y contraseña son obligatorios.");
    return;
  }

  setCredentialButtonMode("loading");
  let credentialsOk = false;
  if (!trustedCheckOut) {
    try {
      const resp = await fetch("/api/v1/local-credentials-check", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password, action: currentAction, auth_channel: AUTH_CHANNEL }),
      });
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok || !data.ok) {
        const reason = data.block_reason === "user_without_employee"
          ? "Tu usuario no tiene empleado vinculado en Odoo."
          : data.block_reason === "demo_channel_forbidden"
            ? "Este canal biométrico está restringido al usuario administrador."
          : "Credenciales incorrectas. Verifica usuario y contraseña e intenta de nuevo.";
        showCredentialError(reason);
        return;
      }
      credentialsOk = true;
    } catch (error) {
      showCredentialError("No se pudo validar credenciales. Intenta de nuevo.");
      return;
    } finally {
      if (!credentialsOk) {
        setCredentialButtonMode("idle");
      }
    }
  } else {
    credentialsOk = true;
  }

  flowId = makeLocalId("local-flow");
  livenessSessionId = makeLocalId("local-session");
  clearChallengeLog();
  setProgress(0);
  setStep("step-liveness");
  setCredentialButtonMode("idle");

  let cameraCount = 0;
  try {
    cameraCount = await prepareCamera();
  } catch (error) {
    setLivePrompt("No se pudo activar la cámara");
    setStatus(buildCameraErrorMessage(error));
    return;
  }

  if (cameraCount === 0) {
    setLivePrompt("No se detecta cámara");
    setStatus("No se detectaron cámaras disponibles.");
    return;
  }

  await ensureFaceDetector();
  baselineMetrics = null;
  setButtonsForIdle();
  document.getElementById("btn-liveness-start").disabled = false;
  setChallenge('Presiona "Comenzar prueba" para iniciar.');
  setStatus("");
  setPrimaryButtonMode("start");
}

async function runLocalLiveness() {
  if (!flowId || !livenessSessionId) {
    setStatus("Primero inicia la sesión local de prueba.");
    return;
  }
  if (!currentStream) {
    try {
      await startCamera(document.getElementById("cameraSelect").value || null);
    } catch (error) {
      setLivePrompt("No se pudo activar la cámara");
      setStatus(buildCameraErrorMessage(error));
      return;
    }
  }
  if (livenessRunning) {
    return;
  }

  livenessRunning = true;
  setButtonsForRunning();
  setPrimaryButtonMode("running");
  clearChallengeLog();
  resetMotionBuffer();
  cachedTelemetry = null;
  cachedProbeImage = null;
  cachedVideoBase64 = null;
  let redirecting = false;
  let recordingStarted = false;

  try {
    setStatus("");
    cachedTelemetry = await collectTelemetry();
    if (!cachedTelemetry.geo_permission_granted || cachedTelemetry.lat === null || cachedTelemetry.lon === null) {
      cachedProbeImage = captureProbeImageBase64();
      await sendLocalFailure("gps_required", { step: "pre_liveness" });
      setStatus("No se pudo validar geolocalización. Debes habilitar GPS para continuar.");
      setPrimaryButtonMode("retry");
      return;
    }

    recordingStarted = startVideoRecording();

    if (faceDetector) {
      setChallenge("Calibrando rostro. Mira al frente.");
      baselineMetrics = await calibrateBaseline();
      if (!baselineMetrics) {
        cachedProbeImage = captureProbeImageBase64();
        cachedVideoBase64 = await stopVideoRecordingAsBase64();
        await sendLocalFailure("liveness_calibration_failed", { step: "calibration" });
        setStatus("No fue posible calibrar el rostro. Verifica iluminación y encuadre.");
        appendChallengeLog("Calibración fallida: rostro no detectado.", "fail");
        setPrimaryButtonMode("retry");
        return;
      }
    } else {
      baselineMetrics = null;
    }

    const challenges = buildChallenges();
    for (let i = 0; i < challenges.length; i += 1) {
      const passed = await executeChallenge(challenges[i], i, challenges.length);
      if (!passed) {
        cachedProbeImage = captureProbeImageBase64();
        cachedVideoBase64 = await stopVideoRecordingAsBase64();
        await sendLocalFailure("liveness_failed", { step: `challenge_${i + 1}` });
        setLivePrompt('Presiona "Reintentar"');
        setPrimaryButtonMode("retry");
        return;
      }
    }

    cachedProbeImage = captureProbeImageBase64();
    cachedVideoBase64 = await stopVideoRecordingAsBase64();
    if (!cachedVideoBase64) {
      await sendLocalFailure("video_capture_failed", { step: "video_recording" });
      setStatus("No se pudo capturar el video de evidencia. Reintenta la validación.");
      setPrimaryButtonMode("retry");
      return;
    }

    stopCamera();
    setLivePrompt("Procesando...");
    setStatus("");

    const username = document.getElementById("username")?.value?.trim() || "";
    const password = document.getElementById("password")?.value || "";
    const completeResp = await fetch("/api/v1/local-complete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username,
        password,
        action: currentAction,
        auth_channel: AUTH_CHANNEL,
        redirect: NEXT_URL,
        next_logout_url: NEXT_LOGOUT_URL || null,
        telemetry: cachedTelemetry,
        probe_image_base64: cachedProbeImage,
        video_base64: cachedVideoBase64,
        liveness_meta: {
          provider: "local_ui",
          passed: true,
          score: 99.0,
        },
        ...trustedLogoutPayload(),
      }),
    });
    const completeData = await completeResp.json().catch(() => ({}));
    if (!completeResp.ok) {
      const message = completeData.detail || completeResp.statusText || "Error al completar verificación";
      setStatus(`No se pudo completar autenticación: ${message}`);
      setPrimaryButtonMode("retry");
      setButtonsForIdle();
      return;
    }

    if (completeData.redirect_url) {
      redirecting = true;
      window.location.href = completeData.redirect_url;
      return;
    }

    const msg = completeData.message || "Operación completada correctamente.";
    setStatus(msg);
    setPrimaryButtonMode("start");
    setButtonsForIdle();
    resetToStart();
  } catch (error) {
    if (recordingStarted) {
      cachedVideoBase64 = cachedVideoBase64 || (await stopVideoRecordingAsBase64());
    }
    cachedProbeImage = cachedProbeImage || captureProbeImageBase64();
    await sendLocalFailure("local_flow_error", { error: String(error?.message || error) });
    setStatus(`No se pudo completar autenticación: ${error.message}`);
    setPrimaryButtonMode("retry");
    setButtonsForIdle();
  } finally {
    if (!redirecting) {
      livenessRunning = false;
      setButtonsForIdle();
      if (runMode === "running") {
        setPrimaryButtonMode("start");
      }
    }
  }
}

function resetToStart() {
  stopCamera();
  flowId = null;
  livenessSessionId = null;
  baselineMetrics = null;
  cachedTelemetry = null;
  cachedProbeImage = null;
  cachedVideoBase64 = null;
  clearChallengeLog();
  clearCredentialLog();
  setCredentialButtonMode("idle");
  setProgress(0);
  setStep("step-credentials");
  setLivePrompt("Colócate frente a la cámara");
  setStatus("");
  setChallenge('Presiona "Comenzar prueba" para iniciar.');
  setPrimaryButtonMode("start");
}

const btnStart = document.getElementById("btn-start");
if (btnStart) {
  btnStart.addEventListener("click", () => {
    startLocalFlow("check_in").catch((error) => {
      setStatus(`Error al iniciar flujo local: ${error.message}`);
    });
  });
}

const btnCheckOut = document.getElementById("btn-checkout");
if (btnCheckOut) {
  btnCheckOut.addEventListener("click", () => {
    startLocalFlow("check_out", { skipCredentials: hasTrustedCheckOutContext() }).catch((error) => {
      setStatus(`Error al iniciar flujo local: ${error.message}`);
    });
  });
}

const usernameField = document.getElementById("username");
if (usernameField) {
  usernameField.addEventListener("input", () => clearCredentialLog());
}
const passwordField = document.getElementById("password");
if (passwordField) {
  passwordField.addEventListener("input", () => clearCredentialLog());
  passwordField.addEventListener("keydown", (event) => {
  if (event.key !== "Enter") {
    return;
  }
  event.preventDefault();
  const btn = (isCheckOutAction(currentAction)
    ? document.getElementById("btn-checkout")
    : document.getElementById("btn-start"))
    || document.getElementById("btn-start")
    || document.getElementById("btn-checkout");
  if (btn && !btn.disabled) {
    btn.click();
  }
  });
}

const btnLivenessStart = document.getElementById("btn-liveness-start");
if (btnLivenessStart) {
  btnLivenessStart.addEventListener("click", () => {
    runLocalLiveness().catch((error) => {
      setStatus(`Error en prueba de vida: ${error.message}`);
      setPrimaryButtonMode("retry");
      livenessRunning = false;
      setButtonsForIdle();
    });
  });
}

const btnRefreshCameras = document.getElementById("btn-refresh-cameras");
if (btnRefreshCameras) {
  btnRefreshCameras.addEventListener("click", async () => {
  try {
    await listCameras();
    await startCamera(document.getElementById("cameraSelect").value || null);
    setLivePrompt("Cámara activa");
    setStatus("");
  } catch (error) {
    setLivePrompt("No se pudo activar la cámara");
    setStatus(buildCameraErrorMessage(error));
  }
  });
}

const cameraSelect = document.getElementById("cameraSelect");
if (cameraSelect) {
  cameraSelect.addEventListener("change", async (event) => {
  try {
    await startCamera(event.target.value || null);
    setLivePrompt("Cámara activa");
    setStatus("");
  } catch (error) {
    setLivePrompt("No se pudo activar la cámara");
    setStatus(buildCameraErrorMessage(error));
  }
  });
}

const btnBack = document.getElementById("btn-back");
if (btnBack) {
  btnBack.addEventListener("click", () => {
    resetToStart();
  });
}

window.addEventListener("beforeunload", () => {
  stopCamera();
});

setLivenessHeader(currentAction);
setLivePrompt("Colócate frente a la cámara");
if (hasTrustedCheckOutContext()) {
  const usernameInput = document.getElementById("username");
  const passwordInput = document.getElementById("password");
  if (usernameInput) {
    usernameInput.value = TRUSTED_LOGOUT_LOGIN;
    usernameInput.readOnly = true;
  }
  if (passwordInput) {
    passwordInput.value = "";
    passwordInput.disabled = true;
    passwordInput.placeholder = "No requerido para salida desde sesión activa";
  }
  setStatus("Modo salida desde sesión activa: completa prueba de vida.");
  window.setTimeout(() => {
    startLocalFlow("check_out", { skipCredentials: true }).catch((error) => {
      setStatus(`Error al iniciar flujo local: ${error.message}`);
    });
  }, 80);
} else if (!window.isSecureContext && !isLocalhostHost()) {
  setStatus("Para activar cámara en móviles, abre esta página por HTTPS.");
} else if (isCheckOutAction(currentAction)) {
  setStatus("Modo salida: ingresa usuario y contraseña, luego completa prueba de vida.");
} else {
  setStatus("");
}
