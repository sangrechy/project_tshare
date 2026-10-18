/**
 * T-Share v3 Frontend Application Logic
 * High-speed direct Ethernet file transfer interface.
 * Strictly real metrics, zero mock data.
 */

// Application State
let activeTab = 'home';
let selectedTargetIp = '';
let selectedTargetPort = 52001;
let selectedVerifySessionId = null;
let currentPendingOffer = null;
let pollTimer = null;

// DOM Elements Initialization
document.addEventListener('DOMContentLoaded', () => {
  setupTabNavigation();
  setupSendControls();
  setupReceiveControls();
  setupVerifyControls();
  setupSettingsControls();
  setupEmergencyControls();

  // Listen for manual IP changes to update target status in real time
  const manualIp = document.getElementById('manualIpInput');
  const manualPort = document.getElementById('manualPortInput');
  if (manualIp) manualIp.addEventListener('input', updateTargetReceiverStatus);
  if (manualPort) manualPort.addEventListener('input', updateTargetReceiverStatus);

  // Initialize immediately if pywebview is already present
  if (window.pywebview && window.pywebview.api) {
    initApp();
  } else {
    window.addEventListener('pywebviewready', () => {
      initApp();
    });
  }
});

function initApp() {
  loadNetworkPill();
  loadSettings();
  loadHistory();

  // Start 250ms throttled telemetry polling loop
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

  // Update nav buttons
  document.querySelectorAll('.nav-tab').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-tab') === tabName);
  });

  // Update panels
  document.querySelectorAll('.tab-panel').forEach(p => {
    p.classList.toggle('active', p.id === `tab-${tabName}`);
  });

  // Tab-specific refreshes
  if (tabName === 'history') {
    loadHistory();
  } else if (tabName === 'verify') {
    loadVerifyLedgers();
  } else if (tabName === 'receive') {
    loadNetworkPill();
  } else if (tabName === 'send') {
    updateTargetReceiverStatus();
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

    // 1. Update Hardware Overview Cards
    if (hw) {
      if (hw.network && hw.network.primary_ip) {
        document.getElementById('telemetryIp').textContent = hw.network.primary_ip;
        const senderIpEl = document.getElementById('senderNodeIp');
        if (senderIpEl) senderIpEl.textContent = `Local IP: ${hw.network.primary_ip}`;
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

    // 2. Check for Incoming Offer on Receiver
    if (transfer && transfer.pending_offer) {
      showIncomingOffer(transfer.pending_offer);
    } else {
      hideIncomingOffer();
    }

    // 3. Handle Active Transfer Screen vs Idle Screen
    const isTransferActive = (role !== 'none') && (transfer.status === 'streaming' || transfer.status === 'receiving' || transfer.status === 'connecting');

    if (isTransferActive) {
      // Auto-redirect to home tab on first detection of active transfer
      if (activeTab !== 'home' && !window._redirectedForTransfer) {
        switchTab('home');
        window._redirectedForTransfer = true;
      }

      document.getElementById('homeActiveTransfer').classList.remove('hidden');
      document.getElementById('homeHardwareView').classList.add('hidden');

      // Update Transfer Dashboard
      document.getElementById('transferRoleBadge').textContent = (role === 'sender') ? 'TRANSMITTING (SENDER)' : 'RECEIVING (RECEIVER)';
      document.getElementById('liveSpeedNumber').textContent = transfer.speed_mbps ? transfer.speed_mbps.toFixed(1) : '0.0';
      document.getElementById('livePeerText').textContent = `${transfer.peer_name || 'Peer'} (${transfer.peer_ip || ''})`;

      // ETA
      if (transfer.eta_seconds && transfer.eta_seconds > 0) {
        const mins = Math.floor(transfer.eta_seconds / 60);
        const secs = transfer.eta_seconds % 60;
        document.getElementById('liveEtaText').textContent = `${mins}m ${secs}s`;
      } else {
        document.getElementById('liveEtaText').textContent = '--:--';
      }

      // Transferred Data
      const transGB = (transfer.transferred_bytes / (1024 ** 3)).toFixed(2);
      const totalGB = (transfer.total_bytes / (1024 ** 3)).toFixed(2);
      document.getElementById('liveTransferredText').textContent = `${transGB} GB / ${totalGB} GB`;

      // Progress bar
      const pct = transfer.total_bytes > 0 ? Math.min(100, Math.round((transfer.transferred_bytes / transfer.total_bytes) * 100)) : 0;
      document.getElementById('liveOverallPct').textContent = `${pct}%`;
      document.getElementById('liveOverallBar').style.width = `${pct}%`;

      document.getElementById('liveActiveFileTitle').textContent = `File [${transfer.current_file_index || 1}/${transfer.total_files || 1}]: ${transfer.current_file_name || 'Streaming...'}`;
      document.getElementById('liveStatusSubtext').textContent = (role === 'sender') ? (transfer.receiver_status || 'Streaming blocks...') : 'Verifying 4 MB chunks...';

    } else {
      window._redirectedForTransfer = false;
      document.getElementById('homeActiveTransfer').classList.add('hidden');
      document.getElementById('homeHardwareView').classList.remove('hidden');
    }

    // 4. Update Send Tab Honest Connection Status Nodes
    const sDot = document.getElementById('senderStatusDot');
    const sText = document.getElementById('senderStatusText');
    const rDot = document.getElementById('receiverStatusDot');
    const rText = document.getElementById('receiverStatusText');
    const rSub = document.getElementById('receiverNodeTarget');

    if (sDot && sText && rDot && rText && rSub) {
      if (role === 'sender' && isTransferActive) {
        sDot.className = 'status-indicator-dot dot-connected';
        sText.textContent = `Streaming (${transfer.status})`;

        rDot.className = 'status-indicator-dot dot-connected';
        rText.textContent = `Connected (${transfer.peer_name || 'Receiver'})`;
        rSub.textContent = `Wire transfer active · ${transfer.speed_mbps.toFixed(1)} MB/s`;
      } else if (role === 'sender' && transfer.status === 'completed') {
        sDot.className = 'status-indicator-dot dot-idle';
        sText.textContent = 'Idle (Transfer Finished)';

        rDot.className = 'status-indicator-dot dot-connected';
        rText.textContent = 'Completed';
        rSub.textContent = 'Transfer completed successfully';
      } else if (role === 'sender' && transfer.status === 'rejected') {
        sDot.className = 'status-indicator-dot dot-idle';
        sText.textContent = 'Ready (Offer Declined)';

        rDot.className = 'status-indicator-dot dot-disconnected';
        rText.textContent = 'Declined';
        rSub.textContent = transfer.receiver_status || 'Peer declined transfer';
      } else {
        updateTargetReceiverStatus();
      }
    }

    // Refresh Send Tab Discovery list if on send tab
    if (activeTab === 'send') {
      refreshDiscoveredPeers();
    }

  } catch (err) {
    console.error("Telemetry error:", err);
  }
}

function updateTargetReceiverStatus() {
  const manualIp = document.getElementById('manualIpInput');
  const manualPort = document.getElementById('manualPortInput');
  const targetIp = (manualIp ? manualIp.value.trim() : '') || selectedTargetIp;
  const targetPort = (manualPort ? manualPort.value.trim() : '') || selectedTargetPort;

  const sDot = document.getElementById('senderStatusDot');
  const sText = document.getElementById('senderStatusText');
  const rDot = document.getElementById('receiverStatusDot');
  const rText = document.getElementById('receiverStatusText');
  const rSub = document.getElementById('receiverNodeTarget');

  if (sDot && sText) {
    sDot.className = 'status-indicator-dot dot-idle';
    sText.textContent = 'Idle (Ready)';
  }

  if (rDot && rText && rSub) {
    if (targetIp) {
      rDot.className = 'status-indicator-dot dot-disconnected';
      rText.textContent = 'Not Connected';
      rSub.textContent = `Target: ${targetIp}:${targetPort} (Ready to connect)`;
    } else {
      rDot.className = 'status-indicator-dot dot-disconnected';
      rText.textContent = 'Disconnected';
      rSub.textContent = 'No target peer selected';
    }
  }
}

// ----------------- SEND TAB CONTROLS -----------------

function setupSendControls() {
  document.getElementById('btnSelectFiles').addEventListener('click', async () => {
    if (!window.pywebview) return;
    const res = await window.pywebview.api.select_source_files();
    updateSourceSelectionUI(res);
  });

  document.getElementById('btnSelectFolder').addEventListener('click', async () => {
    if (!window.pywebview) return;
    const res = await window.pywebview.api.select_source_folder();
    updateSourceSelectionUI(res);
  });

  document.getElementById('btnStartTransfer').addEventListener('click', async () => {
    const ip = document.getElementById('manualIpInput').value.trim() || selectedTargetIp;
    const port = parseInt(document.getElementById('manualPortInput').value) || selectedTargetPort;

    if (!ip) {
      alert("Please enter receiver IP or select a discovered peer.");
      return;
    }

    const rText = document.getElementById('receiverStatusText');
    const rSub = document.getElementById('receiverNodeTarget');
    if (rText) rText.textContent = 'Connecting...';
    if (rSub) rSub.textContent = `Opening TCP socket to ${ip}:${port}...`;

    const res = await window.pywebview.api.start_transfer(ip, port);
    if (res && res.success) {
      switchTab('home');
    } else {
      if (rText) rText.textContent = 'Connection Failed';
      if (rSub) rSub.textContent = res.error || 'Connection refused';
      alert(`Transfer failed to start: ${res.error || 'Unknown error'}`);
    }
  });
}

function updateSourceSelectionUI(summary) {
  if (!summary) return;
  document.getElementById('selectedFileCount').textContent = summary.count || 0;

  if (summary.total_bytes >= 1024 ** 3) {
    document.getElementById('selectedTotalSize').textContent = `${(summary.total_bytes / (1024 ** 3)).toFixed(2)} GB`;
  } else {
    document.getElementById('selectedTotalSize').textContent = `${summary.total_mb || 0} MB`;
  }

  const list = document.getElementById('selectedPathsList');
  list.innerHTML = '';
  if (summary.paths && summary.paths.length > 0) {
    summary.paths.forEach(p => {
      const item = document.createElement('div');
      item.textContent = p;
      list.appendChild(item);
    });
    document.getElementById('btnStartTransfer').disabled = false;
  } else {
    list.innerHTML = '<span class="empty-path-msg">No files selected.</span>';
    document.getElementById('btnStartTransfer').disabled = true;
  }
}

async function refreshDiscoveredPeers() {
  if (!window.pywebview) return;
  try {
    const peers = await window.pywebview.api.get_discovered_peers();
    const list = document.getElementById('peerList');
    list.innerHTML = '';

    if (!peers || peers.length === 0) {
      list.innerHTML = '<div class="empty-peers">Looking for peers on direct Ethernet cable...</div>';
      return;
    }

    peers.forEach(peer => {
      const div = document.createElement('div');
      div.className = 'peer-item';
      if (peer.ip === selectedTargetIp) div.classList.add('selected');

      div.innerHTML = `
        <div>
          <div class="peer-name">${peer.name}</div>
          <div class="peer-ip">${peer.ip}:${peer.port} ${peer.is_direct_ethernet ? '· Direct Wire' : ''}</div>
        </div>
        <button class="btn-primary btn-sm">Select</button>
      `;

      div.addEventListener('click', () => {
        selectedTargetIp = peer.ip;
        selectedTargetPort = peer.port;
        document.getElementById('manualIpInput').value = peer.ip;
        document.getElementById('manualPortInput').value = peer.port;
        updateTargetReceiverStatus();
        refreshDiscoveredPeers();
      });

      list.appendChild(div);
    });
  } catch (err) {
    console.error(err);
  }
}

// ----------------- RECEIVE TAB CONTROLS -----------------

function setupReceiveControls() {
  document.getElementById('btnBrowseDestination').addEventListener('click', async () => {
    if (!window.pywebview) return;
    const res = await window.pywebview.api.select_destination_folder();
    if (res && res.path) {
      document.getElementById('destinationPathInput').value = res.path;
    }
  });

  document.getElementById('btnCopyAddress').addEventListener('click', () => {
    const text = document.getElementById('receiverAddressPill').textContent;
    navigator.clipboard.writeText(text);
    alert(`Copied direct address: ${text}`);
  });

  document.getElementById('btnAcceptReceive').addEventListener('click', acceptCurrentOffer);
  document.getElementById('btnBannerAccept').addEventListener('click', () => {
    switchTab('receive');
  });

  document.getElementById('btnRejectReceive').addEventListener('click', rejectCurrentOffer);
  document.getElementById('btnBannerDecline').addEventListener('click', rejectCurrentOffer);
}

async function loadNetworkPill() {
  if (!window.pywebview) return;
  try {
    const info = await window.pywebview.api.get_my_network_info();
    if (info) {
      document.getElementById('receiverAddressPill').textContent = info.display_address;
    }
  } catch (err) {
    console.error(err);
  }
}

function showIncomingOffer(offer) {
  currentPendingOffer = offer;
  const banner = document.getElementById('offerNotification');
  const sizeGB = (offer.total_bytes / (1024 ** 3)).toFixed(2);

  document.getElementById('offerTitle').textContent = `Incoming: ${offer.root_name || 'File Transfer'}`;
  document.getElementById('offerSubtitle').textContent = `From ${offer.peer_name} (${offer.peer_ip}) · ${offer.total_files} files (${sizeGB} GB)`;
  banner.classList.remove('hidden');

  // Receive Tab Card
  document.getElementById('receiveOfferHeading').textContent = `${offer.root_name || 'Batch'} (${sizeGB} GB)`;
  document.getElementById('receiveOfferDesc').textContent = `Sender: ${offer.peer_name} · Total files: ${offer.total_files}`;
  document.getElementById('receiveDecisionButtons').classList.remove('hidden');
}

function hideIncomingOffer() {
  currentPendingOffer = null;
  document.getElementById('offerNotification').classList.add('hidden');
  document.getElementById('receiveOfferHeading').textContent = "Listening for Sender...";
  document.getElementById('receiveOfferDesc').textContent = "When a sender connects, transfer details will appear here for your approval.";
  document.getElementById('receiveDecisionButtons').classList.add('hidden');
}

async function acceptCurrentOffer() {
  let dest = document.getElementById('destinationPathInput').value.trim();
  if (!dest) {
    const res = await window.pywebview.api.select_destination_folder();
    if (!res || !res.path) {
      alert("Please select a destination folder to receive files.");
      return;
    }
    dest = res.path;
    document.getElementById('destinationPathInput').value = dest;
  }

  const policy = document.querySelector('input[name="collisionPolicy"]:checked').value;
  await window.pywebview.api.accept_transfer(dest, policy);
  hideIncomingOffer();
  switchTab('home');
}

async function rejectCurrentOffer() {
  await window.pywebview.api.reject_transfer("User declined");
  hideIncomingOffer();
}

// ----------------- VERIFY TAB CONTROLS -----------------

function setupVerifyControls() {
  document.getElementById('btnRunVerification').addEventListener('click', async () => {
    if (!selectedVerifySessionId) {
      alert("Select a session from the history ledgers first.");
      return;
    }

    const mode = document.getElementById('verifyModeSelect').value;
    document.getElementById('verifyLiveProgress').classList.remove('hidden');
    document.getElementById('btnRunVerification').disabled = true;

    await window.pywebview.api.start_verification(selectedVerifySessionId, mode);

    // Poll verification progress
    const verifyPoll = setInterval(async () => {
      const v = await window.pywebview.api.get_verify_telemetry();
      if (!v) return;

      const pct = v.total_bytes > 0 ? Math.min(100, Math.round((v.bytes_checked / v.total_bytes) * 100)) : 0;
      document.getElementById('verifyProgressBar').style.width = `${pct}%`;
      document.getElementById('verifySpeedText').textContent = `${v.read_speed_mbps} MB/s`;
      document.getElementById('verifyCurrentFileText').textContent = `Reading: ${v.current_file || 'Scanning...'}`;
      document.getElementById('verifyDetailsText').textContent = v.details || `Verifying ${pct}%...`;

      if (v.status !== 'auditing') {
        clearInterval(verifyPoll);
        document.getElementById('btnRunVerification').disabled = false;
        alert(`Verification Result: ${v.status.toUpperCase()}\n${v.details}`);
      }
    }, 300);
  });
}

async function loadVerifyLedgers() {
  if (!window.pywebview) return;
  try {
    const ledger = await window.pywebview.api.get_verify_ledger();

    // Sender Ledger
    const sList = document.getElementById('senderLedgerList');
    sList.innerHTML = '';
    if (ledger.sender_sessions && ledger.sender_sessions.length > 0) {
      ledger.sender_sessions.forEach(s => {
        const item = createLedgerItem(s);
        sList.appendChild(item);
      });
    } else {
      sList.innerHTML = '<div class="empty-ledger">No sender records.</div>';
    }

    // Receiver Ledger
    const rList = document.getElementById('receiverLedgerList');
    rList.innerHTML = '';
    if (ledger.receiver_sessions && ledger.receiver_sessions.length > 0) {
      ledger.receiver_sessions.forEach(s => {
        const item = createLedgerItem(s);
        rList.appendChild(item);
      });
    } else {
      rList.innerHTML = '<div class="empty-ledger">No receiver records.</div>';
    }
  } catch (err) {
    console.error(err);
  }
}

function createLedgerItem(session) {
  const div = document.createElement('div');
  div.className = 'ledger-item';
  const sizeGB = (session.total_bytes / (1024 ** 3)).toFixed(2);

  div.innerHTML = `
    <div>
      <div class="ledger-id">Session #${session.session_id} (${session.status})</div>
      <div class="ledger-meta">${session.created_at} · ${session.total_files} files · ${sizeGB} GB</div>
    </div>
    <button class="btn-secondary btn-sm">Select</button>
  `;

  div.addEventListener('click', () => {
    document.querySelectorAll('.ledger-item').forEach(el => el.classList.remove('selected'));
    div.classList.add('selected');
    selectedVerifySessionId = session.session_id;
    document.getElementById('btnRunVerification').disabled = false;
  });

  return div;
}

// ----------------- HISTORY TAB -----------------

async function loadHistory() {
  if (!window.pywebview) return;
  try {
    const list = await window.pywebview.api.get_history();
    const tbody = document.getElementById('historyTableBody');
    tbody.innerHTML = '';

    document.getElementById('historySessionCount').textContent = `${list.length} Transfers`;

    if (!list || list.length === 0) {
      tbody.innerHTML = '<tr><td colspan="9" class="empty-table-cell">No transfer records found.</td></tr>';
      return;
    }

    list.forEach(row => {
      const tr = document.createElement('tr');
      const sizeGB = (row.total_bytes / (1024 ** 3)).toFixed(2);
      const badgeClass = `badge-${row.status.toLowerCase()}`;

      tr.innerHTML = `
        <td><strong>#${row.session_id}</strong></td>
        <td><span class="badge-status">${row.role.toUpperCase()}</span></td>
        <td>${row.peer_name || 'Peer'}</td>
        <td>${row.total_files}</td>
        <td>${sizeGB} GB</td>
        <td>${row.avg_speed_mbps} MB/s</td>
        <td>${row.duration_sec}s</td>
        <td><span class="badge-status ${badgeClass}">${row.status}</span></td>
        <td>
          <button class="btn-secondary btn-sm btn-open-folder">Open</button>
        </td>
      `;

      tr.querySelector('.btn-open-folder').addEventListener('click', () => {
        if (row.local_path) {
          window.pywebview.api.open_folder(row.local_path);
        } else {
          alert("Path not available for this record.");
        }
      });

      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error(err);
  }
}

// ----------------- SETTINGS TAB -----------------

function setupSettingsControls() {
  const ramSlider = document.getElementById('sliderRamBuffer');
  const cpuSlider = document.getElementById('sliderCpuDuty');
  const threadSlider = document.getElementById('sliderWorkerThreads');
  const netSlider = document.getElementById('sliderBandwidthLimit');
  const fullToggle = document.getElementById('toggleFullResources');

  ramSlider.addEventListener('input', () => {
    document.getElementById('valRamBuffer').textContent = `${ramSlider.value} MB`;
  });

  cpuSlider.addEventListener('input', () => {
    document.getElementById('valCpuDuty').textContent = `${cpuSlider.value}%`;
  });

  threadSlider.addEventListener('input', () => {
    document.getElementById('valWorkerThreads').textContent = `${threadSlider.value} Threads`;
  });

  netSlider.addEventListener('input', () => {
    const val = parseInt(netSlider.value);
    document.getElementById('valBandwidthLimit').textContent = val === 0 ? "Uncapped (Max Wire Speed)" : `${val} MB/s`;
  });

  fullToggle.addEventListener('change', () => {
    if (fullToggle.checked) {
      ramSlider.value = 1024;
      cpuSlider.value = 100;
      threadSlider.value = 8;
      netSlider.value = 0;
      document.getElementById('valRamBuffer').textContent = "1024 MB";
      document.getElementById('valCpuDuty').textContent = "100%";
      document.getElementById('valWorkerThreads').textContent = "8 Threads";
      document.getElementById('valBandwidthLimit').textContent = "Uncapped (Max Wire Speed)";
    }
  });

  document.getElementById('btnSaveSettings').addEventListener('click', async () => {
    const newSettings = {
      use_full_resources: fullToggle.checked,
      ram_buffer_mb: parseInt(ramSlider.value),
      cpu_duty_percent: parseInt(cpuSlider.value),
      worker_threads: parseInt(threadSlider.value),
      bandwidth_limit_mbps: parseInt(netSlider.value)
    };

    if (window.pywebview) {
      await window.pywebview.api.save_settings(newSettings);
      alert("Settings applied successfully!");
    }
  });
}

async function loadSettings() {
  if (!window.pywebview) return;
  try {
    const s = await window.pywebview.api.get_settings();
    if (!s) return;

    document.getElementById('toggleFullResources').checked = s.use_full_resources;
    document.getElementById('sliderRamBuffer').value = s.ram_buffer_mb;
    document.getElementById('valRamBuffer').textContent = `${s.ram_buffer_mb} MB`;

    document.getElementById('sliderCpuDuty').value = s.cpu_duty_percent;
    document.getElementById('valCpuDuty').textContent = `${s.cpu_duty_percent}%`;

    document.getElementById('sliderWorkerThreads').value = s.worker_threads;
    document.getElementById('valWorkerThreads').textContent = `${s.worker_threads} Threads`;

    document.getElementById('sliderBandwidthLimit').value = s.bandwidth_limit_mbps;
    document.getElementById('valBandwidthLimit').textContent = s.bandwidth_limit_mbps === 0 ? "Uncapped (Max Wire Speed)" : `${s.bandwidth_limit_mbps} MB/s`;
  } catch (err) {
    console.error(err);
  }
}

// ----------------- EMERGENCY CONTROLS -----------------

function setupEmergencyControls() {
  document.getElementById('btnEmergencyCancel').addEventListener('click', async () => {
    if (confirm("Are you sure you want to cancel the active transfer? Progress is journaled for resume.")) {
      if (window.pywebview) {
        await window.pywebview.api.cancel_active_transfer();
      }
    }
  });
}
