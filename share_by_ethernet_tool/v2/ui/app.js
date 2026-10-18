/**
 * ⚡ T-SHARE V2: UNIFIED DESKTOP CONTROLLER
 * Full Dark Neumorphic Soft UI Physics, Dual-Deck Robocopy Telemetry,
 * Deep Cryptographic Verifier, Receiver Watcher, and SQLite History.
 */

// Ring Circumference: 2 * PI * 50 = 314.159
const RING_CIRCUMFERENCE = 314.159;

// State Store
const state = {
  activeTab: 'home',
  isTransferRunning: false,
  isVerifyRunning: false,
  isReceiverMonitoring: false,
  verifyRigor: 'metadata',
  verifyWorkers: 4,
  auditFilter: 'ALL',
  historyFilter: 'ALL',
  rawAuditLedger: [],
  speedHistory: [],
  peakSpeedMbps: 0,
};

// Canvas & Context
let sparklineCanvas = null;
let sparklineCtx = null;

// ==========================================================================
// LIFECYCLE INITIALIZATION
// ==========================================================================

document.addEventListener('DOMContentLoaded', () => {
  setupSvgRing();
  initSparklineCanvas();

  if (window.pywebview) {
    onBridgeReady();
  } else {
    window.addEventListener('pywebviewready', onBridgeReady);
  }

  // Periodic Telemetry Loop (every 500ms for smooth 60fps feel)
  setInterval(pollSystemTelemetry, 500);

  // Initial load
  setTimeout(() => {
    refreshSystemOverview();
    loadHistory();
  }, 200);
});

function onBridgeReady() {
  console.log('[T-Share v2] Native PyWebView Bridge Connected.');
  refreshSystemOverview();
  loadHistory();
}

function setupSvgRing() {
  const ring = document.getElementById('progressRingFill');
  if (ring) {
    ring.style.strokeDasharray = `${RING_CIRCUMFERENCE}`;
    ring.style.strokeDashoffset = `${RING_CIRCUMFERENCE}`;
  }
}

function initSparklineCanvas() {
  sparklineCanvas = document.getElementById('speedSparkline');
  if (sparklineCanvas) {
    sparklineCtx = sparklineCanvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    sparklineCanvas.width = sparklineCanvas.clientWidth * dpr;
    sparklineCanvas.height = sparklineCanvas.clientHeight * dpr;
    sparklineCtx.scale(dpr, dpr);
    renderSparkline([]);
  }
}

// ==========================================================================
// TAB NAVIGATION
// ==========================================================================

function switchTab(tabKey) {
  state.activeTab = tabKey;

  const tabs = [
    { key: 'home', btn: 'tabBtnHome', view: 'viewHome' },
    { key: 'send', btn: 'tabBtnSend', view: 'viewSend' },
    { key: 'receive', btn: 'tabBtnReceive', view: 'viewReceive' },
    { key: 'verify', btn: 'tabBtnVerify', view: 'viewVerify' },
    { key: 'history', btn: 'tabBtnHistory', view: 'viewHistory' },
  ];

  tabs.forEach(t => {
    const btnEl = document.getElementById(t.btn);
    const viewEl = document.getElementById(t.view);
    if (btnEl) btnEl.classList.toggle('active', t.key === tabKey);
    if (viewEl) viewEl.classList.toggle('active', t.key === tabKey);
  });

  if (tabKey === 'send') {
    setTimeout(initSparklineCanvas, 50);
  } else if (tabKey === 'history') {
    loadHistory();
  } else if (tabKey === 'home') {
    refreshSystemOverview();
  }
}

// ==========================================================================
// SYSTEM OVERVIEW & TELEMETRY POLLING
// ==========================================================================

let startupCleanupNotified = false;

