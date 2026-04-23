let currentStream = null;
let livenessRunning = false;
let faceDetector = null;
let baselineMetrics = null;
let motionCanvas = null;
let motionContext = null;
let previousMotionFrame = null;
let runMode = 'start'; // start | retry | running
const LIVENESS_DEBUG = (() => {
  try {
    return window.localStorage?.getItem('liveness_debug') === '1';
  } catch {
    return false;
  }
})();

function debugLog(...args) {
  if (!LIVENESS_DEBUG) return;
  // eslint-disable-next-line no-console
  console.debug('[liveness]', ...args);
}

function setStatus(msg) {
  document.getElementById('status').textContent = msg;
}

function setLivePrompt(msg) {
  const badge = document.getElementById('livePromptBadge');
  if (badge) {
    badge.textContent = msg;
  }
}

function promptForChallenge(text) {
  const normalized = String(text || '').toLowerCase();
  if (normalized.includes('calibr')) {
    return 'Mira al frente para calibrar';
  }
  if (normalized.includes('quiet')) {
    return 'Permanece quieto';
  }
  if (normalized.includes('circular') || normalized.includes('círculo') || normalized.includes('circulo')) {
    return 'Gira la cabeza en círculo';
  }
  if (normalized.includes('presiona')) {
    return 'Presiona "Comenzar prueba"';
  }
  if (normalized.includes('reintent')) {
    return 'Presiona "Reintentar"';
  }
  if (normalized.includes('proces')) {
    return 'Procesando...';
  }
  if (normalized.includes('complet')) {
    return 'Prueba completada';
  }
  return text;
}

function setProgress(ratio) {
  const safe = Math.max(0, Math.min(1, ratio));
  const progress = document.getElementById('challengeProgress');
  if (progress) {
    progress.style.width = `${Math.round(safe * 100)}%`;
  }
}

function clearChallengeLog() {
  const log = document.getElementById('challengeLog');
  if (log) {
    log.innerHTML = '';
  }
}

function appendChallengeLog(text, kind = '') {
  const log = document.getElementById('challengeLog');
  if (!log) {
    return;
  }
  const item = document.createElement('li');
  item.textContent = text;
  if (kind) {
    item.classList.add(kind);
  }
  log.appendChild(item);
}

function setPrimaryButtonMode(mode) {
  const btn = document.getElementById('btn-logout');
  if (!btn) {
    return;
  }
  runMode = mode;
  if (mode === 'retry') {
    btn.textContent = 'Reintentar';
    return;
  }
  if (mode === 'running') {
    btn.textContent = 'Procesando...';
    return;
  }
  btn.textContent = 'Comenzar prueba';
}

function stopCamera() {
  if (!currentStream) {
    return;
  }
  currentStream.getTracks().forEach((track) => track.stop());
  currentStream = null;
  document.getElementById('camera').srcObject = null;
}

function isLocalhostHost() {
  const host = window.location.hostname;
  return host === 'localhost' || host === '127.0.0.1' || host === '::1';
}

function buildCameraErrorMessage(error) {
  if (!window.isSecureContext && !isLocalhostHost()) {
    return 'En móviles la cámara requiere HTTPS. Abre esta URL con HTTPS para permitir acceso.';
  }
  if (error?.name === 'NotAllowedError') {
    return 'Permiso de cámara denegado. Habilítalo en el navegador y reintenta.';
  }
  if (error?.name === 'NotFoundError') {
    return 'No se detectó cámara disponible en este dispositivo.';
  }
  if (error?.name === 'NotReadableError') {
    return 'La cámara está ocupada por otra app. Cierra otras apps de cámara e intenta de nuevo.';
  }
  return `No se pudo activar la cámara: ${error?.message || 'error desconocido'}`;
}

async function getUserMediaWithFallback(deviceId = null) {
  const candidates = [];
  const hd = { width: { ideal: 1280 }, height: { ideal: 720 } };
  if (deviceId) {
    candidates.push({ video: { deviceId: { exact: deviceId }, ...hd }, audio: false });
    candidates.push({ video: { deviceId: { exact: deviceId } }, audio: false });
  }
  candidates.push({ video: { facingMode: { ideal: 'user' }, ...hd }, audio: false });
  candidates.push({ video: { facingMode: { ideal: 'user' } }, audio: false });
  candidates.push({ video: { facingMode: 'user', ...hd }, audio: false });
  candidates.push({ video: { facingMode: 'user' }, audio: false });
  candidates.push({ video: true, audio: false });

  let lastError = null;
  for (const constraints of candidates) {
    try {
      return await navigator.mediaDevices.getUserMedia(constraints);
    } catch (error) {
      lastError = error;
    }
  }
  throw lastError || new Error('No se pudo inicializar la cámara');
}

