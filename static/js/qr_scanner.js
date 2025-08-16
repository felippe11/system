// Module to handle QR code scanning using Html5Qrcode
// Provides initScanner(containerId, onSuccess) and stopScanner()

let html5QrCode = null;
let currentCameraId = null;
const scanHistory = [];
let historyListEl = null;
let errorEl = null;
let cameraSelectEl = null;

async function startScanner(cameraId, onSuccess) {
  if (!html5QrCode) return;
  if (html5QrCode.isScanning) {
    await html5QrCode.stop();
  }
  await html5QrCode.start(
    { deviceId: { exact: cameraId } },
    { fps: 10, qrbox: 250 },
    (decodedText) => {
      scanHistory.unshift(decodedText);
      if (historyListEl) {
        const li = document.createElement('li');
        li.textContent = decodedText;
        li.className = 'list-group-item';
        historyListEl.prepend(li);
      }
      if (onSuccess) onSuccess(decodedText);
    },
    () => {}
  );
  currentCameraId = cameraId;
}

export async function initScanner(containerId, onSuccess) {
  const container = document.getElementById(containerId);
  if (!container) {
    throw new Error(`Container ${containerId} não encontrado`);
  }

  html5QrCode = new Html5Qrcode(containerId);

  // Error element
  errorEl = document.getElementById(`${containerId}-error`);
  if (!errorEl) {
    errorEl = document.createElement('div');
    errorEl.id = `${containerId}-error`;
    errorEl.className = 'text-danger mt-2';
    container.parentNode.insertBefore(errorEl, container.nextSibling);
  } else {
    errorEl.textContent = '';
  }

  // History list
  historyListEl = document.getElementById(`${containerId}-history`);
  if (!historyListEl) {
    historyListEl = document.createElement('ul');
    historyListEl.id = `${containerId}-history`;
    historyListEl.className = 'list-group w-100 mt-3';
    container.parentNode.insertBefore(historyListEl, errorEl.nextSibling);
  } else {
    historyListEl.innerHTML = '';
  }

  // Camera select
  cameraSelectEl = document.getElementById(`${containerId}-camera`);
  if (!cameraSelectEl) {
    cameraSelectEl = document.createElement('select');
    cameraSelectEl.id = `${containerId}-camera`;
    cameraSelectEl.className = 'form-select mb-2';
    container.parentNode.insertBefore(cameraSelectEl, container);
  } else {
    cameraSelectEl.innerHTML = '';
  }

  try {
    const cameras = await Html5Qrcode.getCameras();
    if (!cameras || cameras.length === 0) {
      errorEl.textContent = 'Nenhuma câmera encontrada.';
      return;
    }
    cameras.forEach((cam) => {
      const option = document.createElement('option');
      option.value = cam.id;
      option.text = cam.label;
      cameraSelectEl.appendChild(option);
    });
    cameraSelectEl.addEventListener('change', (e) => {
      startScanner(e.target.value, onSuccess);
    });
    await startScanner(cameraSelectEl.value || cameras[0].id, onSuccess);
  } catch (err) {
    if (err && err.name === 'NotAllowedError') {
      errorEl.textContent = 'Permissão de câmera negada.';
    } else {
      errorEl.textContent = `Erro ao acessar câmera: ${err.message || err}`;
    }
    throw err;
  }
}

export async function stopScanner() {
  if (html5QrCode) {
    try {
      await html5QrCode.stop();
      html5QrCode.clear();
    } catch (err) {
      // ignore
    }
    html5QrCode = null;
  }
}

export function getScanHistory() {
  return [...scanHistory];
}

