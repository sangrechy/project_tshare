/**
 * T-Share Unified Frontend Application Logic
 * Integrates:
 * 1. Direct Cable P2P Engine with Dynamic Integrity Toggle (SHA-256 / CRC32 / None)
 * 2. LAN Web Portal (File Server & Mobile Uploads with QR Code)
 * 3. Two-Tier Verification Audits (Quick Parity + Full Cryptographic SHA-256)
 * 4. Transparent API Proxy for Browser Mode fallback
 */

// Browser Mode Transparent API Bridge Polyfill
if (!window.pywebview) {
  window.pywebview = {
    api: new Proxy({}, {
      get: (_target, prop) => {
        return async (...args) => {
          try {
            const resp = await fetch(`/api/${String(prop)}`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(args)
            });
            if (!resp.ok) {
              return { error: `HTTP ${resp.status}: ${resp.statusText}` };
            }
            return await resp.json();
          } catch (err) {
            console.error(`Browser Mode API error on ${String(prop)}:`, err);
            return { error: String(err) };
          }
        };
      }
    })
  };
}

// Application State
let activeTab = 'home';
let selectedMedium = 'ethernet';
let selectedTargetIp = '';
let selectedTargetPort = 52001;
let selectedHashMode = 'crc32';
let selectedVerifySessionId = null;
let currentPendingOffer = null;
let pollTimer = null;
let appInitialized = false;

// DOM Initialization
document.addEventListener('DOMContentLoaded', () => {
  setupTabNavigation();
  setupWireControls();
  setupPortalControls();
  setupVerifyControls();
  setupHistoryControls();
  setupSettingsControls();
  setupAuthModalControls();

  // Listen for manual IP changes
  const manualIp = document.getElementById('manualIpInput');
  const manualPort = document.getElementById('manualPortInput');
  if (manualIp) manualIp.addEventListener('input', () => { selectedTargetIp = manualIp.value.trim(); });
  if (manualPort) manualPort.addEventListener('input', () => { selectedTargetPort = parseInt(manualPort.value.trim()) || 52001; });

  const selHash = document.getElementById('selHashMode');
  if (selHash) selHash.addEventListener('change', () => { selectedHashMode = selHash.value; });

  // PyWebView Ready Check
  if (window.pywebview && window.pywebview.api) {
    initApp();
  } else {
    window.addEventListener('pywebviewready', () => { initApp(); });
    setTimeout(() => { if (!appInitialized) initApp(); }, 400);
  }
});

function initApp() {
  if (appInitialized) return;
  appInitialized = true;

  loadNetworkPill();
  loadPortalStatus();
  loadSettings();
  loadHistory();

  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(updateTelemetry, 250);
}

// ----------------- TAB NAVIGATION -----------------

function setupTabNavigation() {
  const tabs = document.querySelectorAll('.nav-tab');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const target = tab.getAttribute('data-tab');
      switchTab(target);
    });
  });
}

function switchTab(tabName) {
  activeTab = tabName;

  document.querySelectorAll('.nav-tab').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-tab') === tabName);
  });

  document.querySelectorAll('.tab-panel').forEach(p => {
    p.classList.toggle('active', p.id === `tab-${tabName}`);
  });

  if (tabName === 'history') {
    loadHistory();
  } else if (tabName === 'verify') {
    loadVerifyLedgers();
  } else if (tabName === 'portal') {
    loadPortalStatus();
  } else if (tabName === 'wire') {
    loadNetworkPill();
  }
}

// ----------------- TELEMETRY & HOME TAB -----------------