async function refreshSystemOverview() {
  if (!window.pywebview || !window.pywebview.api) return;
  try {
    const data = await window.pywebview.api.get_system_overview();
    if (!data) return;

    // Startup safety check notification
    if (data.startup_cleanup && !startupCleanupNotified) {
      startupCleanupNotified = true;
      const sc = data.startup_cleanup;
      if (sc.share_name) {
        showToast(`🛡 Startup Safety: Orphaned share '${sc.share_name}' from previous session was safely revoked.`, 'info');
      }
    }

    // 1. Host Info
    if (data.machine) {
      document.getElementById('homeHostName').innerText = data.machine.hostname || 'Local';
      document.getElementById('homeHostIp').innerText = data.machine.primary_ip || '127.0.0.1';
      document.getElementById('homeHostUser').innerText = data.machine.username || 'User';

      document.getElementById('receiveUncHostDisplay').innerText = `\\\\${data.machine.hostname}\\Transfers`;
      document.getElementById('receiveUncIpDisplay').innerText = `\\\\${data.machine.primary_ip}\\Transfers`;
    }

    // 2. Network Adapters
    const adapterList = document.getElementById('homeAdapterList');
    if (adapterList && data.adapters) {
      if (data.adapters.length === 0) {
        adapterList.innerHTML = '<div style="font-size: 0.78rem; color: var(--text-muted); text-align: center; padding: 1rem;">No network adapters found.</div>';
      } else {
        adapterList.innerHTML = data.adapters.map(ad => {
          const isUp = ad.is_up;
          const statusClass = isUp ? 'online' : 'stopped';
          const ipText = ad.ips && ad.ips.length > 0 ? ad.ips.join(', ') : 'No IPv4';
          return `
            <div class="adapter-card-row">
              <div style="display: flex; align-items: center; gap: 0.65rem;">
                <span class="status-dot dot-sm ${statusClass}"></span>
                <div>
                  <div style="font-weight: 700; font-size: 0.85rem; color: var(--text-primary);">${escapeHtml(ad.name)}</div>
                  <div style="font-size: 0.72rem; color: var(--text-muted);">${escapeHtml(ad.description)}</div>
                </div>
              </div>
              <div style="display: flex; align-items: center; gap: 0.5rem;">
                <span class="adapter-badge-speed">${escapeHtml(ad.speed)}</span>
                <span style="font-family: 'JetBrains Mono', monospace; font-size: 0.74rem; color: var(--text-secondary);">${escapeHtml(ipText)}</span>
              </div>
            </div>
          `;
        }).join('');
      }
    }

    // 3. Drive Meters
    const driveList = document.getElementById('homeDriveList');
    if (driveList && data.drives) {
      driveList.innerHTML = data.drives.map(d => `
        <div class="drive-card">
          <div style="display: flex; justify-content: space-between; font-size: 0.78rem; margin-bottom: 0.35rem;">
            <strong style="color: var(--text-primary);">${d.drive}</strong>
            <span style="color: var(--text-muted); font-size: 0.73rem;">${d.free_display} free of ${d.total_display} (${d.pct_used}% used)</span>
          </div>
          <div class="mini-track">
            <div class="mini-fill fill-dest" style="width: ${d.pct_used}%;"></div>
          </div>
        </div>
      `).join('');
    }

    // 4. Lifetime Stats
    if (data.stats) {
      document.getElementById('homeStatTransfers').innerText = (data.stats.total_transfers || 0).toLocaleString();
      document.getElementById('homeStatBytes').innerText = formatBytes(data.stats.total_bytes_transferred || 0);
      document.getElementById('homeStatPeakSpeed').innerText = `${data.stats.max_speed_mbps || 0} MB/s`;
      document.getElementById('homeStatAudits').innerText = (data.stats.total_audits || 0).toLocaleString();
      document.getElementById('homeStatFilesAudited').innerText = (data.stats.total_verified_files || 0).toLocaleString();
    }

  } catch (err) {
    console.error('refreshSystemOverview error:', err);
  }
}

async function pollSystemTelemetry() {
  if (!window.pywebview || !window.pywebview.api) return;

  try {
    // 1. Transfer Telemetry
    const tData = await window.pywebview.api.get_transfer_telemetry();
    if (tData) {
      applyTransferTelemetry(tData);
    }

    // 2. Verifier Telemetry
    if (state.isVerifyRunning || state.activeTab === 'verify') {
      const vData = await window.pywebview.api.get_verifier_status();
      if (vData) {
        applyVerifierTelemetry(vData);
      }
    }

    // 3. Receiver Telemetry
    if (state.isReceiverMonitoring || state.activeTab === 'receive') {
      const rData = await window.pywebview.api.get_receiver_status();
      if (rData) {
        applyReceiverTelemetry(rData);
      }
    }

    // Update Header Pill
    updateSystemPill();

  } catch (err) {
    // ignore polling hiccups
  }
}

function updateSystemPill() {
  const dot = document.getElementById('systemStatusDot');
  const txt = document.getElementById('systemStatusText');
  if (!dot || !txt) return;

  if (state.isTransferRunning) {
    dot.className = 'status-dot active';
    txt.innerText = 'Transfer Active';
  } else if (state.isVerifyRunning) {
    dot.className = 'status-dot online';
    txt.innerText = 'Verifying Integrity';
  } else if (state.isReceiverMonitoring) {
    dot.className = 'status-dot warning';
    txt.innerText = 'Receiver Listening';
  } else {
    dot.className = 'status-dot online';
    txt.innerText = 'Cockpit Ready';
  }
}

// ==========================================================================
// FILE & FOLDER PICKER
// ==========================================================================

