/**
 * TShare — Unified Desktop Application Logic
 * Implements 5 Navigation Menus and 3-State Rotary File Sharing Workflow
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
            console.error(`API bridge error on ${String(prop)}:`, err);
            return { error: String(err) };
          }
        };
      }
    })
  };
}

// Global State
let activeTab = 'home';
let currentSharingState = 1; // 1: Rotary, 2: Device Connect, 3: Transfer Dashboard
let selectedAction = null; // 'SEND' | 'RECEIVE'
let selectedMethod = null; // 'WIFI' | 'BLE' | 'ETHERNET'
let connectedDevice = null;
let currentPendingOffer = null;
let pollTimer = null;

// Helpers
function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  if (!container) return;
  const item = document.createElement('div');
  item.className = `toast-item ${type}`;
  item.textContent = message;
  container.appendChild(item);
  setTimeout(() => {
    item.style.opacity = '0';
    item.style.transform = 'translateY(10px)';
    item.style.transition = 'all 0.3s ease';
    setTimeout(() => item.remove(), 300);
  }, 3500);
}

function formatBytes(bytes) {
  if (!bytes || bytes <= 0) return '0.0 MB';
  const mb = bytes / (1024 * 1024);
  if (mb >= 1024) {
    return (mb / 1024).toFixed(2) + ' GB';
  }
  return mb.toFixed(1) + ' MB';
}

function formatDuration(sec) {
  if (!sec || sec <= 0) return '--:--';
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${s < 10 ? '0' : ''}${s}`;
}

// DOM Initialization
document.addEventListener('DOMContentLoaded', () => {
  setupNavigation();
  setupHomeTab();
  setupRotaryStage();
  setupDeviceConnectionStage();
  setupTransferDashboardStage();
  setupFileServerTab();
  setupVerifyTab();
  setupSettingsTab();

  // Start Background Telemetry Polling (Every 800ms)
  pollTimer = setInterval(pollAppTelemetry, 800);
  pollAppTelemetry();
});

// ========================================================
// 1. TOP NAVIGATION (5 MENUS)
// ========================================================
function setupNavigation() {
  const navTabs = document.querySelectorAll('.nav-tab');
  navTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const targetTab = tab.getAttribute('data-tab');
      switchTab(targetTab);
    });
  });
}

function switchTab(tabId) {
  activeTab = tabId;

  document.querySelectorAll('.nav-tab').forEach(t => {
    t.classList.toggle('active', t.getAttribute('data-tab') === tabId);
  });

  document.querySelectorAll('.tab-panel').forEach(p => {
    p.classList.toggle('active', p.id === `tab-${tabId}`);
  });

  if (tabId === 'file-server') {
    refreshFileServerInfo();
  } else if (tabId === 'verify') {
    loadPastAuditSessions();
  } else if (tabId === 'home') {
    loadHomeDefaultDestination();
  }
}

// ========================================================
// 2. HOME TAB
// ========================================================
function setupHomeTab() {
  loadHomeDefaultDestination();

  const btnPick = document.getElementById('btnHomePickDestination');
  const btnSave = document.getElementById('btnHomeSaveDestination');
  const inputDest = document.getElementById('homeDestinationInput');

  if (btnPick) {
    btnPick.addEventListener('click', async () => {
      try {
        const res = await window.pywebview.api.select_destination_folder();
        if (res && res.path) {
          inputDest.value = res.path;
        }
      } catch (e) {
        showToast('Error selecting folder: ' + e, 'error');
      }
    });
  }

  if (btnSave) {
    btnSave.addEventListener('click', async () => {
      const path = inputDest.value.trim();
      if (!path) {
        showToast('Please enter or select a destination path', 'error');
        return;
      }
      try {
        const res = await window.pywebview.api.save_default_destination(path);
        if (res && res.success) {
          showToast('Destination path saved as default receiving location', 'success');
        } else {
          showToast(res.error || 'Failed to save destination', 'error');
        }
      } catch (e) {
        showToast('Error saving destination: ' + e, 'error');
      }
    });
  }
}

async function loadHomeDefaultDestination() {
  try {
    const res = await window.pywebview.api.get_default_destination();
    if (res && res.path) {
      const input = document.getElementById('homeDestinationInput');
      const settingsInput = document.getElementById('settingsDestInput');
      if (input) input.value = res.path;
      if (settingsInput) settingsInput.value = res.path;
    }
  } catch (e) {
    console.error('Failed to load default destination:', e);
  }
}

// ========================================================
// 3. FILE SHARING TAB (3 States)
// ========================================================
function setSharingState(stateNum) {
  currentSharingState = stateNum;

  document.getElementById('sharingState1').classList.toggle('active', stateNum === 1);
  document.getElementById('sharingState2').classList.toggle('active', stateNum === 2);
  document.getElementById('sharingState3').classList.toggle('active', stateNum === 3);

  if (stateNum === 2) {
    initDeviceConnectionView();
  }
}

// --------------------------------------------------------
// STATE 1: ROTARY SELECTION INTERFACE
// --------------------------------------------------------
function setupRotaryStage() {
  const outerRing = document.getElementById('rotaryOuterRing');
  const btnSelect = document.getElementById('btnRotaryCenterSelect');
  const btnConfirm = document.getElementById('btnConfirmSelection');

  // Option Nodes
  const nodeSend = document.getElementById('nodeSend');
  const nodeReceive = document.getElementById('nodeReceive');
  const nodeWifi = document.getElementById('nodeWifi');
  const nodeBle = document.getElementById('nodeBle');
  const nodeEthernet = document.getElementById('nodeEthernet');

  function rotateRingTo(angleDeg) {
    if (outerRing) {
      outerRing.style.transform = `rotate(${angleDeg}deg)`;
    }
  }

  // Click SEND
  nodeSend.addEventListener('click', () => {
    selectedAction = 'SEND';
    nodeSend.classList.add('active');
    nodeReceive.classList.remove('active');
    rotateRingTo(nodeSend.getAttribute('data-angle') || 155);
    updateRotaryMirrors();
  });

  // Click RECEIVE
  nodeReceive.addEventListener('click', () => {
    selectedAction = 'RECEIVE';
    nodeReceive.classList.add('active');
    nodeSend.classList.remove('active');
    rotateRingTo(nodeReceive.getAttribute('data-angle') || 205);
    updateRotaryMirrors();
  });

  // Click WIFI
  nodeWifi.addEventListener('click', () => {
    selectedMethod = 'WIFI';
    nodeWifi.classList.add('active');
    nodeBle.classList.remove('active');
    nodeEthernet.classList.remove('active');
    rotateRingTo(nodeWifi.getAttribute('data-angle') || 90);
    updateRotaryMirrors();
  });

  // Click BLE
  nodeBle.addEventListener('click', () => {
    selectedMethod = 'BLE';
    nodeBle.classList.add('active');
    nodeWifi.classList.remove('active');
    nodeEthernet.classList.remove('active');
    rotateRingTo(nodeBle.getAttribute('data-angle') || 25);
    updateRotaryMirrors();
  });

  // Click ETHERNET
  nodeEthernet.addEventListener('click', () => {
    selectedMethod = 'ETHERNET';
    nodeEthernet.classList.add('active');
    nodeWifi.classList.remove('active');
    nodeBle.classList.remove('active');
    rotateRingTo(nodeEthernet.getAttribute('data-angle') || 335);
    updateRotaryMirrors();
  });

  function updateRotaryMirrors() {
    const badgeAction = document.getElementById('badgeSelectedAction');
    const badgeMethod = document.getElementById('badgeSelectedMethod');
    const mirrorSend = document.getElementById('mirrorSend');
    const mirrorReceive = document.getElementById('mirrorReceive');
    const mirrorWifi = document.getElementById('mirrorWifi');
    const mirrorBle = document.getElementById('mirrorBle');
    const mirrorEthernet = document.getElementById('mirrorEthernet');
    const formulaText = document.getElementById('chosenFormulaText');

    if (badgeAction) badgeAction.textContent = selectedAction || 'SELECT ACTION';
    if (badgeMethod) badgeMethod.textContent = selectedMethod || 'SELECT METHOD';

    mirrorSend.classList.toggle('active', selectedAction === 'SEND');
    mirrorReceive.classList.toggle('active', selectedAction === 'RECEIVE');

    mirrorWifi.classList.toggle('active', selectedMethod === 'WIFI');
    mirrorBle.classList.toggle('active', selectedMethod === 'BLE');
    mirrorEthernet.classList.toggle('active', selectedMethod === 'ETHERNET');

    if (selectedAction && selectedMethod) {
      formulaText.textContent = `Selected: ${selectedAction} + ${selectedMethod}`;
      btnConfirm.disabled = false;
    } else if (selectedAction) {
      formulaText.textContent = `Action: ${selectedAction} · Now select Connection Method`;
      btnConfirm.disabled = true;
    } else if (selectedMethod) {
      formulaText.textContent = `Method: ${selectedMethod} · Now select SEND or RECEIVE`;
      btnConfirm.disabled = true;
    } else {
      formulaText.textContent = 'Please make your selection';
      btnConfirm.disabled = true;
    }
  }

  function handleConfirm() {
    if (!selectedAction || !selectedMethod) {
      showToast('Please select both an Action (SEND/RECEIVE) and a Connection Method (WIFI/BLE/ETHERNET)', 'error');
      return;
    }
    // Transition to State 2
    setSharingState(2);
  }

  btnSelect.addEventListener('click', handleConfirm);
  btnConfirm.addEventListener('click', handleConfirm);
}

// --------------------------------------------------------
// STATE 2: DEVICE CONNECTION INTERFACE
// --------------------------------------------------------
function setupDeviceConnectionStage() {
  const btnBack = document.getElementById('btnBackToRotary');
  const tabManual = document.getElementById('tabManualConnect');
  const tabAuto = document.getElementById('tabAutoFind');
  const btnDoConnect = document.getElementById('btnDoManualConnect');
  const btnTriggerScan = document.getElementById('btnTriggerScan');

  btnBack.addEventListener('click', () => {
    setSharingState(1);
  });

  tabManual.addEventListener('click', () => {
    tabManual.classList.add('active');
    tabAuto.classList.remove('active');
    document.getElementById('viewManualConnect').classList.add('active');
    document.getElementById('viewAutoFind').classList.remove('active');
  });

  tabAuto.addEventListener('click', () => {
    tabAuto.classList.add('active');
    tabManual.classList.remove('active');
    document.getElementById('viewAutoFind').classList.add('active');
    document.getElementById('viewManualConnect').classList.remove('active');
    triggerDeviceScan();
  });

  btnDoConnect.addEventListener('click', async () => {
    await performManualConnection();
  });

  btnTriggerScan.addEventListener('click', () => {
    triggerDeviceScan();
  });

  // Direct Cable IP Setup Button
  const btnAutoIp = document.getElementById('btnAutoSetupEthIp');
  if (btnAutoIp) {
    btnAutoIp.addEventListener('click', async () => {
      try {
        const res = await window.pywebview.api.configure_ethernet('');
        if (res.requires_sudo) {
          openAuthModal();
        } else if (res.success) {
          showToast('Direct cable interface configured (192.168.123.x)', 'success');
          document.getElementById('inputManualIp').value = '192.168.123.1';
        } else {
          showToast(res.error || 'Failed to setup cable IP', 'error');
        }
      } catch (e) {
        showToast('Configuration error: ' + e, 'error');
      }
    });
  }

  // Sender File Selection Buttons
  const btnPickFiles = document.getElementById('btnState2PickFiles');
  const btnPickFolder = document.getElementById('btnState2PickFolder');
  const btnClearFiles = document.getElementById('btnState2ClearFiles');
  const btnStartSend = document.getElementById('btnState2StartSend');

  btnPickFiles.addEventListener('click', async () => {
    try {
      const summary = await window.pywebview.api.select_source_files();
      renderSelectedFiles(summary);
    } catch (e) {
      showToast('Error picking files: ' + e, 'error');
    }
  });

  btnPickFolder.addEventListener('click', async () => {
    try {
      const summary = await window.pywebview.api.select_source_folder();
      renderSelectedFiles(summary);
    } catch (e) {
      showToast('Error picking folder: ' + e, 'error');
    }
  });

  btnClearFiles.addEventListener('click', async () => {
    try {
      const summary = await window.pywebview.api.clear_source_paths();
      renderSelectedFiles(summary);
    } catch (e) {
      showToast('Error clearing: ' + e, 'error');
    }
  });

  btnStartSend.addEventListener('click', async () => {
    await startSendingFiles();
  });

  // Receiver Incoming Offer Buttons
  const btnOfferAccept = document.getElementById('btnOfferAccept');
  const btnOfferReject = document.getElementById('btnOfferReject');
  const btnOfferBrowseDest = document.getElementById('btnOfferBrowseDest');

  btnOfferBrowseDest.addEventListener('click', async () => {
    try {
      const res = await window.pywebview.api.select_destination_folder();
      if (res && res.path) {
        document.getElementById('offerDestInput').value = res.path;
      }
    } catch (e) {
      showToast('Error selecting destination: ' + e, 'error');
    }
  });

  btnOfferAccept.addEventListener('click', async () => {
    const dest = document.getElementById('offerDestInput').value.trim();
    if (!dest) {
      showToast('Please select destination directory', 'error');
      return;
    }
    try {
      const res = await window.pywebview.api.accept_transfer(dest, 'keep_both');
      if (res && res.success) {
        setSharingState(3); // Transition to State 3!
      } else {
        showToast(res.error || 'Failed to accept transfer', 'error');
      }
    } catch (e) {
      showToast('Accept error: ' + e, 'error');
    }
  });

  btnOfferReject.addEventListener('click', async () => {
    try {
      await window.pywebview.api.reject_transfer('User declined in dialog');
      document.getElementById('state2IncomingOfferBox').classList.add('hidden');
      showToast('Transfer request declined', 'info');
    } catch (e) {
      showToast('Reject error: ' + e, 'error');
    }
  });
}

function initDeviceConnectionView() {
  const badge = document.getElementById('state2SelectedBadge');
  const desc = document.getElementById('manualModeDesc');
  const groupPort = document.getElementById('groupManualPort');
  const helperBox = document.getElementById('ethernetHelperBox');
  const lblIp = document.getElementById('lblManualIp');
  const inputIp = document.getElementById('inputManualIp');

  badge.textContent = `Selected: ${selectedAction} + ${selectedMethod}`;

  // Role Action Deck (Show Send Deck or Receive Deck)
  document.getElementById('roleSendActionDeck').classList.toggle('active', selectedAction === 'SEND');
  document.getElementById('roleReceiveActionDeck').classList.toggle('active', selectedAction === 'RECEIVE');

  // Connection Medium Customization
  if (selectedMethod === 'WIFI') {
    desc.textContent = 'Enter the target device Wi-Fi IP address and receiver port.';
    lblIp.textContent = 'Target Wi-Fi IP Address:';
    inputIp.placeholder = '192.168.1.x';
    groupPort.classList.remove('hidden');
    helperBox.classList.add('hidden');
  } else if (selectedMethod === 'ETHERNET') {
    desc.textContent = 'Enter the direct Ethernet IP address (192.168.123.x) or setup cable interface.';
    lblIp.textContent = 'Target Ethernet IP Address:';
    inputIp.placeholder = '192.168.123.1';
    groupPort.classList.remove('hidden');
    helperBox.classList.remove('hidden');
  } else if (selectedMethod === 'BLE') {
    desc.textContent = 'Enter the target Bluetooth device identifier or MAC address.';
    lblIp.textContent = 'Target BLE Identifier:';
    inputIp.placeholder = 'TSHARE-DEVICE-ID or MAC';
    groupPort.classList.add('hidden');
    helperBox.classList.add('hidden');
  }

  // Load existing source files summary if Send
  if (selectedAction === 'SEND') {
    window.pywebview.api.get_source_paths().then(renderSelectedFiles).catch(() => {});
  }
}

async function performManualConnection() {
  const ip = document.getElementById('inputManualIp').value.trim();
  const port = parseInt(document.getElementById('inputManualPort').value, 10) || 52001;
  const banner = document.getElementById('connValidationBanner');
  const bannerTitle = document.getElementById('connStatusTitle');
  const bannerMsg = document.getElementById('connStatusMsg');

  if (!ip) {
    showToast('Please enter target IP address or identifier', 'error');
    return;
  }

  banner.classList.remove('hidden', 'success', 'error');
  bannerTitle.textContent = 'Connecting...';
  bannerMsg.textContent = `Validating ${selectedMethod} connection to ${ip}...`;

  try {
    const res = await window.pywebview.api.connect_device(ip, port, selectedMethod.toLowerCase());
    if (res && res.success) {
      banner.classList.add('success');
      bannerTitle.textContent = 'Connected';
      bannerMsg.textContent = `Connection verified with target (${res.medium.toUpperCase()})`;
      connectedDevice = { ip, port, medium: res.medium };
      showToast(`Connected to ${ip}:${port}`, 'success');
    } else {
      banner.classList.add('error');
      bannerTitle.textContent = 'Connection Failed';
      bannerMsg.textContent = res.error || 'Could not reach target device';
      connectedDevice = null;
    }
  } catch (e) {
    banner.classList.add('error');
    bannerTitle.textContent = 'Connection Error';
    bannerMsg.textContent = String(e);
    connectedDevice = null;
  }
}

async function triggerDeviceScan() {
  const statusText = document.getElementById('discoveryStatusText');
  const dot = document.getElementById('discoveryDot');
  const list = document.getElementById('discoveredDevicesList');

  statusText.textContent = 'Searching for devices...';
  dot.classList.add('pulse-dot');
  list.innerHTML = '<div class="device-placeholder">Scanning local network for TShare peers...</div>';

  try {
    const peers = await window.pywebview.api.get_discovered_peers();
    if (!peers || peers.length === 0) {
      list.innerHTML = '<div class="device-placeholder">No devices discovered yet. Ensure peer is running TShare.</div>';
      statusText.textContent = 'Scan idle (0 devices found)';
      return;
    }

    list.innerHTML = '';
    peers.forEach(peer => {
      const card = document.createElement('div');
      card.className = 'device-card-item';
      card.innerHTML = `
        <div class="device-info-left">
          <span class="device-info-name">${peer.hostname || 'TShare Peer'}</span>
          <span class="device-info-meta">${peer.ip}:${peer.port || 52001} · ${peer.medium || 'Wire'}</span>
        </div>
        <button class="btn-primary btn-sm btn-select-peer" data-ip="${peer.ip}" data-port="${peer.port || 52001}">
          SELECT
        </button>
      `;
      list.appendChild(card);
    });

    list.querySelectorAll('.btn-select-peer').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const ip = e.target.getAttribute('data-ip');
        const port = e.target.getAttribute('data-port');
        document.getElementById('inputManualIp').value = ip;
        document.getElementById('inputManualPort').value = port;
        connectedDevice = { ip, port: parseInt(port, 10), medium: selectedMethod.toLowerCase() };
        showToast(`Selected device: ${ip}`, 'success');
      });
    });

    statusText.textContent = `Found ${peers.length} active device(s)`;
  } catch (e) {
    statusText.textContent = 'Scan error';
    list.innerHTML = `<div class="device-placeholder text-danger">Discovery error: ${e}</div>`;
  }
}

function renderSelectedFiles(summary) {
  const countEl = document.getElementById('state2FilesCount');
  const bytesEl = document.getElementById('state2FilesBytes');
  const listEl = document.getElementById('state2FileList');

  if (!summary) return;

  countEl.textContent = `${summary.count || 0} Files Selected`;
  bytesEl.textContent = formatBytes(summary.total_bytes || 0);

  if (!summary.items || summary.items.length === 0) {
    listEl.innerHTML = '<div class="file-placeholder">No files chosen. Click Select Files or Select Folder.</div>';
    return;
  }

  listEl.innerHTML = '';
  summary.items.forEach((item, idx) => {
    const row = document.createElement('div');
    row.className = 'file-item-row';
    row.innerHTML = `
      <div class="file-item-name" title="${item.path}">
        <strong>${item.name}</strong> ${item.is_dir ? '(Folder)' : `(${formatBytes(item.size)})`}
      </div>
      <button class="btn-icon btn-remove-file" data-idx="${idx}" title="Remove file">✕</button>
    `;
    listEl.appendChild(row);
  });

  listEl.querySelectorAll('.btn-remove-file').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      const idx = parseInt(e.target.getAttribute('data-idx'), 10);
      try {
        const updated = await window.pywebview.api.remove_source_path(idx);
        renderSelectedFiles(updated);
      } catch (err) {
        showToast('Error removing file: ' + err, 'error');
      }
    });
  });
}

async function startSendingFiles() {
  const ip = document.getElementById('inputManualIp').value.trim();
  const port = parseInt(document.getElementById('inputManualPort').value, 10) || 52001;
  const hashMode = document.getElementById('state2HashModeSelect').value;

  if (!ip) {
    showToast('Please specify target IP or select device', 'error');
    return;
  }

  try {
    const res = await window.pywebview.api.start_transfer(ip, port, hashMode);
    if (res && res.success) {
      showToast(`Transfer initialized (${hashMode.toUpperCase()} mode)`, 'success');
      setSharingState(3); // Transition to State 3!
    } else {
      showToast(res.error || 'Failed to start transfer', 'error');
    }
  } catch (e) {
    showToast('Transfer start error: ' + e, 'error');
  }
}

// --------------------------------------------------------
// STATE 3: TRANSFER MONITORING DASHBOARD
// --------------------------------------------------------
function setupTransferDashboardStage() {
  const btnCancel = document.getElementById('btnCancelActiveTransfer');
  const btnReturn = document.getElementById('btnReturnToSelection');
  const btnCompleteReturn = document.getElementById('btnCompleteReturn');
  const btnClearLogs = document.getElementById('btnClearDashLogs');

  btnCancel.addEventListener('click', async () => {
    try {
      await window.pywebview.api.cancel_active_transfer();
      showToast('Transfer cancel requested', 'info');
    } catch (e) {
      showToast('Cancel error: ' + e, 'error');
    }
  });

  function doReturnToSelection() {
    // Reset back to State 1
    selectedAction = null;
    selectedMethod = null;
    connectedDevice = null;
    document.querySelectorAll('.rotary-node').forEach(n => n.classList.remove('active'));
    document.querySelectorAll('.mirror-item').forEach(m => m.classList.remove('active'));
    document.getElementById('btnConfirmSelection').disabled = true;
    document.getElementById('transferCompleteBanner').classList.add('hidden');
    document.getElementById('btnReturnToSelection').classList.add('hidden');
    setSharingState(1);
  }

  btnReturn.addEventListener('click', doReturnToSelection);
  btnCompleteReturn.addEventListener('click', doReturnToSelection);

  btnClearLogs.addEventListener('click', () => {
    const panel = document.getElementById('dashLogPanel');
    if (panel) panel.innerHTML = '<div class="log-line text-dim">Logs cleared.</div>';
  });
}

// ========================================================
// 4. TELEMETRY POLLING & DIAL UPDATES
// ========================================================
async function pollAppTelemetry() {
  try {
    const data = await window.pywebview.api.get_dashboard_telemetry();
    if (!data) return;

    const hw = data.hardware || {};
    const transfer = data.transfer || {};
    const role = data.active_role || 'none';

    // Update HOME hardware cards
    const homeIp = document.getElementById('homeHwIp');
    const homeDisk = document.getElementById('homeHwDisk');
    const homeCpu = document.getElementById('homeHwCpu');
    const homeRam = document.getElementById('homeHwRam');

    if (homeIp) homeIp.textContent = hw.primary_ip || '127.0.0.1';
    if (homeDisk) homeDisk.textContent = `${hw.free_disk_gb || 0} GB Free`;
    if (homeCpu) homeCpu.textContent = `${hw.cpu_percent || 0}% (${hw.cpu_count || 1} Cores)`;
    if (homeRam) homeRam.textContent = `${hw.used_ram_gb || 0} GB / ${hw.total_ram_gb || 0} GB`;

    // Update Speed & Progress in HOME tab
    const homeSpeedVal = document.getElementById('homeSpeedVal');
    const homeSpeedStatus = document.getElementById('homeSpeedStatus');
    const homeProgressPct = document.getElementById('homeProgressPct');
    const homeProgressBar = document.getElementById('homeProgressBar');
    const homeProgressBytes = document.getElementById('homeProgressBytes');
    const homeActiveFile = document.getElementById('homeActiveFile');

    const liveSpeed = transfer.speed_mbps || 0;
    const totalBytes = transfer.total_bytes || 0;
    const transBytes = transfer.transferred_bytes || 0;
    const pct = totalBytes > 0 ? Math.min(100, Math.round((transBytes / totalBytes) * 100)) : 0;

    if (homeSpeedVal) homeSpeedVal.textContent = liveSpeed.toFixed(1);
    if (homeSpeedStatus) {
      if (role !== 'none') {
        homeSpeedStatus.textContent = `${role.toUpperCase()}: Streaming data · ETA: ${formatDuration(transfer.eta_seconds)}`;
      } else {
        homeSpeedStatus.textContent = 'Idle · No active wire activity';
      }
    }

    if (homeProgressPct) homeProgressPct.textContent = `${pct}%`;
    if (homeProgressBar) homeProgressBar.style.width = `${pct}%`;
    if (homeProgressBytes) homeProgressBytes.textContent = `${formatBytes(transBytes)} / ${formatBytes(totalBytes)}`;
    if (homeActiveFile) {
      homeActiveFile.textContent = transfer.current_file_name ? `File: ${transfer.current_file_name}` : 'File: Ready';
    }

    // Update Transfer Log in HOME tab & State 3 panel
    updateLogsView();

    // Update State 3 Gauges & Progress Bar
    if (currentSharingState === 3) {
      updateState3Dashboard(transfer, role, hw);
    }

    // Check for incoming receiver offer
    if (transfer.status === 'waiting_user' && transfer.pending_offer) {
      renderIncomingOffer(transfer.pending_offer);
    }

  } catch (err) {
    // console.warn('Telemetry error:', err);
  }
}

function updateState3Dashboard(transfer, role, hw) {
  const speedNum = document.getElementById('dashSpeedNum');
  const speedCircle = document.getElementById('dialSpeedCircle');
  const cpuNum = document.getElementById('dashCpuNum');
  const cpuCircle = document.getElementById('dialCpuCircle');
  const etaText = document.getElementById('dashEtaText');
  const roleBadge = document.getElementById('dashRoleBadge');
  const statusBadge = document.getElementById('dashStatusBadge');
  const integrityBadge = document.getElementById('dashIntegrityBadge');
  const progPct = document.getElementById('dashProgressPct');
  const progFill = document.getElementById('dashProgressFill');
  const fileName = document.getElementById('dashCurrentFileName');
  const byteText = document.getElementById('dashTransferredBytes');
  const completeBanner = document.getElementById('transferCompleteBanner');
  const btnReturn = document.getElementById('btnReturnToSelection');

  const speed = transfer.speed_mbps || 0;
  const cpu = hw.cpu_percent || 0;
  const total = transfer.total_bytes || 0;
  const transferred = transfer.transferred_bytes || 0;
  const pct = total > 0 ? Math.min(100, Math.round((transferred / total) * 100)) : 0;

  // Speed Dial Ring: max dial is 125 MB/s (Gigabit wire speed)
  // Circumference = 2 * PI * 68 = ~427
  const maxSpeed = 125;
  const speedRatio = Math.min(1, speed / maxSpeed);
  const speedOffset = 427 - (427 * speedRatio);
  if (speedNum) speedNum.textContent = speed.toFixed(1);
  if (speedCircle) speedCircle.style.strokeDashoffset = speedOffset;
  if (etaText) etaText.textContent = formatDuration(transfer.eta_seconds);

  // CPU Dial Ring: 0-100%
  const cpuRatio = Math.min(1, cpu / 100);
  const cpuOffset = 427 - (427 * cpuRatio);
  if (cpuNum) cpuNum.textContent = `${Math.round(cpu)}%`;
  if (cpuCircle) cpuCircle.style.strokeDashoffset = cpuOffset;

  // Badges
  if (roleBadge) roleBadge.textContent = role === 'receiver' ? 'RECEIVER' : 'SENDER';
  if (statusBadge) statusBadge.textContent = (transfer.status || 'STREAMING').toUpperCase();
  if (integrityBadge) integrityBadge.textContent = `${(transfer.hash_mode || 'CRC32').toUpperCase()} MODE`;

  // Progress Bar
  if (progPct) progPct.textContent = `${pct}%`;
  if (progFill) progFill.style.width = `${pct}%`;
  if (fileName) {
    fileName.textContent = transfer.current_file_name ? `File [${transfer.current_file_index || 1}/${transfer.total_files || 1}]: ${transfer.current_file_name}` : 'Ready';
  }
  if (byteText) byteText.textContent = `${formatBytes(transferred)} / ${formatBytes(total)}`;

  // Completion
  if (transfer.status === 'completed') {
    completeBanner.classList.remove('hidden');
    btnReturn.classList.remove('hidden');
    document.getElementById('completeTitle').textContent = 'Transfer Completed Successfully';
    document.getElementById('completeDesc').textContent = `Transferred ${transfer.total_files || 0} files (${formatBytes(total)}) with ${transfer.hash_mode || 'CRC32'} verification.`;
  } else if (transfer.status === 'error') {
    completeBanner.classList.remove('hidden');
    btnReturn.classList.remove('hidden');
    document.getElementById('completeTitle').textContent = 'Transfer Encountered Error';
    document.getElementById('completeDesc').textContent = transfer.error_message || 'Connection interrupted';
  }
}

async function updateLogsView() {
  try {
    const logs = await window.pywebview.api.get_transfer_logs();
    if (!logs || !Array.isArray(logs)) return;

    const homeFeed = document.getElementById('homeLogFeed');
    const dashFeed = document.getElementById('dashLogPanel');

    const logHtml = logs.map(l => `<div class="log-line">${l}</div>`).join('');

    if (homeFeed && homeFeed.children.length !== logs.length) {
      homeFeed.innerHTML = logHtml;
      homeFeed.scrollTop = homeFeed.scrollHeight;
    }

    if (dashFeed && dashFeed.children.length !== logs.length) {
      dashFeed.innerHTML = logHtml;
      dashFeed.scrollTop = dashFeed.scrollHeight;
    }
  } catch (e) {
    // Suppress log polling errors
  }
}

function renderIncomingOffer(offer) {
  const panel = document.getElementById('state2IncomingOfferBox');
  const banner = document.getElementById('offerNotification');

  if (offer) {
    document.getElementById('offerPeerName').textContent = offer.peer_name || 'Unknown';
    document.getElementById('offerPeerIp').textContent = offer.peer_ip || '127.0.0.1';
    document.getElementById('offerFilesCount').textContent = offer.total_files || 0;
    document.getElementById('offerTotalSize').textContent = formatBytes(offer.total_bytes || 0);

    // If currently on State 2 and Action is Receive, show prompt box
    if (currentSharingState === 2 && selectedAction === 'RECEIVE') {
      panel.classList.remove('hidden');
    } else {
      // Show top floating notification banner across other pages
      banner.classList.remove('hidden');
      document.getElementById('offerTitle').textContent = `Transfer Offer from ${offer.peer_name}`;
      document.getElementById('offerSubtitle').textContent = `${offer.total_files} files (${formatBytes(offer.total_bytes)})`;
    }
  } else {
    panel.classList.add('hidden');
    banner.classList.add('hidden');
  }
}

// ========================================================
// 5. FILE SERVER TAB
// ========================================================
function setupFileServerTab() {
  const btnToggle = document.getElementById('btnToggleServer');
  const btnOpenBrowser = document.getElementById('btnOpenServerBrowser');
  const btnCopy = document.getElementById('btnCopyServerUrl');
  const btnChangeShared = document.getElementById('btnChangeSharedFolder');
  const btnChangeUploads = document.getElementById('btnChangeUploadsFolder');
  const chkUploads = document.getElementById('chkServerAllowUploads');

  btnToggle.addEventListener('click', async () => {
    const isRunning = btnToggle.textContent.includes('STOP');
    try {
      const res = await window.pywebview.api.toggle_web_portal(!isRunning);
      if (res && res.success) {
        refreshFileServerInfo();
        showToast(isRunning ? 'Server stopped' : 'Server started', 'info');
      }
    } catch (e) {
      showToast('Server toggle error: ' + e, 'error');
    }
  });

  btnCopy.addEventListener('click', () => {
    const url = document.getElementById('serverUrlText').textContent;
    navigator.clipboard.writeText(url).then(() => {
      showToast('Server URL copied to clipboard', 'success');
    });
  });

  btnOpenBrowser.addEventListener('click', () => {
    const url = document.getElementById('serverUrlText').textContent;
    window.open(url, '_blank');
  });

  btnChangeShared.addEventListener('click', async () => {
    try {
      const res = await window.pywebview.api.select_portal_shared_folder();
      if (res && res.success) {
        document.getElementById('serverSharedFolderInput').value = res.folder;
        showToast('Shared folder updated', 'success');
      }
    } catch (e) {
      showToast('Error selecting folder: ' + e, 'error');
    }
  });

  btnChangeUploads.addEventListener('click', async () => {
    try {
      const res = await window.pywebview.api.select_portal_uploads_folder();
      if (res && res.success) {
        document.getElementById('serverUploadsFolderInput').value = res.folder;
        showToast('Uploads destination updated', 'success');
      }
    } catch (e) {
      showToast('Error selecting folder: ' + e, 'error');
    }
  });

  chkUploads.addEventListener('change', async (e) => {
    try {
      await window.pywebview.api.set_portal_allow_uploads(e.target.checked);
      showToast(e.target.checked ? 'Guest uploads enabled' : 'Guest uploads disabled', 'info');
    } catch (err) {
      showToast('Error changing upload setting: ' + err, 'error');
    }
  });
}

async function refreshFileServerInfo() {
  try {
    const status = await window.pywebview.api.get_web_portal_status();
    if (!status) return;

    const badge = document.getElementById('serverStatusBadge');
    const btnToggle = document.getElementById('btnToggleServer');
    const urlText = document.getElementById('serverUrlText');
    const ipPortText = document.getElementById('serverIpPortText');
    const sharedInput = document.getElementById('serverSharedFolderInput');
    const uploadsInput = document.getElementById('serverUploadsFolderInput');
    const qrContainer = document.getElementById('serverQrContainer');

    const running = status.running;
    badge.textContent = running ? 'RUNNING' : 'STOPPED';
    badge.className = `portal-status-badge ${running ? 'active' : ''}`;
    btnToggle.textContent = running ? 'STOP SERVER' : 'START SERVER';
    btnToggle.className = running ? 'btn-danger' : 'btn-primary';

    urlText.textContent = status.portal_url || `http://127.0.0.1:${status.port}/portal`;
    ipPortText.textContent = `${status.ip} : ${status.port}`;
    sharedInput.value = status.shared_folder || '';
    uploadsInput.value = status.uploads_folder || '';

    // Load QR SVG
    const qrSvg = await window.pywebview.api.get_portal_qr_svg();
    if (qrContainer && qrSvg) {
      qrContainer.innerHTML = qrSvg;
    }
  } catch (e) {
    console.error('File Server refresh error:', e);
  }
}

// ========================================================
// 6. VERIFY TAB (Dedicated Pairwise File Verification)
// ========================================================
function setupVerifyTab() {
  const btnPickOrig = document.getElementById('btnPickOriginalFile');
  const btnPickRecv = document.getElementById('btnPickReceivedFile');
  const btnVerify = document.getElementById('btnDoVerifyFiles');
  const inputOrig = document.getElementById('verifyOriginalPath');
  const inputRecv = document.getElementById('verifyReceivedPath');
  const origSizeTag = document.getElementById('verifyOriginalSize');
  const recvSizeTag = document.getElementById('verifyReceivedSize');
  const resultCard = document.getElementById('verifyResultCard');

  btnPickOrig.addEventListener('click', async () => {
    try {
      const res = await window.pywebview.api.select_file_for_verify('Select Original File');
      if (res && res.success) {
        inputOrig.value = res.path;
        origSizeTag.textContent = `${res.name} (${formatBytes(res.size)})`;
      }
    } catch (e) {
      showToast('Error selecting file: ' + e, 'error');
    }
  });

  btnPickRecv.addEventListener('click', async () => {
    try {
      const res = await window.pywebview.api.select_file_for_verify('Select Received File');
      if (res && res.success) {
        inputRecv.value = res.path;
        recvSizeTag.textContent = `${res.name} (${formatBytes(res.size)})`;
      }
    } catch (e) {
      showToast('Error selecting file: ' + e, 'error');
    }
  });

  btnVerify.addEventListener('click', async () => {
    const origPath = inputOrig.value.trim();
    const recvPath = inputRecv.value.trim();

    if (!origPath || !recvPath) {
      showToast('Please select both the Original File and Received File', 'error');
      return;
    }

    btnVerify.disabled = true;
    btnVerify.textContent = 'Calculating SHA-256...';
    resultCard.classList.add('hidden');

    try {
      const res = await window.pywebview.api.verify_two_files(origPath, recvPath);
      btnVerify.disabled = false;
      btnVerify.textContent = '[ VERIFY ]';

      if (!res || !res.success) {
        showToast(res.error || 'Verification failed', 'error');
        return;
      }

      resultCard.classList.remove('hidden');
      const badge = document.getElementById('verifyResultBadge');
      const origHashEl = document.getElementById('verifyOriginalHash');
      const recvHashEl = document.getElementById('verifyReceivedHash');
      const durationEl = document.getElementById('verifyDurationText');
      const verdictEl = document.getElementById('verifyParityVerdict');

      origHashEl.textContent = res.original_hash || '--';
      recvHashEl.textContent = res.received_hash || '--';
      durationEl.textContent = `Time Elapsed: ${res.duration_sec}s · Size: ${formatBytes(res.original_size)}`;

      if (res.match) {
        badge.textContent = 'RESULT: MATCH';
        badge.className = 'result-badge match';
        verdictEl.textContent = 'Bit-for-bit cryptographic parity confirmed. Both hashes match identically.';
      } else {
        badge.textContent = 'RESULT: MISMATCH';
        badge.className = 'result-badge mismatch';
        verdictEl.textContent = 'Cryptographic mismatch detected! The received file differs from the original source.';
      }

      showToast(`Verification completed: ${res.match ? 'MATCH' : 'MISMATCH'}`, res.match ? 'success' : 'error');
    } catch (e) {
      btnVerify.disabled = false;
      btnVerify.textContent = '[ VERIFY ]';
      showToast('Verification error: ' + e, 'error');
    }
  });

  const btnRefreshPast = document.getElementById('btnRefreshPastSessions');
  if (btnRefreshPast) {
    btnRefreshPast.addEventListener('click', loadPastAuditSessions);
  }
}

async function loadPastAuditSessions() {
  const tbody = document.getElementById('verifySessionsTableBody');
  if (!tbody) return;

  try {
    const history = await window.pywebview.api.get_history();
    if (!history || history.length === 0) {
      tbody.innerHTML = '<tr><td colspan="8" class="loading-td">No transfer sessions recorded yet.</td></tr>';
      return;
    }

    tbody.innerHTML = '';
    history.forEach(item => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><code>#${item.session_id}</code></td>
        <td><span class="role-badge">${(item.role || 'sender').toUpperCase()}</span></td>
        <td>${item.peer_name || 'Peer'}</td>
        <td>${item.total_files || 1}</td>
        <td>${formatBytes(item.total_bytes || 0)}</td>
        <td>${(item.hash_mode || 'crc32').toUpperCase()}</td>
        <td><span class="status-badge-active">${(item.status || 'OK').toUpperCase()}</span></td>
        <td>
          <button class="btn-secondary btn-sm btn-audit-session" data-session="${item.session_id}">
            Audit SHA-256
          </button>
        </td>
      `;
      tbody.appendChild(tr);
    });

    tbody.querySelectorAll('.btn-audit-session').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const sId = e.target.getAttribute('data-session');
        try {
          const res = await window.pywebview.api.start_verification(sId, 'full_crypto');
          if (res && res.success) {
            showToast(`Cryptographic audit started for Session #${sId}`, 'success');
          } else {
            showToast(res.error || 'Could not start audit', 'error');
          }
        } catch (err) {
          showToast('Audit error: ' + err, 'error');
        }
      });
    });
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="8" class="loading-td text-danger">Error loading history: ${e}</td></tr>`;
  }
}

// ========================================================
// 7. SETTINGS TAB
// ========================================================
function setupSettingsTab() {
  loadSettings();

  const btnSave = document.getElementById('btnSaveSettings');
  const rngRam = document.getElementById('rngRamBuffer');
  const lblRam = document.getElementById('lblRamBuffer');
  const rngBandwidth = document.getElementById('rngBandwidth');
  const lblBandwidth = document.getElementById('lblBandwidth');

  if (rngRam && lblRam) {
    rngRam.addEventListener('input', () => {
      lblRam.textContent = `${rngRam.value} MB`;
    });
  }

  if (rngBandwidth && lblBandwidth) {
    rngBandwidth.addEventListener('input', () => {
      const val = parseInt(rngBandwidth.value, 10);
      lblBandwidth.textContent = val === 0 ? 'Uncapped (Max Wire Speed)' : `${val} MB/s`;
    });
  }

  if (btnSave) {
    btnSave.addEventListener('click', async () => {
      const cfg = {
        use_full_resources: document.getElementById('chkFullResources').checked,
        default_hash_mode: document.getElementById('cfgDefaultHashMode').value,
        ram_buffer_mb: parseInt(rngRam.value, 10),
        bandwidth_limit_mbps: parseInt(rngBandwidth.value, 10)
      };
      try {
        await window.pywebview.api.save_settings(cfg);
        showToast('Application settings saved', 'success');
      } catch (e) {
        showToast('Error saving settings: ' + e, 'error');
      }
    });
  }

  // Network Auto-Setup & Revert
  const btnSetupEth = document.getElementById('btnSetupEthernet');
  const btnRevertEth = document.getElementById('btnRevertEthernet');

  if (btnSetupEth) {
    btnSetupEth.addEventListener('click', async () => {
      try {
        const res = await window.pywebview.api.configure_ethernet('');
        if (res.requires_sudo) {
          openAuthModal();
        } else if (res.success) {
          showToast('Direct cable interface configured (192.168.123.x)', 'success');
          document.getElementById('netSetupStatus').textContent = 'Direct Cable IP: 192.168.123.x active.';
        } else {
          showToast(res.error || 'Setup failed', 'error');
        }
      } catch (e) {
        showToast('Setup error: ' + e, 'error');
      }
    });
  }

  if (btnRevertEth) {
    btnRevertEth.addEventListener('click', async () => {
      try {
        await window.pywebview.api.revert_ethernet();
        showToast('Network settings reverted to DHCP/Link-Local', 'info');
        document.getElementById('netSetupStatus').textContent = 'Network settings reverted to normal state.';
      } catch (e) {
        showToast('Revert error: ' + e, 'error');
      }
    });
  }

  // Destination Settings Buttons
  const btnPickDest = document.getElementById('btnSettingsPickDest');
  const btnSaveDest = document.getElementById('btnSettingsSaveDest');
  const inputDest = document.getElementById('settingsDestInput');

  if (btnPickDest) {
    btnPickDest.addEventListener('click', async () => {
      try {
        const res = await window.pywebview.api.select_destination_folder();
        if (res && res.path) inputDest.value = res.path;
      } catch (e) {
        showToast('Error selecting destination: ' + e, 'error');
      }
    });
  }

  if (btnSaveDest) {
    btnSaveDest.addEventListener('click', async () => {
      const p = inputDest.value.trim();
      if (!p) return;
      try {
        const res = await window.pywebview.api.save_default_destination(p);
        if (res && res.success) {
          showToast('Default destination updated', 'success');
          loadHomeDefaultDestination();
        }
      } catch (e) {
        showToast('Error saving destination: ' + e, 'error');
      }
    });
  }
}

async function loadSettings() {
  try {
    const s = await window.pywebview.api.get_settings();
    if (!s) return;

    if (document.getElementById('chkFullResources')) {
      document.getElementById('chkFullResources').checked = Boolean(s.use_full_resources);
    }
    if (document.getElementById('cfgDefaultHashMode')) {
      document.getElementById('cfgDefaultHashMode').value = s.default_hash_mode || 'crc32';
    }
    if (document.getElementById('rngRamBuffer')) {
      document.getElementById('rngRamBuffer').value = s.ram_buffer_mb || 512;
      document.getElementById('lblRamBuffer').textContent = `${s.ram_buffer_mb || 512} MB`;
    }
    if (document.getElementById('rngBandwidth')) {
      const bw = s.bandwidth_limit_mbps || 0;
      document.getElementById('rngBandwidth').value = bw;
      document.getElementById('lblBandwidth').textContent = bw === 0 ? 'Uncapped (Max Wire Speed)' : `${bw} MB/s`;
    }

    const platform = await window.pywebview.api.get_system_platform();
    const platEl = document.getElementById('settingsPlatformText');
    if (platEl && platform) {
      platEl.textContent = `${platform} (Python 3 Engine)`;
    }
  } catch (e) {
    console.error('Failed to load settings:', e);
  }
}

// ========================================================
// 8. SUDO PASSWORD MODAL
// ========================================================
function openAuthModal() {
  const modal = document.getElementById('authModal');
  const input = document.getElementById('authPasswordInput');
  const err = document.getElementById('authErrorMsg');
  const btnCancel = document.getElementById('btnCancelAuth');
  const btnConfirm = document.getElementById('btnConfirmAuth');

  modal.classList.remove('hidden');
  input.value = '';
  err.classList.add('hidden');
  input.focus();

  btnCancel.onclick = () => modal.classList.add('hidden');

  btnConfirm.onclick = async () => {
    const pwd = input.value;
    try {
      const res = await window.pywebview.api.configure_ethernet(pwd);
      if (res && res.success) {
        modal.classList.add('hidden');
        showToast('Ethernet adapter configured with direct IP (192.168.123.x)', 'success');
      } else {
        err.textContent = res.error || 'Authentication failed';
        err.classList.remove('hidden');
      }
    } catch (e) {
      err.textContent = String(e);
      err.classList.remove('hidden');
    }
  };
}
