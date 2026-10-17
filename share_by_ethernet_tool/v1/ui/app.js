/**
 * Dual-Deck Dark Neumorphic Soft UI Controller
 * Tracks independent Source Upload / Destination Write speeds,
 * animates the data flow pipeline, renders the throughput sparkline,
 * and manages prominent Estimation Time (ETA).
 */

const state = {
  isConfirmed: false,
  isRunning: false,
  isScanning: false,
  settingsOpen: false,
  autoScroll: true,
  logFilter: 'all',
  logCount: 0,
  peakSpeedMbps: 0,
  options: {
    threads: 8,
    restartable: true,
    unbuffered: true,
    exclude_older: true,
    exclude_system: true,
    retry_count: 2,
    retry_wait: 2
  }
};

// Center Progress Ring Circumference (2 * PI * 50)
const RING_CIRCUMFERENCE = 314.159;

document.addEventListener('DOMContentLoaded', () => {
  setupRing();
  setInterval(pollTelemetry, 500);
  setTimeout(pollTelemetry, 100);
});

function setupRing() {
  const ring = document.getElementById('progressRingFill');
  if (ring) {
    ring.style.strokeDasharray = `${RING_CIRCUMFERENCE}`;
    ring.style.strokeDashoffset = `${RING_CIRCUMFERENCE}`;
  }
}

// ----------------------------------------------------
// BACKEND API BRIDGE
// ----------------------------------------------------
async function getApi() {
  if (window.pywebview && window.pywebview.api) {
    return window.pywebview.api;
  }
  return null;
}

async function pollTelemetry() {
  const api = await getApi();
  if (!api) return;

  try {
    const data = await api.get_telemetry();
    if (data) {
      applyTelemetry(data);
    }
  } catch (err) {
    console.error('Telemetry polling error:', err);
  }
}

