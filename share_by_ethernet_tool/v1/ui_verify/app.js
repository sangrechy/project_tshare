/**
 * Deep Verification Frontend Controller
 * Connects to Python VerificationEngine via pywebview.api,
 * renders the live audit ledger, updates SVG progress rings & ETA,
 * and handles HTML certificate export.
 */

const state = {
  mode: 'metadata',
  workers: 4,
  isRunning: false,
  filter: 'all',
  searchQuery: '',
  allRecords: [],
  logCount: 0
};

const RING_CIRCUMFERENCE = 289.027; // 2 * PI * 46

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
    const data = await api.get_verifier_status();
    if (data) {
      applyTelemetry(data);
    }
  } catch (err) {
    console.error('Verifier polling error:', err);
  }
}

function applyTelemetry(data) {
  state.isRunning = data.is_running;

  // 1. Status Pill
  const sysDot = document.getElementById('verifierStatusDot');
  const sysText = document.getElementById('verifierStatusText');
  if (state.isRunning) {
    sysDot.className = 'status-dot active';
    sysText.innerText = `Auditing (${data.mode.toUpperCase()})…`;
  } else if (data.files_processed > 0) {
    sysDot.className = data.mismatch_count === 0 && data.missing_count === 0 ? 'status-dot online' : 'status-dot stopped';
    sysText.innerText = data.mismatch_count === 0 && data.missing_count === 0 ? 'Parity 100% Verified' : 'Discrepancy Found';
  } else {
    sysDot.className = 'status-dot online';
    sysText.innerText = 'Auditor Ready';
  }

  // 2. Inventory Display
  if (data.total_source_files > 0) {
    document.getElementById('srcFilesDisplay').innerText = data.total_source_files.toLocaleString();
    document.getElementById('srcBytesDisplay').innerText = data.total_source_bytes_formatted;
  }
  if (data.total_dest_files > 0) {
    document.getElementById('dstFilesDisplay').innerText = data.total_dest_files.toLocaleString();
    document.getElementById('dstBytesDisplay').innerText = data.total_dest_bytes_formatted;
  }

  // 3. Progress Ring & Bar
  const pct = data.progress_percent || 0;
  document.getElementById('progressPercentValue').innerText = `${pct.toFixed(1)}%`;
  document.getElementById('progressBytesCaption').innerText =
    `${data.bytes_processed_formatted} / ${data.total_source_bytes_formatted || '0 B'}`;

  const ringFill = document.getElementById('progressRingFill');
  if (ringFill) {
    const offset = RING_CIRCUMFERENCE - (pct / 100) * RING_CIRCUMFERENCE;
    ringFill.style.strokeDashoffset = `${offset}`;
  }

  const barFill = document.getElementById('mainProgressFill');
  const barThumb = document.getElementById('mainProgressThumb');
  if (barFill && barThumb) {
    barFill.style.width = `${pct}%`;
    barThumb.style.left = `${pct}%`;
  }

  // 4. Hashing Throughput & Equalizer
  const speedVal = document.getElementById('hashingSpeedValue');
  const eq = document.getElementById('verifyEqualizer');
  const speedCaption = document.getElementById('speedCaption');

  if (state.isRunning && data.hashing_speed_bps > 1024) {
    speedVal.innerText = data.hashing_speed_formatted;
    eq.classList.add('active');
    speedCaption.innerText = 'Active Throughput';
  } else {
    speedVal.innerText = '0 B/s';
    eq.classList.remove('active');
    speedCaption.innerText = state.isRunning ? 'Reading metadata…' : 'Idle';
  }

  // 5. PROMINENT ESTIMATION TIME (ETA)
  const etaVal = document.getElementById('etaDisplayValue');
  const elapsedCaption = document.getElementById('elapsedCaption');
  if (state.isRunning) {
    if (data.eta_seconds && data.eta_seconds > 0) {
      etaVal.innerText = formatDurationHuman(data.eta_seconds);
    } else if (pct >= 100) {
      etaVal.innerText = 'Complete';
    } else {
      etaVal.innerText = 'Estimating…';
    }
  } else {
    etaVal.innerText = pct >= 100 ? 'Audit Done' : '—';
  }
  elapsedCaption.innerText = `Elapsed: ${data.elapsed_formatted || '00:00:00'}`;

  // 6. Matched vs Mismatched Counts
  document.getElementById('matchedCountValue').innerText = data.matched_count.toLocaleString();
  document.getElementById('discrepancySub').innerText = `${data.mismatch_count.toLocaleString()} Mismatches`;
  document.getElementById('missingSub').innerText = `${data.missing_count.toLocaleString()} Missing`;

  // 7. Active File
  const fileEl = document.getElementById('currentFileDisplay');
  if (fileEl) {
    fileEl.innerText = state.isRunning ? (data.current_file || 'Verifying…') : 'Ready (Click Start Deep Verification)';
  }

  // 8. Ledger Streaming Records
  if (data.recent_records && data.recent_records.length > 0) {
    state.allRecords = data.recent_records;
    renderLedgerTable();
  }

  // 9. Buttons
  const btnStart = document.getElementById('btnStartVerify');
  const btnStartLabel = document.getElementById('btnStartVerifyLabel');
  const btnStop = document.getElementById('btnStopVerify');

  if (state.isRunning) {
    btnStart.disabled = true;
    btnStartLabel.innerText = 'Verification In Progress…';
    btnStop.disabled = false;
  } else {
    btnStart.disabled = false;
    btnStartLabel.innerText = 'Start Deep Verification';
    btnStop.disabled = true;
  }
}