async function browseFolder(inputId) {
  const el = document.getElementById(inputId);
  const cur = el ? el.value.trim() : '';

  try {
    const res = await window.pywebview.api.browse_folder(cur, 'Select Directory');
    if (res && res.success && res.path) {
      el.value = res.path;
      showToast(`Selected: ${res.path}`, 'success');

      if (inputId === 'sendSourceInput') {
        window.pywebview.api.scan_source();
      } else if (inputId === 'receiveFolderInput') {
        const snippet = document.getElementById('receiveShareCmdSnippet');
        if (snippet) snippet.innerText = `net share Transfers="${res.path}" /grant:Everyone,FULL`;
      }
    }
  } catch (err) {
    console.error('browseFolder error:', err);
  }
}

function openFolder(path) {
  if (!path) {
    showToast('Path is empty.', 'warning');
    return;
  }
  window.pywebview.api.open_folder(path);
}

function openCurrentDest() {
  const p = document.getElementById('sendDestInput')?.value.trim() || document.getElementById('receiveFolderInput')?.value.trim();
  openFolder(p);
}

// ==========================================================================
// TAB 2: SEND / ROBOCOPY ENGINE
// ==========================================================================

async function startTransfer() {
  const source = document.getElementById('sendSourceInput').value.trim();
  const dest = document.getElementById('sendDestInput').value.trim();
  const threads = parseInt(document.getElementById('sendThreadsSelect').value, 10);
  const restartable = document.getElementById('sendOptRestartable').checked;
  const unbuffered = document.getElementById('sendOptUnbuffered').checked;
  const excludeOlder = document.getElementById('sendOptExcludeOlder').checked;
  const autoVerify = document.getElementById('sendOptAutoVerify').checked;

  if (!source || !dest) {
    showToast('Please specify both Source and Destination directories.', 'warning');
    return;
  }

  const options = {
    source: source,
    dest: dest,
    threads: threads,
    restartable: restartable,
    unbuffered: unbuffered,
    exclude_older: excludeOlder,
    exclude_system: true,
    retry_count: 2,
    retry_wait: 2,
    auto_verify: autoVerify,
  };

  try {
    const res = await window.pywebview.api.start_transfer(options);
    if (res && res.success) {
      showToast('Robocopy process started!', 'success');
      state.isTransferRunning = true;
      document.getElementById('btnStartTransfer').disabled = true;
      document.getElementById('btnStopTransfer').disabled = false;
    } else {
      showToast(`Transfer failed to start: ${res.message}`, 'error');
    }
  } catch (err) {
    showToast(`Error starting transfer: ${err}`, 'error');
  }
}

async function stopTransfer() {
  try {
    const res = await window.pywebview.api.stop_transfer();
    if (res && res.success) {
      showToast('Robocopy transfer cancelled.', 'warning');
      state.isTransferRunning = false;
      document.getElementById('btnStartTransfer').disabled = false;
      document.getElementById('btnStopTransfer').disabled = true;
    }
  } catch (err) {
    showToast(`Stop error: ${err}`, 'error');
  }
}

async function testSendLatency() {
  const dest = document.getElementById('sendDestInput').value.trim();
  if (!dest) {
    showToast('Please specify a destination path or IP.', 'warning');
    return;
  }
  const lbl = document.getElementById('sendDestPingLabel');
  lbl.innerText = '⚡ Pinging port 445…';

  try {
    const res = await window.pywebview.api.test_latency(dest);
    if (res && res.success) {
      lbl.innerText = `⚡ Latency: ${res.display}`;
      document.getElementById('latencyText').innerText = `SMB: ${res.display}`;
      showToast(`Destination reached: ${res.display}`, 'success');
    } else {
      lbl.innerText = '⚡ Ping: Offline';
      document.getElementById('latencyText').innerText = 'SMB: Offline';
      showToast(`Destination port 445 is unreachable: ${dest}`, 'warning');
    }
  } catch (e) {
    lbl.innerText = '⚡ Ping: Error';
  }
}