function applyTelemetry(data) {
  state.isRunning = data.is_managed_running;
  state.isScanning = data.scan_busy;

  // 1. SMB Latency & System Status
  const latEl = document.getElementById('latencyText');
  if (latEl) {
    if (data.smb_latency_ms !== null && data.smb_latency_ms !== undefined) {
      latEl.innerText = `SMB Latency: ${data.smb_latency_ms} ms`;
    } else {
      latEl.innerText = data.source_reachable ? 'SMB: Connected' : 'SMB: Offline';
    }
  }

  const sysDot = document.getElementById('systemStatusDot');
  const sysText = document.getElementById('systemStatusText');
  if (state.isRunning) {
    sysDot.className = 'status-dot active';
    sysText.innerText = `Copy Running (PID ${data.managed_pid || 'Active'})`;
  } else if (data.external_processes && data.external_processes.length > 0) {
    sysDot.className = 'status-dot warning';
    const extPids = data.external_processes.map(p => p.pid).join(', ');
    sysText.innerText = `External Robocopy (${extPids})`;
  } else if (state.isScanning) {
    sysDot.className = 'status-dot warning';
    sysText.innerText = 'Scanning Folders…';
  } else {
    sysDot.className = 'status-dot online';
    sysText.innerText = 'Cockpit Ready';
  }

  // 2. LEFT DECK: SOURCE SYSTEM TELEMETRY
  const srcDot = document.getElementById('sourceDot');
  const srcText = document.getElementById('sourceStatusText');
  const srcPath = document.getElementById('sourcePathDisplay');
  if (srcPath) srcPath.innerText = data.source_path || '\\\\192.168.1.X\\SharedFolder';

  if (data.source_reachable) {
    srcDot.className = 'status-dot dot-sm online';
    srcText.innerText = 'Connected';
  } else {
    srcDot.className = 'status-dot dot-sm stopped';
    srcText.innerText = 'Offline';
  }

  // Source Upload Speed
  const srcUploadEl = document.getElementById('sourceUploadSpeed');
  const srcEq = document.getElementById('sourceEqualizer');
  if (srcUploadEl) {
    srcUploadEl.innerText = state.isRunning ? data.source_upload_formatted : '0 B/s';
  }
  if (srcEq) {
    if (state.isRunning && data.source_upload_bps > 1024) {
      srcEq.classList.add('active');
    } else {
      srcEq.classList.remove('active');
    }
  }

  // Source Disk & Files
  if (data.source_disk) {
    document.getElementById('sourceCapacityText').innerText = formatBytes(data.source_disk.total);
    document.getElementById('sourceUsedText').innerText = `Used: ${formatBytes(data.source_disk.used)}`;
    const usedPct = Math.min(100, (data.source_disk.used / data.source_disk.total) * 100);
    document.getElementById('sourceCapacityFill').style.width = `${usedPct.toFixed(1)}%`;
  }
  document.getElementById('sourceFilesCount').innerText = `${(data.source_total_files || 0).toLocaleString()}`;
  document.getElementById('sourceTotalBytes').innerText = `${formatBytes(data.source_total_bytes)} total`;

  const activeFolderEl = document.getElementById('activeFolderDisplay');
  if (activeFolderEl) {
    activeFolderEl.innerText = data.current_folder || 'Source';
  }

  // 3. RIGHT DECK: DESTINATION SYSTEM TELEMETRY
  const dstDot = document.getElementById('destDot');
  const dstText = document.getElementById('destStatusText');
  const dstPath = document.getElementById('destPathDisplay');
  if (dstPath) dstPath.innerText = data.dest_path || 'D:\\Transfer';

  if (data.dest_reachable) {
    dstDot.className = 'status-dot dot-sm online';
    dstText.innerText = 'Ready';
  } else {
    dstDot.className = 'status-dot dot-sm stopped';
    dstText.innerText = 'Drive Missing';
  }

  // Destination Download / Write Speed
  const dstDownEl = document.getElementById('destDownloadSpeed');
  const dstEq = document.getElementById('destEqualizer');
  if (dstDownEl) {
    dstDownEl.innerText = state.isRunning ? data.dest_download_formatted : '0 B/s';
  }
  if (dstEq) {
    if (state.isRunning && data.dest_download_bps > 1024) {
      dstEq.classList.add('active');
    } else {
      dstEq.classList.remove('active');
    }
  }

  // Destination Disk & Files
  if (data.dest_disk) {
    document.getElementById('destFreeText').innerText = formatBytes(data.dest_disk.free);
    document.getElementById('destTotalText').innerText = `Total: ${formatBytes(data.dest_disk.total)}`;
    const usedPct = Math.min(100, ((data.dest_disk.total - data.dest_disk.free) / data.dest_disk.total) * 100);
    document.getElementById('destCapacityFill').style.width = `${usedPct.toFixed(1)}%`;
  }
  document.getElementById('destFilesCount').innerText = `${(data.dest_copied_files || 0).toLocaleString()}`;

  const activeFileEl = document.getElementById('activeFileDisplay');
  if (activeFileEl) {
    activeFileEl.innerText = state.isRunning ? (data.current_file || 'Transferring…') : 'Waiting for transfer…';
  }

  // 4. CENTER NEXUS: DATA PIPELINE & ETA
  const pipeline = document.getElementById('flowPipeline');
  if (pipeline) {
    if (state.isRunning && (data.source_upload_bps > 1024 || data.dest_download_bps > 1024)) {
      pipeline.classList.add('active');
    } else {
      pipeline.classList.remove('active');
    }
  }

  const pct = data.progress_percent || 0;
  document.getElementById('progressPercentValue').innerText = `${pct.toFixed(1)}%`;
  document.getElementById('progressBytesCaption').innerText =
    `${formatBytes(data.dest_copied_bytes)} / ${formatBytes(data.source_total_bytes)}`;

  const ringFill = document.getElementById('progressRingFill');
  if (ringFill) {
    const offset = RING_CIRCUMFERENCE - (pct / 100) * RING_CIRCUMFERENCE;
    ringFill.style.strokeDashoffset = `${offset}`;
  }

  // Main Progress Bar Track
  const barFill = document.getElementById('mainProgressFill');
  const barThumb = document.getElementById('mainProgressThumb');
  if (barFill && barThumb) {
    barFill.style.width = `${pct}%`;
    barThumb.style.left = `${pct}%`;
  }

  // PROMINENT ESTIMATION TIME (ETA)
  const etaVal = document.getElementById('etaDisplayValue');
  const elapsedCaption = document.getElementById('elapsedCaption');
  if (state.isRunning) {
    if (data.eta_seconds && data.eta_seconds > 0) {
      etaVal.innerText = formatDurationHuman(data.eta_seconds);
    } else if (pct >= 100) {
      etaVal.innerText = 'Done';
    } else {
      etaVal.innerText = 'Estimating…';
    }
  } else {
    etaVal.innerText = pct >= 100 ? 'Complete' : '—';
  }
  if (elapsedCaption) {
    elapsedCaption.innerText = `Elapsed: ${data.elapsed_formatted || '00:00:00'}`;
  }

  document.getElementById('filesCountValue').innerText = `${(data.dest_copied_files || 0).toLocaleString()}`;
  document.getElementById('filesTotalSub').innerText = `of ${(data.source_total_files || 0).toLocaleString()} files`;

  // 5. RENDER REAL-TIME SPARKLINE CHART
  renderSparkline(data.speed_history);

  // 6. BUTTONS STATE MANAGEMENT
  updateButtonStates(data);
}