async function listCameras() {
  if (!navigator.mediaDevices?.enumerateDevices) {
    throw new Error('El navegador no soporta enumeración de cámaras');
  }
  const devices = await navigator.mediaDevices.enumerateDevices();
  const cameras = devices.filter((device) => device.kind === 'videoinput');
  const select = document.getElementById('cameraSelect');
  select.innerHTML = '';
  cameras.forEach((camera, idx) => {
    const option = document.createElement('option');
    option.value = camera.deviceId;
    option.textContent = camera.label || `Cámara ${idx + 1}`;
    select.appendChild(option);
  });
  return cameras;
}

async function startCamera(deviceId = null) {
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new Error('Este navegador/bloqueo de seguridad no permite acceso a cámara.');
  }

  stopCamera();
  currentStream = await getUserMediaWithFallback(deviceId);
  const video = document.getElementById('camera');
  video.srcObject = currentStream;
  video.setAttribute('playsinline', 'true');
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
  const selected = document.getElementById('cameraSelect').value || null;
  await startCamera(selected);
  return cameras.length;
}

function resetMotionBuffer() {
  previousMotionFrame = null;
  motionCanvas = document.createElement('canvas');
  motionCanvas.width = 96;
  motionCanvas.height = 72;
  motionContext = motionCanvas.getContext('2d', { willReadFrequently: true });
}

function readMotionScores(includeTop = false) {
  const video = document.getElementById('camera');
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
  if (!('FaceDetector' in window)) {
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
  const video = document.getElementById('camera');
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
    await delay(250);
  }
  return null;
}

function setButtonsForIdle() {
  const btn = document.getElementById('btn-logout');
  if (btn) {
    btn.disabled = false;
  }
}