function applyTransferTelemetry(data) {
  state.isTransferRunning = data.is_managed_running;

  // Buttons
  document.getElementById('btnStartTransfer').disabled = state.isTransferRunning;
  document.getElementById('btnStopTransfer').disabled = !state.isTransferRunning;

  // Paths
  document.getElementById('sourcePathDisplay').innerText = data.source_path || 'No source directory';
  document.getElementById('destPathDisplay').innerText = data.dest_path || 'No destination directory';

  // Speed dials
  document.getElementById('sourceUploadSpeed').innerText = state.isTransferRunning ? (data.source_upload_formatted || '0 B/s') : '0 B/s';
  document.getElementById('destDownloadSpeed').innerText = state.isTransferRunning ? (data.dest_download_formatted || '0 B/s') : '0 B/s';

  // Equalizers
  const srcEq = document.getElementById('sourceEqualizer');
  const dstEq = document.getElementById('destEqualizer');
  if (state.isTransferRunning && data.source_upload_bps > 1024) srcEq?.classList.add('active');
  else srcEq?.classList.remove('active');

  if (state.isTransferRunning && data.dest_download_bps > 1024) dstEq?.classList.add('active');
  else dstEq?.classList.remove('active');

  // Center Nexus Progress Ring
  const pct = Math.min(100, Math.max(0, data.progress_percent || 0));
  document.getElementById('progressPercentValue').innerText = `${pct.toFixed(0)}%`;
  const ring = document.getElementById('progressRingFill');
  if (ring) {
    const offset = RING_CIRCUMFERENCE - (pct / 100 * RING_CIRCUMFERENCE);
    ring.style.strokeDashoffset = `${offset}`;
  }

  // Bytes & ETA
  document.getElementById('progressBytesCaption').innerText = `${formatBytes(data.dest_copied_bytes || 0)} / ${formatBytes(data.source_total_bytes || 0)}`;
  document.getElementById('etaDisplayValue').innerText = data.eta_formatted || '--:--:--';
  document.getElementById('elapsedCaption').innerText = `Elapsed: ${data.elapsed_formatted || '00:00:00'}`;

  document.getElementById('filesCountValue').innerText = (data.dest_copied_files || 0).toLocaleString();
  document.getElementById('filesTotalSub').innerText = `of ${(data.source_total_files || 0).toLocaleString()} files`;

  // Capacity & Metas
  if (data.source_disk) {
    document.getElementById('sourceCapacityText').innerText = formatBytes(data.source_disk.total);
    document.getElementById('sourceUsedText').innerText = `Used: ${formatBytes(data.source_disk.used)}`;
    const usedPct = (data.source_disk.used / data.source_disk.total) * 100;
    document.getElementById('sourceCapacityFill').style.width = `${usedPct.toFixed(1)}%`;
  }
  document.getElementById('sourceFilesCount').innerText = (data.source_total_files || 0).toLocaleString();
  document.getElementById('sourceTotalBytes').innerText = `${formatBytes(data.source_total_bytes || 0)} total`;
  document.getElementById('activeFolderDisplay').innerText = data.current_folder || 'Source';
  document.getElementById('sendSourceCountLabel').innerText = `${(data.source_total_files || 0).toLocaleString()} files indexed`;

  if (data.dest_disk) {
    document.getElementById('destFreeText').innerText = formatBytes(data.dest_disk.free);
    document.getElementById('destTotalText').innerText = `Total: ${formatBytes(data.dest_disk.total)}`;
    const freePct = (data.dest_disk.free / data.dest_disk.total) * 100;
    document.getElementById('destCapacityFill').style.width = `${freePct.toFixed(1)}%`;
  }
  document.getElementById('robocopyPidText').innerText = data.managed_pid ? `PID ${data.managed_pid}` : 'Idle';
  document.getElementById('destSpeedMbpsCaption').innerText = `${data.dest_write_speed_mbps || 0} MB/s live`;
  document.getElementById('activeDestFolderDisplay').innerText = data.dest_path ? data.dest_path.split('\\').pop() : 'Target';

  // Active File
  document.getElementById('activeFileDisplay').innerText = data.current_file || 'Idle';

  // Particles Flow
  const pipeline = document.getElementById('flowPipeline');
  if (pipeline) {
    if (state.isTransferRunning && data.dest_download_bps > 512) {
      pipeline.classList.add('active');
    } else {
      pipeline.classList.remove('active');
    }
  }

  // Home Active Banner
  const homeBanner = document.getElementById('homeActiveBanner');
  if (homeBanner) {
    if (state.isTransferRunning) {
      homeBanner.style.display = 'flex';
      document.getElementById('homeActiveFolder').innerText = `Reading: ${data.current_folder || 'Folder'}`;
      document.getElementById('homeActiveFile').innerText = data.current_file || '';
      document.getElementById('homeActiveSpeed').innerText = `${data.dest_download_formatted || '0 B/s'}`;
      document.getElementById('homeActiveEta').innerText = `ETA: ${data.eta_formatted || '--:--:--'}`;
    } else {
      homeBanner.style.display = 'none';
    }
  }

  // Sparkline Chart
  if (data.speed_history && sparklineCtx) {
    state.speedHistory = data.speed_history;
    state.peakSpeedMbps = data.peak_speed_mbps || 0;
    document.getElementById('peakSpeedDisplay').innerText = `Peak: ${state.peakSpeedMbps} MB/s`;
    renderSparkline(state.speedHistory);
  }
}