function selectMode(m) {
  if (state.isRunning) return;
  state.mode = m;
  ['metadata', 'smart', 'full_sha256'].forEach(id => {
    const card = document.getElementById(
      id === 'metadata' ? 'modeCardMetadata' : id === 'smart' ? 'modeCardSmart' : 'modeCardFull'
    );
    if (card) {
      if (id === m) card.classList.add('active');
      else card.classList.remove('active');
    }
  });
  appendLog('info', `Selected verification rigor: ${m.toUpperCase()}`);
}

function setWorkers(num) {
  if (state.isRunning) return;
  state.workers = num;
  [2, 4, 8].forEach(n => {
    const el = document.getElementById(`w${n}`);
    if (el) {
      if (n === num) el.classList.add('active');
      else el.classList.remove('active');
    }
  });
  appendLog('info', `Thread concurrency set to ${num} workers.`);
}

async function startVerification() {
  if (state.isRunning) return;
  const api = await getApi();
  if (!api) {
    alert('Python backend bridge is not connected.');
    return;
  }

  appendLog('info', `Initiating verification in ${state.mode.toUpperCase()} mode...`);
  const res = await api.start_verification(state.mode, state.workers);
  if (!res.success) {
    appendLog('error', res.message);
    alert(res.message);
  } else {
    appendLog('success', res.message);
  }
  pollTelemetry();
}

async function stopVerification() {
  const api = await getApi();
  if (api) {
    await api.stop_verification();
    appendLog('warning', 'Stop signal sent to verification workers.');
  }
}

async function exportReport() {
  const api = await getApi();
  if (api) {
    appendLog('info', 'Generating HTML Verification Certificate...');
    const res = await api.export_report();
    if (res.success) {
      appendLog('success', `Certificate saved: ${res.path}`);
      alert(`Verification Certificate successfully created and opened:\n${res.path}`);
    } else {
      appendLog('error', res.message);
    }
  }
}

async function openDestFolder() {
  const api = await getApi();
  if (api) await api.open_folder('dest');
}

// ----------------------------------------------------
// LEDGER TABLE RENDERER & FILTERS
// ----------------------------------------------------
function renderLedgerTable() {
  const tbody = document.getElementById('ledgerTableBody');
  const badge = document.getElementById('ledgerCountBadge');
  if (!tbody) return;

  let filtered = state.allRecords;

  if (state.filter === 'ok') {
    filtered = filtered.filter(r => r.status.includes('OK'));
  } else if (state.filter === 'err') {
    filtered = filtered.filter(r => !r.status.includes('OK'));
  }

  if (state.searchQuery) {
    const q = state.searchQuery.toLowerCase();
    filtered = filtered.filter(r => r.rel_path.toLowerCase().includes(q));
  }

  if (badge) badge.innerText = `${state.allRecords.length} audited`;

  if (filtered.length === 0) {
    tbody.innerHTML = '<tr><td colspan="4" class="empty-cell">No matching files found.</td></tr>';
    return;
  }

  // Render recent 50
  const rows = filtered.slice(-50).reverse().map(r => {
    const isOk = r.status.includes('OK');
    const badgeClass = isOk ? 'ok' : 'err';
    const hash = r.dest_hash || '—';
    return `
      <tr>
        <td class="file-cell" title="${escapeHtml(r.rel_path)}">${escapeHtml(r.rel_path)}</td>
        <td class="mono-cell">${formatBytes(r.size)}</td>
        <td><span class="badge-tag ${badgeClass}">${r.status}</span></td>
        <td class="mono-cell" title="${escapeHtml(hash)}">${escapeHtml(hash)}</td>
      </tr>
    `;
  });

  tbody.innerHTML = rows.join('');
}

function setFilter(flt) {
  state.filter = flt;
  ['all', 'ok', 'err'].forEach(f => {
    const el = document.getElementById(f === 'all' ? 'fltAll' : f === 'ok' ? 'fltOk' : 'fltErr');
    if (el) {
      if (f === flt) el.classList.add('active');
      else el.classList.remove('active');
    }
  });
  renderLedgerTable();
}

function filterLedger() {
  const inp = document.getElementById('searchInput');
  state.searchQuery = inp ? inp.value.trim() : '';
  renderLedgerTable();
}

// ----------------------------------------------------
// LOG STREAM
// ----------------------------------------------------
function appendLog(level, text) {
  const terminal = document.getElementById('terminalOutput');
  if (!terminal) return;

  const now = new Date();
  const timeStr = now.toTimeString().split(' ')[0];

  const entry = document.createElement('div');
  entry.className = `log-entry ${level}`;
  entry.innerHTML = `<span class="log-time">[${timeStr}]</span> ${escapeHtml(text)}`;

  terminal.appendChild(entry);
  terminal.scrollTop = terminal.scrollHeight;

  if (terminal.children.length > 300) {
    terminal.removeChild(terminal.firstElementChild);
  }
}

function clearLogs() {
  const terminal = document.getElementById('terminalOutput');
  if (terminal) {
    terminal.innerHTML = '<div class="log-entry info"><span class="log-time">[Clear]</span> Console cleared.</div>';
  }
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
  return idx === 0 ? `${parseInt(bytes).toLocaleString()} B` : `${val.toFixed(2)} ${units[idx]}`;
}

function formatDurationHuman(seconds) {
  seconds = Math.max(0, parseInt(seconds));
  if (seconds < 60) return `${seconds}s`;
  const hrs = Math.floor(seconds / 3600);
  const rem = seconds % 3600;
  const mins = Math.floor(rem / 60);
  const secs = rem % 60;
  if (hrs > 0) return `~${hrs}h ${mins}m`;
  return `~${mins}m ${secs}s`;
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

window.onBackendLog = function(level, text) {
  appendLog(level, text);
};