function setButtonsForRunning() {
  const btn = document.getElementById('btn-logout');
  if (btn) {
    btn.disabled = true;
  }
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
        text: 'Mantén la cabeza quieta y centrada.',
        requiredHits: 5,
        evaluate: async () => {
          const metrics = await readFaceMetrics();
          if (!metrics) {
            return { ok: false, detail: 'No se detecta rostro en cámara.' };
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
            : { ok: false, detail: 'Quédate quieto y centrado unos segundos.' };
        },
      },
      {
        text: 'Mueve la cabeza en forma circular sin salir del cuadro.',
        requiredHits: 1,
        timeoutMs: 14000,
        evaluate: async () => {
          const metrics = await readFaceMetrics();
          if (!metrics) {
            return { ok: false, detail: 'No se detecta rostro en cámara.' };
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
            return { ok: false, detail: 'Amplía un poco el círculo con la cabeza.' };
          }
          if (radius > 0.24) {
            return { ok: false, detail: 'Haz el círculo más corto para no salir del encuadre.' };
          }

          if (!orbitState.startPoint) {
            orbitState.startPoint = { dx, dy };
          }
          orbitState.samples.push({ dx, dy, radius });

          if (dx >= 0 && dy < 0) orbitState.quadrants.add('q1');
          if (dx < 0 && dy < 0) orbitState.quadrants.add('q2');
          if (dx < 0 && dy >= 0) orbitState.quadrants.add('q3');
          if (dx >= 0 && dy >= 0) orbitState.quadrants.add('q4');

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
      text: 'Mantén la cabeza quieta por unos segundos.',
      requiredHits: 6,
      evaluate: async () => {
        const motion = readMotionScores(true);
        if (motion.mean < 6) {
          fallbackState.baselineMean.push(motion.mean);
          fallbackState.baselineTop.push(motion.top);
          if (fallbackState.baselineMean.length > 32) fallbackState.baselineMean.shift();
          if (fallbackState.baselineTop.length > 32) fallbackState.baselineTop.shift();
          debugLog('fallback baseline sample', motion);
          return { ok: true };
        }
        return { ok: false, detail: 'Quédate quieto y centrado.' };
      },
    },
    {
      text: 'Mueve la cabeza en círculo frente a la cámara.',
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
        debugLog('fallback motion', { motion, thresholds, hits: fallbackState.strongMotionHits });
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
  const timeoutMs = challenge.timeoutMs || 9000;
  let consecutiveHits = 0;
  let lastDetail = '';
  const startAt = Date.now();

  setLivePrompt(promptForChallenge(challenge.text));
  setProgress(0);

  while (Date.now() - startAt <= timeoutMs) {
    const elapsed = Date.now() - startAt;
    setProgress(elapsed / timeoutMs);

    const result = await challenge.evaluate();
    if (result.ok) {
      consecutiveHits += 1;
      if (consecutiveHits >= challenge.requiredHits) {
        setProgress(1);
        appendChallengeLog(`Paso ${challengeNumber} completado.`, 'ok');
        return true;
      }
    } else {
      consecutiveHits = 0;
      lastDetail = result.detail || '';
    }

    await delay(250);
  }

  appendChallengeLog(
    `Paso ${challengeNumber} no completado: ${lastDetail || 'tiempo agotado'}. Puedes reintentar.`,
    'fail'
  );
  return false;
}

async function runLogoutLiveness() {
  if (!currentStream) {
    try {
      await prepareCamera();
    } catch (error) {
      setLivePrompt('No se pudo activar la cámara');
      setStatus(buildCameraErrorMessage(error));
      return;
    }
  }
  if (livenessRunning) {
    return;
  }

  livenessRunning = true;
  setButtonsForRunning();
  setPrimaryButtonMode('running');
  clearChallengeLog();
  resetMotionBuffer();
  let redirecting = false;

  try {
    setStatus('');
    await ensureFaceDetector();

    if (faceDetector) {
      setLivePrompt('Mira al frente para calibrar');
      baselineMetrics = await calibrateBaseline();
      if (!baselineMetrics) {
        setStatus('No fue posible calibrar el rostro. Verifica iluminación y encuadre.');
        appendChallengeLog('Calibración fallida: rostro no detectado.', 'fail');
        setPrimaryButtonMode('retry');
        return;
      }
    } else {
      baselineMetrics = null;
    }

    const challenges = buildChallenges();
    for (let i = 0; i < challenges.length; i += 1) {
      const passed = await executeChallenge(challenges[i], i, challenges.length);
      if (!passed) {
        setLivePrompt('Presiona "Reintentar"');
        setPrimaryButtonMode('retry');
        return;
      }
    }

    stopCamera();
    setLivePrompt('Procesando...');
    setStatus('');
    redirecting = true;
    window.location.href = window.__NEXT_LOGOUT_URL__;
  } finally {
    if (!redirecting) {
      livenessRunning = false;
      setButtonsForIdle();
      if (runMode === 'running') {
        setPrimaryButtonMode('start');
      }
    }
  }
}

document.getElementById('btn-logout').addEventListener('click', () => {
  runLogoutLiveness().catch((error) => {
    setStatus(`Error: ${error.message}`);
    setPrimaryButtonMode('retry');
    livenessRunning = false;
    setButtonsForIdle();
  });
});

document.getElementById('btn-refresh-cameras').addEventListener('click', async () => {
  try {
    await listCameras();
    await startCamera(document.getElementById('cameraSelect').value || null);
    setLivePrompt('Cámara activa');
    setStatus('');
  } catch (error) {
    setLivePrompt('No se pudo activar la cámara');
    setStatus(buildCameraErrorMessage(error));
  }
});

document.getElementById('cameraSelect').addEventListener('change', async (event) => {
  try {
    await startCamera(event.target.value || null);
    setLivePrompt('Cámara activa');
    setStatus('');
  } catch (error) {
    setLivePrompt('No se pudo activar la cámara');
    setStatus(buildCameraErrorMessage(error));
  }
});

window.addEventListener('load', async () => {
  setPrimaryButtonMode('start');
  setLivePrompt('Colócate frente a la cámara');
  setProgress(0);
  if (!window.isSecureContext && !isLocalhostHost()) {
    setStatus('Para activar cámara en móviles, abre esta página por HTTPS.');
    return;
  }
  try {
    await listCameras();
    await startCamera(document.getElementById('cameraSelect').value || null);
    setStatus('');
    setLivePrompt('Presiona "Comenzar prueba"');
  } catch (error) {
    setStatus(buildCameraErrorMessage(error));
  }
});