async function updateTelemetry() {
  if (!window.pywebview || !window.pywebview.api) return;

  try {
    const data = await window.pywebview.api.get_dashboard_telemetry();
    if (!data) return;

    const hw = data.hardware;
    const transfer = data.transfer;
    const role = data.active_role;

    // 1. Hardware Overview Cards
    if (hw) {
      if (hw.network && hw.network.primary_ip) {
        document.getElementById('telemetryIp').textContent = hw.network.primary_ip;
      }
      if (hw.disk) {
        document.getElementById('telemetryDiskFree').textContent = `${hw.disk.free_gb} GB Free`;
        document.getElementById('telemetryDiskBar').style.width = `${hw.disk.percent_used}%`;
      }
      if (hw.cpu) {
        document.getElementById('telemetryCpu').textContent = `${hw.cpu.percent}% (${hw.cpu.cores} Cores)`;
      }
      if (hw.ram) {
        document.getElementById('telemetryRam').textContent = `${hw.ram.available_gb} GB / ${hw.ram.total_gb} GB`;
      }
    }

    // 2. Incoming Offer on Receiver
    if (transfer && transfer.pending_offer) {
      showIncomingOffer(transfer.pending_offer);
    } else {
      hideIncomingOffer();
    }

    // 3. Active Transfer vs Idle
    const isTransferActive = (role !== 'none') && (transfer.status === 'streaming' || transfer.status === 'receiving' || transfer.status === 'connecting');

    if (isTransferActive) {
      if (activeTab !== 'home' && !window._redirectedForTransfer) {
        switchTab('home');
        window._redirectedForTransfer = true;
      }

      document.getElementById('homeActiveTransfer').classList.remove('hidden');
      document.getElementById('homeHardwareView').classList.add('hidden');

      document.getElementById('transferRoleBadge').textContent = (role === 'sender') ? 'TRANSMITTING (SENDER)' : 'RECEIVING (RECEIVER)';
      document.getElementById('liveSpeedNumber').textContent = transfer.speed_mbps ? transfer.speed_mbps.toFixed(1) : '0.0';
      document.getElementById('livePeerText').textContent = `${transfer.peer_name || 'Peer'} (${transfer.peer_ip || ''})`;

      // Integrity Mode Display
      const hashLabel = (transfer.hash_mode === 'sha256') ? 'SHA-256 (Crypto)' : ((transfer.hash_mode === 'none') ? 'Disabled (Turbo Raw)' : 'CRC32 (Fast Stream)');
      document.getElementById('liveIntegrityText').textContent = hashLabel;

      if (transfer.eta_seconds && transfer.eta_seconds > 0) {
        const mins = Math.floor(transfer.eta_seconds / 60);
        const secs = transfer.eta_seconds % 60;
        document.getElementById('liveEtaText').textContent = `${mins}m ${secs}s`;
      } else {
        document.getElementById('liveEtaText').textContent = '--:--';
      }

      const transGB = (transfer.transferred_bytes / (1024 ** 3)).toFixed(2);
      const totalGB = (transfer.total_bytes / (1024 ** 3)).toFixed(2);
      document.getElementById('liveTransferredText').textContent = `${transGB} GB / ${totalGB} GB`;

      const pct = transfer.total_bytes > 0 ? Math.min(100, Math.round((transfer.transferred_bytes / transfer.total_bytes) * 100)) : 0;
      document.getElementById('liveOverallPct').textContent = `${pct}%`;
      document.getElementById('liveOverallBar').style.width = `${pct}%`;

      document.getElementById('liveActiveFileTitle').textContent = `File [${transfer.current_file_index || 1}/${transfer.total_files || 1}]: ${transfer.current_file_name || 'Streaming...'}`;
      document.getElementById('liveStatusSubtext').textContent = (role === 'sender') ? (transfer.receiver_status || 'Streaming blocks...') : 'Receiving & verifying chunks...';

    } else {
      window._redirectedForTransfer = false;
      document.getElementById('homeActiveTransfer').classList.add('hidden');
      document.getElementById('homeHardwareView').classList.remove('hidden');

      const resumeAlert = document.getElementById('disconnectedResumeAlert');
      if (data.can_resume) {
        resumeAlert.classList.remove('hidden');
      } else {
        resumeAlert.classList.add('hidden');
      }
    }

    // 4. Update Discovered Peers
    updateDiscoveredPeers();

  } catch (err) {
    console.error('Telemetry error:', err);
  }
}

// ----------------- DIRECT CABLE CONTROLS -----------------