function renderSparkline(history) {
  if (!sparklineCtx || !sparklineCanvas) return;
  const w = sparklineCanvas.clientWidth;
  const h = sparklineCanvas.clientHeight;

  sparklineCtx.clearRect(0, 0, w, h);

  // Subtle Neumorphic Grid Lines
  sparklineCtx.strokeStyle = 'rgba(47, 51, 58, 0.4)';
  sparklineCtx.lineWidth = 1;
  for (let y = 0; y < h; y += 25) {
    sparklineCtx.beginPath();
    sparklineCtx.moveTo(0, y);
    sparklineCtx.lineTo(w, y);
    sparklineCtx.stroke();
  }

  if (!history || history.length < 2) return;

  let maxVal = 5.0;
  history.forEach(pt => {
    if (pt.upload_mbps > maxVal) maxVal = pt.upload_mbps;
    if (pt.download_mbps > maxVal) maxVal = pt.download_mbps;
  });
  maxVal *= 1.15;

  const stepX = w / (history.length - 1);

  // Draw Download / Destination Curve (Cyan)
  drawSparklinePath(history.map(p => p.download_mbps), '#38bdf8', 'rgba(56, 189, 248, 0.12)', maxVal, stepX, h);

  // Draw Upload / Source Curve (Violet)
  drawSparklinePath(history.map(p => p.upload_mbps), '#a78bfa', 'rgba(167, 139, 250, 0.12)', maxVal, stepX, h);
}

function drawSparklinePath(values, strokeColor, fillColor, maxVal, stepX, h) {
  if (values.length < 2) return;

  sparklineCtx.beginPath();
  sparklineCtx.moveTo(0, h - (values[0] / maxVal) * (h - 10));

  for (let i = 1; i < values.length; i++) {
    const x = i * stepX;
    const y = h - (values[i] / maxVal) * (h - 10);
    sparklineCtx.lineTo(x, y);
  }

  sparklineCtx.strokeStyle = strokeColor;
  sparklineCtx.lineWidth = 2.2;
  sparklineCtx.stroke();

  sparklineCtx.lineTo((values.length - 1) * stepX, h);
  sparklineCtx.lineTo(0, h);
  sparklineCtx.closePath();
  sparklineCtx.fillStyle = fillColor;
  sparklineCtx.fill();
}

function clearStreamLog() {
  const el = document.getElementById('consoleLog');
  if (el) el.innerHTML = '';
}

// ==========================================================================
// TAB 3: RECEIVER CONTROLLER
// ==========================================================================

async function toggleReceiverWatcher() {
  const folder = document.getElementById('receiveFolderInput').value.trim();
  const btn = document.getElementById('btnToggleReceiverWatcher');
  const txt = document.getElementById('receiveWatcherStateText');

  if (state.isReceiverMonitoring) {
    await window.pywebview.api.stop_receiver_monitoring();
    state.isReceiverMonitoring = false;
    btn.innerText = '▶ Start Folder Watcher';
    btn.className = 'btn-nm btn-primary';
    txt.innerText = 'Watcher: Stopped';
    showToast('Folder watcher stopped.', 'warning');
  } else {
    if (!folder) {
      showToast('Select an incoming folder first.', 'warning');
      return;
    }
    const res = await window.pywebview.api.start_receiver_monitoring(folder);
    if (res && res.success) {
      state.isReceiverMonitoring = true;
      btn.innerText = '■ Stop Folder Watcher';
      btn.className = 'btn-nm btn-danger';
      txt.innerText = 'Watcher: Active (Monitoring)';
      showToast(`Monitoring incoming folder: ${folder}`, 'success');
    }
  }
}

function applyReceiverTelemetry(r) {
  state.isReceiverMonitoring = r.is_monitoring;
  document.getElementById('receiveInboundSpeed').innerText = formatBytes(r.inbound_speed_bps || 0) + '/s';
  document.getElementById('receiveFilesCountCaption').innerText = `(${(r.total_files || 0).toLocaleString()} files • ${formatBytes(r.total_bytes || 0)})`;

  const tbody = document.getElementById('receiveRecentFilesBody');
  if (tbody && r.recent_files) {
    if (r.recent_files.length === 0) {
      tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--text-muted);">Listening on ${escapeHtml(r.folder || 'folder')}... No incoming files detected yet.</td></tr>`;
    } else {
      tbody.innerHTML = r.recent_files.map(f => `
        <tr>
          <td class="file-path-col">${escapeHtml(f.path)}</td>
          <td class="mono-col">${formatBytes(f.size)}</td>
          <td><span class="badge-status-pill badge-ok">RECEIVED</span></td>
          <td class="mono-col">${new Date(f.mtime * 1000).toLocaleTimeString()}</td>
        </tr>
      `).join('');
    }
  }
}

async function autoShareIncomingFolder() {
  const folder = document.getElementById('receiveFolderInput').value.trim();
  if (!folder) {
    showToast('Select an incoming folder first.', 'warning');
    return;
  }
  try {
    const res = await window.pywebview.api.create_share(folder, 'Transfers');
    if (res && res.success) {
      showToast(res.message, 'success');
      refreshSystemOverview();
    } else {
      showToast(res.message || 'Share requires Administrator privileges.', 'warning');
    }
  } catch (err) {
    showToast(`Share error: ${err}`, 'error');
  }
}