function updateButtonStates(data) {
  const btnResume = document.getElementById('btnResume');
  const btnResumeLabel = document.getElementById('btnResumeLabel');
  const btnStop = document.getElementById('btnStop');

  if (state.isRunning) {
    btnResume.disabled = true;
    btnResumeLabel.innerText = 'Copy Running';
    btnStop.disabled = false;
  } else {
    btnResumeLabel.innerText = 'Resume Copy';
    btnResume.disabled = !state.isConfirmed;
    btnStop.disabled = true;
  }
}

// ----------------------------------------------------
// SPARKLINE DUAL CANVAS RENDERER
// ----------------------------------------------------
function renderSparkline(history) {
  const canvas = document.getElementById('speedCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const w = canvas.width;
  const h = canvas.height;

  ctx.clearRect(0, 0, w, h);

  if (!history || history.length < 2) {
    ctx.fillStyle = '#64748b';
    ctx.font = '12px "JetBrains Mono"';
    ctx.fillText('Awaiting transfer throughput samples…', 20, h / 2 + 4);
    return;
  }

  // Find max speed in MB/s
  let maxSpeed = 5.0;
  history.forEach(pt => {
    if (pt.upload > maxSpeed) maxSpeed = pt.upload;
    if (pt.download > maxSpeed) maxSpeed = pt.download;
  });

  if (maxSpeed > state.peakSpeedMbps) {
    state.peakSpeedMbps = maxSpeed;
    const peakLbl = document.getElementById('peakSpeedLabel');
    if (peakLbl) peakLbl.innerText = `Peak: ${maxSpeed.toFixed(1)} MB/s`;
  }

  const stepX = w / (history.length - 1);

  // Helper function to draw smooth line
  function drawLine(key, strokeColor, fillColor) {
    ctx.beginPath();
    history.forEach((pt, idx) => {
      const val = pt[key] || 0;
      const x = idx * stepX;
      const y = h - (val / (maxSpeed * 1.15)) * (h - 14) - 4;
      if (idx === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });

    ctx.strokeStyle = strokeColor;
    ctx.lineWidth = 2.5;
    ctx.lineJoin = 'round';
    ctx.stroke();

    // Fill under line
    ctx.lineTo((history.length - 1) * stepX, h);
    ctx.lineTo(0, h);
    ctx.closePath();
    ctx.fillStyle = fillColor;
    ctx.fill();
  }

  // Draw Upload (Violet)
  drawLine('upload', '#a78bfa', 'rgba(139, 92, 246, 0.12)');

  // Draw Download (Cyan)
  drawLine('download', '#38bdf8', 'rgba(56, 189, 248, 0.15)');
}

// ----------------------------------------------------
// UI ACTIONS & BUTTON HANDLERS
// ----------------------------------------------------
function toggleConfirmSwitch() {
  if (state.isRunning) return;
  state.isConfirmed = !state.isConfirmed;
  const sw = document.getElementById('confirmSwitch');
  if (state.isConfirmed) {
    sw.classList.add('checked');
  } else {
    sw.classList.remove('checked');
  }
  const btnResume = document.getElementById('btnResume');
  if (btnResume && !state.isRunning) {
    btnResume.disabled = !state.isConfirmed;
  }
}

async function startResumeTransfer() {
  if (!state.isConfirmed || state.isRunning) return;

  const api = await getApi();
  if (!api) {
    alert('Python backend bridge is not connected yet.');
    return;
  }

  appendLog('info', 'Initiating safe resume copy with Robocopy...');
  const res = await api.start_transfer(state.options);
  if (!res.success) {
    appendLog('error', `Could not start: ${res.message}`);
    alert(res.message);
  } else {
    appendLog('success', res.message);
  }
  pollTelemetry();
}

async function stopTransfer() {
  const api = await getApi();
  if (!api) return;

  if (confirm('Stop the Robocopy transfer? Files already copied on D:\\temp will remain intact, and resume can be triggered anytime.')) {
    appendLog('warning', 'Sending stop signal to Robocopy process...');
    const res = await api.stop_transfer();
    if (!res.success) {
      appendLog('error', res.message);
      alert(res.message);
    } else {
      appendLog('success', res.message);
    }
    pollTelemetry();
  }
}

async function triggerScan() {
  const api = await getApi();
  if (!api) return;
  appendLog('info', 'Triggering folder scan & disk space verification...');
  await api.trigger_scan();
  pollTelemetry();
}

async function openDestFolder() {
  const api = await getApi();
  if (api) await api.open_folder('dest');
}

async function openSourceFolder() {
  const api = await getApi();
  if (api) await api.open_folder('source');
}

// ----------------------------------------------------
// SETTINGS DRAWER & FLAGS
// ----------------------------------------------------
function toggleSettingsDrawer() {
  state.settingsOpen = !state.settingsOpen;
  const drawer = document.getElementById('settingsDrawer');
  const label = document.getElementById('settingsToggleLabel');
  if (state.settingsOpen) {
    drawer.classList.add('open');
    label.innerText = 'Close Flags';
  } else {
    drawer.classList.remove('open');
    label.innerText = 'Transfer Flags';
  }
}

function setThreads(num) {
  state.options.threads = num;
  [4, 8, 16, 32].forEach(n => {
    const el = document.getElementById(`mt${n}`);
    if (el) {
      if (n === num) el.classList.add('active');
      else el.classList.remove('active');
    }
  });
  appendLog('info', `Robocopy multi-threading set to /MT:${num}`);
}

function toggleOption(key, el) {
  state.options[key] = !state.options[key];
  if (state.options[key]) {
    el.classList.add('checked');
    appendLog('info', `Enabled flag: ${key}`);
  } else {
    el.classList.remove('checked');
    appendLog('warning', `Disabled flag: ${key}`);
  }
}

// ----------------------------------------------------
// STREAM CONSOLE / TERMINAL LOGS
// ----------------------------------------------------
function appendLog(level, text) {
  const terminal = document.getElementById('terminalOutput');
  if (!terminal) return;

  const now = new Date();
  const timeStr = now.toTimeString().split(' ')[0];

  const entry = document.createElement('div');
  entry.className = `log-entry ${level}`;
  entry.dataset.level = level;
  entry.innerHTML = `<span class="log-time">[${timeStr}]</span> ${escapeHtml(text)}`;

  if (state.logFilter !== 'all' && state.logFilter !== level) {
    entry.style.display = 'none';
  }

  terminal.appendChild(entry);
  state.logCount++;

  const badge = document.getElementById('logCountBadge');
  if (badge) badge.innerText = `${state.logCount} events`;

  if (state.autoScroll) {
    terminal.scrollTop = terminal.scrollHeight;
  }

  if (terminal.children.length > 500) {
    terminal.removeChild(terminal.firstElementChild);
  }
}

function clearTerminalLogs() {
  const terminal = document.getElementById('terminalOutput');
  if (terminal) {
    terminal.innerHTML = '<div class="log-entry info"><span class="log-time">[Clear]</span> Console cleared by user.</div>';
    state.logCount = 1;
    const badge = document.getElementById('logCountBadge');
    if (badge) badge.innerText = `1 event`;
  }
}

function toggleAutoScroll() {
  state.autoScroll = !state.autoScroll;
  const btn = document.getElementById('btnAutoScroll');
  if (btn) {
    btn.innerText = `Auto-scroll: ${state.autoScroll ? 'ON' : 'OFF'}`;
  }
}

function setLogFilter(filter) {
  state.logFilter = filter;
  ['all', 'file', 'error'].forEach(f => {
    const el = document.getElementById(f === 'all' ? 'filterAll' : f === 'file' ? 'filterFiles' : 'filterErrors');
    if (el) {
      if (f === filter) el.classList.add('active');
      else el.classList.remove('active');
    }
  });

  const entries = document.querySelectorAll('.log-entry');
  entries.forEach(entry => {
    const lvl = entry.dataset.level;
    if (filter === 'all' || lvl === filter) {
      entry.style.display = 'block';
    } else {
      entry.style.display = 'none';
    }
  });
}

// ----------------------------------------------------
// UTILITIES
// ----------------------------------------------------
function formatBytes(bytes) {
  if (bytes === undefined || bytes === null || bytes < 0) return '0 B';
  let val = parseFloat(bytes);
  const units = ['B', 'KiB', 'MiB', 'GiB', 'TiB'];
  let idx = 0;
  while (val >= 1024 && idx < units.length - 1) {
    val /= 1024;
    idx++;
  }
  return idx === 0 ? `${parseInt(bytes).toLocaleString()} B` : `${val.toFixed(1)} ${units[idx]}`;
}

function formatDurationHuman(seconds) {
  seconds = Math.max(0, parseInt(seconds));
  if (seconds < 60) return `${seconds}s`;
  const hrs = Math.floor(seconds / 3600);
  const rem = seconds % 3600;
  const mins = Math.floor(rem / 60);
  const secs = rem % 60;
  if (hrs > 0) {
    return `~${hrs}h ${mins}m`;
  }
  return `~${mins}m ${secs}s`;
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

window.onBackendLog = function(level, text) {
  appendLog(level, text);
};