function setupWireControls() {
  // Medium selector
  const btnEth = document.getElementById('btnModeEthernet');
  const btnWifi = document.getElementById('btnModeWifi');
  if (btnEth && btnWifi) {
    btnEth.addEventListener('click', () => {
      btnEth.classList.add('active');
      btnWifi.classList.remove('active');
      selectedMedium = 'ethernet';
    });
    btnWifi.addEventListener('click', () => {
      btnWifi.classList.add('active');
      btnEth.classList.remove('active');
      selectedMedium = 'wifi';
    });
  }

  // File & folder selectors
  document.getElementById('btnPickFiles').addEventListener('click', async () => {
    const res = await window.pywebview.api.select_source_files();
    updateSourceSummary(res);
  });

  document.getElementById('btnPickFolder').addEventListener('click', async () => {
    const res = await window.pywebview.api.select_source_folder();
    updateSourceSummary(res);
  });

  // Destination folder selector
  document.getElementById('btnPickDestination').addEventListener('click', async () => {
    const res = await window.pywebview.api.select_destination_folder();
    if (res && res.path) {
      document.getElementById('destinationPathInput').value = res.path;
    }
  });

  // Start Transfer
  document.getElementById('btnStartTransfer').addEventListener('click', async () => {
    const manualIp = document.getElementById('manualIpInput').value.trim();
    const manualPort = parseInt(document.getElementById('manualPortInput').value.trim()) || 52001;
    const targetIp = selectedTargetIp || manualIp;

    if (!targetIp) {
      alert('Please enter a target IP address or select a discovered peer.');
      return;
    }

    const hashMode = document.getElementById('selHashMode').value;
    const res = await window.pywebview.api.start_transfer(targetIp, manualPort, hashMode);
    if (!res.success) {
      alert(`Transfer failed to start: ${res.error}`);
    } else {
      switchTab('home');
    }
  });

  // Copy Receiver Address
  document.getElementById('btnCopyReceiverAddress').addEventListener('click', () => {
    const addr = document.getElementById('receiverAddressPill').textContent;
    navigator.clipboard.writeText(addr);
    alert(`Copied to clipboard: ${addr}`);
  });

  // Emergency Cancel & Resume
  document.getElementById('btnEmergencyCancel').addEventListener('click', () => {
    window.pywebview.api.cancel_active_transfer();
  });

  document.getElementById('btnResumeTransfer').addEventListener('click', () => {
    window.pywebview.api.resume_transfer();
  });

  document.getElementById('btnHomeResume').addEventListener('click', () => {
    window.pywebview.api.resume_transfer();
  });

  // Offer Banner Actions
  document.getElementById('btnBannerAccept').addEventListener('click', async () => {
    const dest = document.getElementById('destinationPathInput').value.trim();
    const policy = document.getElementById('collisionPolicySelect').value;
    if (!dest) {
      alert('Please select a destination folder first in the Direct Cable tab.');
      switchTab('wire');
      return;
    }
    await window.pywebview.api.accept_transfer(dest, policy);
    hideIncomingOffer();
    switchTab('home');
  });

  document.getElementById('btnBannerDecline').addEventListener('click', async () => {
    await window.pywebview.api.reject_transfer("Declined by receiver user");
    hideIncomingOffer();
  });
}

function updateSourceSummary(res) {
  if (!res) return;
  const countEl = document.getElementById('selectedSourcesCount');
  const bytesEl = document.getElementById('selectedSourcesBytes');
  if (res.count > 0) {
    countEl.textContent = `${res.count} item(s) selected`;
    bytesEl.textContent = `${res.total_mb} MB`;
  } else {
    countEl.textContent = 'No files or folder selected';
    bytesEl.textContent = '0 MB';
  }
}

async function loadNetworkPill() {
  try {
    const info = await window.pywebview.api.get_my_network_info();
    if (!info) return;

    const pill = document.getElementById('receiverAddressPill');
    if (pill) pill.textContent = info.display_address;

    const destInput = document.getElementById('destinationPathInput');
    if (destInput && !destInput.value) {
      const defDest = await window.pywebview.api.select_destination_folder();
      if (defDest && defDest.path) destInput.value = defDest.path;
    }
  } catch (e) {}
}