async function revokeShareIncomingFolder() {
  const folder = document.getElementById('receiveFolderInput').value.trim();
  try {
    const res = await window.pywebview.api.revoke_share('Transfers', folder);
    if (res && res.success) {
      showToast(res.message || 'Share revoked and permissions cleared.', 'success');
      refreshSystemOverview();
    } else {
      showToast(res.message || 'Could not revoke share.', 'warning');
    }
  } catch (err) {
    showToast(`Revoke error: ${err}`, 'error');
  }
}

function transferReceivedToVerifier() {
  const folder = document.getElementById('receiveFolderInput').value.trim();
  if (!folder) {
    showToast('Incoming folder is empty.', 'warning');
    return;
  }
  document.getElementById('verifySourceInput').value = folder;
  document.getElementById('verifyDestInput').value = '';
  switchTab('verify');
  showToast(`Loaded ${folder} into Deep Verifier.`, 'success');
}

// ==========================================================================
// TAB 4: DEEP VERIFICATION ENGINE
// ==========================================================================

function selectVerifyRigor(rigor) {
  state.verifyRigor = rigor;
  document.getElementById('modeCardMetadata')?.classList.toggle('active', rigor === 'metadata');
  document.getElementById('modeCardSmart')?.classList.toggle('active', rigor === 'smart');
  document.getElementById('modeCardFull')?.classList.toggle('active', rigor === 'full_sha256');
}

function setVerifyWorkers(w) {
  state.verifyWorkers = w;
  [2, 4, 8, 16].forEach(val => {
    document.getElementById(`vw${val}`)?.classList.toggle('active', val === w);
  });
}

async function startVerification() {
  const src = document.getElementById('verifySourceInput').value.trim();
  const dst = document.getElementById('verifyDestInput').value.trim();

  if (!src) {
    showToast('Please specify a Source tree to verify.', 'warning');
    return;
  }

  try {
    const res = await window.pywebview.api.start_verification(src, dst, state.verifyRigor, state.verifyWorkers);
    if (res && res.success) {
      state.isVerifyRunning = true;
      document.getElementById('btnStartVerify').disabled = true;
      document.getElementById('btnStopVerify').disabled = false;
      showToast(`Verification started (${state.verifyRigor.toUpperCase()})`, 'success');
    } else {
      showToast(`Error: ${res.message}`, 'error');
    }
  } catch (err) {
    showToast(`Verification launch error: ${err}`, 'error');
  }
}

async function stopVerification() {
  try {
    await window.pywebview.api.stop_verification();
    state.isVerifyRunning = false;
    document.getElementById('btnStartVerify').disabled = false;
    document.getElementById('btnStopVerify').disabled = true;
    showToast('Verification stopped by user.', 'warning');
  } catch (err) {
    showToast(`Stop error: ${err}`, 'error');
  }
}

function applyVerifierTelemetry(v) {
  state.isVerifyRunning = v.is_running;

  document.getElementById('btnStartVerify').disabled = state.isVerifyRunning;
  document.getElementById('btnStopVerify').disabled = !state.isVerifyRunning;

  // Wings
  document.getElementById('verifySrcFilesDisplay').innerText = (v.total_source_files || 0).toLocaleString();
  document.getElementById('verifySrcBytesDisplay').innerText = v.total_source_bytes_display || '0 B';
  document.getElementById('verifyDstFilesDisplay').innerText = (v.files_processed || 0).toLocaleString();
  document.getElementById('verifyDstBytesDisplay').innerText = v.bytes_processed_display || '0 B';

  // Stats
  document.getElementById('vStatMatched').innerText = (v.matched_count || 0).toLocaleString();
  document.getElementById('vStatMismatches').innerText = (v.mismatch_count || 0).toLocaleString();
  document.getElementById('vStatMissing').innerText = (v.missing_count || 0).toLocaleString();
  document.getElementById('vStatExtra').innerText = (v.extra_count || 0).toLocaleString();

  // Progress Bar
  const pct = v.progress_percent || 0;
  document.getElementById('verifyProgressFill').style.width = `${pct}%`;
  document.getElementById('verifyProgressPercent').innerText = `${pct.toFixed(0)}% (${(v.files_processed || 0).toLocaleString()} / ${(v.total_source_files || 0).toLocaleString()})`;
  document.getElementById('verifyActiveFile').innerText = v.current_file || 'Ready';
  document.getElementById('verifyEtaDisplay').innerText = `ETA: ${v.eta_display || '--:--:--'}`;

  // Ledger Table
  if (v.ledger && v.ledger.length > 0) {
    state.rawAuditLedger = v.ledger;
    document.getElementById('ledgerCountBadge').innerText = `${v.total_ledger_records || v.ledger.length} files`;
    renderAuditLedger();
  }
}