async function updateDiscoveredPeers() {
  try {
    const peers = await window.pywebview.api.get_discovered_peers();
    const box = document.getElementById('peerList');
    if (!box) return;

    if (!peers || peers.length === 0) {
      box.innerHTML = '<div class="peer-placeholder">Searching for peers via UDP broadcast...</div>';
      return;
    }

    box.innerHTML = '';
    peers.forEach(p => {
      const card = document.createElement('div');
      card.className = `peer-card ${selectedTargetIp === p.ip ? 'active' : ''}`;
      card.innerHTML = `
        <div>
          <div class="peer-name">${p.name}</div>
          <div style="font-size: 11px; color: var(--text-dim);">${p.medium === 'wire_locked' ? '🔒 Wire Locked' : p.medium}</div>
        </div>
        <span class="peer-ip-badge">${p.ip}:${p.port}</span>
      `;
      card.onclick = () => {
        selectedTargetIp = p.ip;
        selectedTargetPort = p.port;
        document.getElementById('manualIpInput').value = p.ip;
        document.getElementById('manualPortInput').value = p.port;
        document.querySelectorAll('.peer-card').forEach(c => c.classList.remove('active'));
        card.classList.add('active');

        const wireBanner = document.getElementById('wireLockBanner');
        if (p.wire_locked) wireBanner.classList.remove('hidden');
        else wireBanner.classList.add('hidden');
      };
      box.appendChild(card);
    });
  } catch (e) {}
}

function showIncomingOffer(offer) {
  currentPendingOffer = offer;
  const banner = document.getElementById('offerNotification');
  const title = document.getElementById('offerTitle');
  const sub = document.getElementById('offerSubtitle');

  const sizeGB = (offer.total_bytes / (1024 ** 3)).toFixed(2);
  title.textContent = `Incoming Transfer from ${offer.peer_name}`;
  sub.textContent = `${offer.total_files} file(s) · ${sizeGB} GB · ${offer.hash_mode.toUpperCase()} mode`;
  banner.classList.remove('hidden');
}

function hideIncomingOffer() {
  currentPendingOffer = null;
  const banner = document.getElementById('offerNotification');
  if (banner) banner.classList.add('hidden');
}

// ----------------- LAN WEB PORTAL CONTROLS -----------------

function setupPortalControls() {
  document.getElementById('btnCopyPortalUrl').addEventListener('click', () => {
    const url = document.getElementById('portalUrlText').textContent;
    navigator.clipboard.writeText(url);
    alert(`Copied URL: ${url}`);
  });

  document.getElementById('btnOpenPortalBrowser').addEventListener('click', () => {
    const url = document.getElementById('portalUrlText').textContent;
    window.open(url, '_blank');
  });

  document.getElementById('btnSelectPortalSharedFolder').addEventListener('click', async () => {
    const res = await window.pywebview.api.select_portal_shared_folder();
    if (res && res.folder) {
      document.getElementById('portalSharedFolderInput').value = res.folder;
    }
  });

  document.getElementById('btnSelectPortalUploadsFolder').addEventListener('click', async () => {
    const res = await window.pywebview.api.select_portal_uploads_folder();
    if (res && res.folder) {
      document.getElementById('portalUploadsFolderInput').value = res.folder;
    }
  });

  document.getElementById('chkPortalAllowUploads').addEventListener('change', async (e) => {
    await window.pywebview.api.set_portal_allow_uploads(e.target.checked);
  });
}

async function loadPortalStatus() {
  try {
    const status = await window.pywebview.api.get_web_portal_status();
    if (!status) return;

    document.getElementById('portalUrlText').textContent = status.portal_url;
    document.getElementById('portalSharedFolderInput').value = status.shared_folder;
    document.getElementById('portalUploadsFolderInput').value = status.uploads_folder;
    document.getElementById('chkPortalAllowUploads').checked = status.allow_uploads;

    // Load QR SVG
    const qrSvg = await window.pywebview.api.get_portal_qr_svg();
    const qrBox = document.getElementById('portalQrContainer');
    if (qrBox && qrSvg) {
      qrBox.innerHTML = qrSvg;
    }
  } catch (e) {}
}

// ----------------- VERIFY & AUDIT CONTROLS -----------------

function setupVerifyControls() {
  const btnAudit = document.getElementById('btnRunAudit');
  btnAudit.addEventListener('click', async () => {
    if (!selectedVerifySessionId) return;
    const mode = document.querySelector('input[name="auditMode"]:checked').value;
    btnAudit.disabled = true;

    const res = await window.pywebview.api.start_verification(selectedVerifySessionId, mode);
    if (!res.success) {
      alert(`Audit failed to start: ${res.error}`);
      btnAudit.disabled = false;
    } else {
      pollAuditTelemetry();
    }
  });
}

async function loadVerifyLedgers() {
  try {
    const data = await window.pywebview.api.get_verify_ledger();
    const box = document.getElementById('verifySessionList');
    box.innerHTML = '';

    const allSessions = [
      ...(data.receiver_sessions || []),
      ...(data.sender_sessions || []),
      ...(data.portal_sessions || [])
    ];

    if (allSessions.length === 0) {
      box.innerHTML = '<div class="session-placeholder">No completed transfer sessions found to audit.</div>';
      return;
    }

    allSessions.forEach(s => {
      const item = document.createElement('div');
      item.className = `session-item ${selectedVerifySessionId === s.session_id ? 'selected' : ''}`;
      const sizeMB = (s.total_bytes / (1024 * 1024)).toFixed(1);
      item.innerHTML = `
        <div>
          <div class="session-title">[${s.role.toUpperCase()}] ${s.peer_name || 'Transfer'}</div>
          <div class="session-meta">Files: ${s.total_files} · Size: ${sizeMB} MB · Date: ${s.created_at}</div>
        </div>
        <span class="status-badge ${s.status}">${s.status}</span>
      `;
      item.onclick = () => {
        selectedVerifySessionId = s.session_id;
        document.querySelectorAll('.session-item').forEach(i => i.classList.remove('selected'));
        item.classList.add('selected');
        document.getElementById('btnRunAudit').disabled = false;
      };
      box.appendChild(item);
    });
  } catch (e) {}
}

async function pollAuditTelemetry() {
  const auditTimer = setInterval(async () => {
    try {
      const data = await window.pywebview.api.get_verify_telemetry();
      if (!data) return;

      document.getElementById('auditStatusBadge').textContent = data.status.toUpperCase();
      document.getElementById('auditStatusBadge').className = `audit-status-badge ${data.status}`;
      document.getElementById('auditSpeedText').textContent = `${data.read_speed_mbps} MB/s`;
      document.getElementById('auditFileText').textContent = data.current_file || 'Auditing files...';

      const pct = data.total_bytes > 0 ? Math.min(100, Math.round((data.bytes_checked / data.total_bytes) * 100)) : 0;
      document.getElementById('auditBar').style.width = `${pct}%`;

      if (data.details) {
        document.getElementById('auditDetailsText').textContent = data.details;
      }

      if (data.status === 'passed' || data.status === 'mismatch' || data.status === 'error') {
        clearInterval(auditTimer);
        document.getElementById('btnRunAudit').disabled = false;
      }
    } catch (e) {
      clearInterval(auditTimer);
      document.getElementById('btnRunAudit').disabled = false;
    }
  }, 300);
}

// ----------------- HISTORY CONTROLS -----------------

function setupHistoryControls() {
  document.getElementById('btnRefreshHistory').addEventListener('click', loadHistory);
}

async function loadHistory() {
  try {
    const list = await window.pywebview.api.get_history();
    const tbody = document.getElementById('historyTableBody');
    tbody.innerHTML = '';

    if (!list || list.length === 0) {
      tbody.innerHTML = '<tr><td colspan="9" class="loading-td">No transfer records found.</td></tr>';
      return;
    }

    list.forEach(item => {
      const tr = document.createElement('tr');
      const sizeMB = (item.total_bytes / (1024 * 1024)).toFixed(1);
      tr.innerHTML = `
        <td>${item.created_at || 'Recently'}</td>
        <td><strong>${item.role.toUpperCase()}</strong></td>
        <td>${item.peer_name || 'Local'} (${item.peer_ip || '127.0.0.1'})</td>
        <td>${item.total_files}</td>
        <td>${sizeMB} MB</td>
        <td>${item.avg_speed_mbps} MB/s</td>
        <td><span class="badge-v3">${(item.hash_mode || 'crc32').toUpperCase()}</span></td>
        <td><span class="status-badge ${item.status}">${item.status}</span></td>
        <td><button class="btn-secondary btn-sm" onclick="openFolder('${escapeJs(item.local_path || '')}')">Open Folder</button></td>
      `;
      tbody.appendChild(tr);
    });
  } catch (e) {}
}