function filterAuditLedger(filter) {
  state.auditFilter = filter;
  document.querySelectorAll('.ledger-filters .filter-btn').forEach(btn => {
    btn.classList.toggle('active', btn.innerText.toUpperCase().includes(filter) || (filter === 'ALL' && btn.innerText === 'All'));
  });
  renderAuditLedger();
}

function onAuditSearch() {
  renderAuditLedger();
}

function renderAuditLedger() {
  const tbody = document.getElementById('auditLedgerBody');
  if (!tbody) return;

  const search = (document.getElementById('ledgerSearchInput').value || '').trim().toLowerCase();
  let rows = state.rawAuditLedger;

  if (state.auditFilter !== 'ALL') {
    if (state.auditFilter === 'MISMATCH') {
      rows = rows.filter(r => r.status === 'MISMATCH_CONTENT' || r.status === 'MISMATCH_SIZE' || r.status === 'READ_ERROR');
    } else {
      rows = rows.filter(r => r.status === state.auditFilter);
    }
  }

  if (search) {
    rows = rows.filter(r => (r.rel_path || '').toLowerCase().includes(search));
  }

  if (rows.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">No records match the current filter.</td></tr>';
    return;
  }

  // Render top 120 rows
  tbody.innerHTML = rows.slice(-120).reverse().map(r => {
    const isMatch = r.status === 'MATCH';
    const isMismatch = r.status.includes('MISMATCH') || r.status === 'READ_ERROR';
    const badgeClass = isMatch ? 'badge-ok' : (isMismatch ? 'badge-err' : 'badge-warn');

    return `
      <tr>
        <td class="file-path-col" title="${escapeHtml(r.rel_path)}">${escapeHtml(r.rel_path)}</td>
        <td class="mono-col">${formatBytes(r.source_size)}</td>
        <td class="mono-col">${formatBytes(r.dest_size)}</td>
        <td><span class="badge-status-pill ${badgeClass}">${r.status}</span></td>
        <td class="mono-col" style="font-size: 0.72rem;">${escapeHtml(r.hash || '-')}</td>
        <td style="color: var(--text-secondary); font-size: 0.73rem;">${escapeHtml(r.detail || '')}</td>
      </tr>
    `;
  }).join('');
}

async function exportVerificationCertificate() {
  try {
    const res = await window.pywebview.api.export_verification_report();
    if (res && res.success) {
      showToast(`Exported Certificate: ${res.path}`, 'success');
    } else {
      showToast(res.message || 'Error exporting certificate.', 'warning');
    }
  } catch (err) {
    showToast(`Export error: ${err}`, 'error');
  }
}

// ==========================================================================
// TAB 5: HISTORY (SQLITE DATABASE)
// ==========================================================================

async function loadHistory(filter = state.historyFilter) {
  state.historyFilter = filter;
  if (!window.pywebview || !window.pywebview.api) return;

  try {
    const res = await window.pywebview.api.get_history(100, state.historyFilter);
    const tbody = document.getElementById('historyTableBody');
    if (!tbody) return;

    if (!res || !res.records || res.records.length === 0) {
      tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; color: var(--text-muted);">No history records in database.</td></tr>';
      return;
    }

    tbody.innerHTML = res.records.map(rec => {
      const isTransfer = rec.category === 'TRANSFER';
      const isOk = (rec.status === 'COMPLETED' || rec.status === 'PASSED');
      const isErr = (rec.status === 'FAILED' || rec.status === 'INTERRUPTED');
      const badgeClass = isOk ? 'badge-ok' : (isErr ? 'badge-err' : 'badge-warn');

      return `
        <tr>
          <td class="mono-col" style="font-size: 0.74rem;">${rec.timestamp}</td>
          <td><span class="badge-status-pill ${isTransfer ? 'badge-warn' : 'badge-ok'}">${escapeHtml(rec.task_type || rec.category)}</span></td>
          <td class="file-path-col" title="${escapeHtml(rec.source_path)}">${escapeHtml(rec.source_path)}</td>
          <td class="file-path-col" title="${escapeHtml(rec.dest_path)}">${escapeHtml(rec.dest_path || '-')}</td>
          <td class="mono-col">${(rec.total_files || rec.files_processed || 0).toLocaleString()} files (${formatBytes(rec.total_bytes)})</td>
          <td class="mono-col">${rec.avg_speed_mbps || rec.hash_speed_mbps || 0} MB/s (${formatDuration(rec.duration_seconds || 0)})</td>
          <td><span class="badge-status-pill ${badgeClass}">${rec.status}</span></td>
          <td>
            <div style="display: flex; gap: 4px;">
              <button class="btn-nm btn-xs" onclick="reVerifyHistoryRow('${escapeJs(rec.source_path)}', '${escapeJs(rec.dest_path)}')">🛡 Re-Verify</button>
              <button class="btn-nm btn-xs" onclick="openFolder('${escapeJs(rec.dest_path || rec.source_path)}')">📂 Open</button>
              <button class="btn-nm btn-xs btn-danger" onclick="deleteHistoryRow('${rec.category}', ${rec.id})">✕</button>
            </div>
          </td>
        </tr>
      `;
    }).join('');

  } catch (err) {
    console.error('loadHistory error:', err);
  }
}