function openFolder(path) {
  if (path) window.pywebview.api.open_folder(path);
}

// ----------------- SETTINGS & AUTH MODAL -----------------

function setupSettingsControls() {
  const rngRam = document.getElementById('rngRamBuffer');
  const lblRam = document.getElementById('lblRamBuffer');
  rngRam.addEventListener('input', () => { lblRam.textContent = `${rngRam.value} MB`; });

  const rngBw = document.getElementById('rngBandwidth');
  const lblBw = document.getElementById('lblBandwidth');
  rngBw.addEventListener('input', () => {
    lblBw.textContent = (rngBw.value == 0) ? 'Uncapped (Max Wire Speed)' : `${rngBw.value} Mbps`;
  });

  document.getElementById('btnSaveSettings').addEventListener('click', async () => {
    const newSettings = {
      use_full_resources: document.getElementById('chkFullResources').checked,
      default_hash_mode: document.getElementById('cfgDefaultHashMode').value,
      ram_buffer_mb: parseInt(rngRam.value),
      bandwidth_limit_mbps: parseInt(rngBw.value)
    };
    await window.pywebview.api.save_settings(newSettings);
    alert('Settings saved successfully!');
  });

  document.getElementById('btnSetupEthernet').addEventListener('click', async () => {
    const res = await window.pywebview.api.configure_ethernet("");
    if (res.need_password) {
      showAuthModal();
    } else {
      document.getElementById('netSetupStatus').textContent = res.message || res.error;
    }
  });

  document.getElementById('btnRevertEthernet').addEventListener('click', async () => {
    const res = await window.pywebview.api.revert_ethernet();
    document.getElementById('netSetupStatus').textContent = res.message || res.error;
  });
}

async function loadSettings() {
  try {
    const s = await window.pywebview.api.get_settings();
    if (!s) return;
    document.getElementById('chkFullResources').checked = s.use_full_resources;
    document.getElementById('cfgDefaultHashMode').value = s.default_hash_mode || 'crc32';
    document.getElementById('rngRamBuffer').value = s.ram_buffer_mb || 512;
    document.getElementById('lblRamBuffer').textContent = `${s.ram_buffer_mb || 512} MB`;
    document.getElementById('rngBandwidth').value = s.bandwidth_limit_mbps || 0;
    document.getElementById('lblBandwidth').textContent = (s.bandwidth_limit_mbps == 0) ? 'Uncapped (Max Wire Speed)' : `${s.bandwidth_limit_mbps} Mbps`;
  } catch (e) {}
}

function setupAuthModalControls() {
  document.getElementById('btnCancelAuth').addEventListener('click', hideAuthModal);
  document.getElementById('btnConfirmAuth').addEventListener('click', async () => {
    const pass = document.getElementById('authPasswordInput').value;
    const res = await window.pywebview.api.configure_ethernet(pass);
    if (!res.success) {
      const err = document.getElementById('authErrorMsg');
      err.textContent = res.error || 'Authentication failed';
      err.classList.remove('hidden');
    } else {
      hideAuthModal();
      document.getElementById('netSetupStatus').textContent = res.message;
    }
  });
}

function showAuthModal() {
  document.getElementById('authPasswordInput').value = '';
  document.getElementById('authErrorMsg').classList.add('hidden');
  document.getElementById('authModal').classList.remove('hidden');
}

function hideAuthModal() {
  document.getElementById('authModal').classList.add('hidden');
}

function escapeJs(str) {
  return str.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
}