function filterHistoryTable(filter) {
  state.historyFilter = filter;
  document.querySelectorAll('.history-toolbar .filter-btn').forEach(btn => {
    btn.classList.toggle('active', btn.innerText.toUpperCase().includes(filter) || (filter === 'ALL' && btn.innerText.includes('All')));
  });
  loadHistory(filter);
}

async function deleteHistoryRow(category, id) {
  try {
    await window.pywebview.api.delete_history_entry(category, id);
    loadHistory();
    refreshSystemOverview();
    showToast('Record deleted.', 'info');
  } catch (err) {
    showToast(`Error: ${err}`, 'error');
  }
}

async function clearHistoryDb() {
  if (!confirm('Clear all history records from SQLite database?')) return;
  try {
    await window.pywebview.api.clear_all_history();
    loadHistory();
    refreshSystemOverview();
    showToast('History cleared.', 'info');
  } catch (err) {
    showToast(`Error: ${err}`, 'error');
  }
}

function reVerifyHistoryRow(source, dest) {
  document.getElementById('verifySourceInput').value = source;
  document.getElementById('verifyDestInput').value = dest;
  switchTab('verify');
}

// ==========================================================================
// BACKEND EVENT LISTENERS (PUSHED FROM PYTHON)
// ==========================================================================

window.onBackendLog = function(level, text) {
  const container = document.getElementById('consoleLog');
  if (!container) return;

  const div = document.createElement('div');
  div.className = `log-msg ${level}`;
  div.innerText = `[${new Date().toLocaleTimeString()}] ${text}`;
  container.appendChild(div);

  if (document.getElementById('logAutoScroll')?.checked) {
    container.scrollTop = container.scrollHeight;
  }
};

window.onTransferFinished = function(data) {
  state.isTransferRunning = false;
  document.getElementById('btnStartTransfer').disabled = false;
  document.getElementById('btnStopTransfer').disabled = true;

  if (data.success) {
    showToast(`Transfer Finished! ${data.message}`, 'success');
  } else {
    showToast(`Transfer Incomplete: ${data.message}`, 'error');
  }

  if (data.auto_verify) {
    showToast('Auto-Verify triggered: Launching Deep Verification Audit...', 'info');
    document.getElementById('verifySourceInput').value = data.source;
    document.getElementById('verifyDestInput').value = data.dest;
    switchTab('verify');
    setTimeout(() => {
      startVerification();
    }, 600);
  }

  refreshSystemOverview();
  loadHistory();
};

window.onVerificationFinished = function(data) {
  state.isVerifyRunning = false;
  document.getElementById('btnStartVerify').disabled = false;
  document.getElementById('btnStopVerify').disabled = true;

  if (data.status === 'PASSED') {
    showToast(`Audit PASSED! 100% parity across ${data.total.toLocaleString()} files.`, 'success');
  } else {
    showToast(`Audit complete: ${data.mismatches} mismatches found.`, 'warning');
  }

  refreshSystemOverview();
  loadHistory();
};

// ==========================================================================
// UTILITIES
// ==========================================================================

function formatBytes(bytes) {
  if (bytes === null || bytes === undefined || bytes < 0) return '0 B';
  const units = ['B', 'KiB', 'MiB', 'GiB', 'TiB'];
  let b = parseFloat(bytes);
  for (let i = 0; i < units.length; i++) {
    if (b < 1024.0 || i === units.length - 1) {
      return i === 0 ? `${parseInt(b, 10)} B` : `${b.toFixed(1)} ${units[i]}`;
    }
    b /= 1024.0;
  }
  return `${parseInt(bytes, 10)} B`;
}

function formatDuration(seconds) {
  const s = Math.max(0, parseInt(seconds, 10));
  const hrs = Math.floor(s / 3600);
  const rem = s % 3600;
  const mins = Math.floor(rem / 60);
  const secs = rem % 60;
  return `${String(hrs).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

function copyText(str) {
  if (navigator.clipboard) {
    navigator.clipboard.writeText(str);
    showToast(`Copied: ${str}`, 'success');
  }
}

function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerText = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(12px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function escapeJs(str) {
  if (!str) return '';
  return String(str).replace(/\\/g, '\\\\').replace(/'/g, "\\'");
}
