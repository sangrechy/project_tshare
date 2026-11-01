let currentPath = '';
let allItems = [];

document.addEventListener('DOMContentLoaded', () => {
  setupNavigation();
  setupUploadZone();
  setupSearch();
  loadHostInfo();
  loadDirectory('');
});

function setupNavigation() {
  const btnBrowse = document.getElementById('tabBtnBrowse');
  const btnUpload = document.getElementById('tabBtnUpload');
  const viewBrowse = document.getElementById('viewBrowse');
  const viewUpload = document.getElementById('viewUpload');

  btnBrowse.addEventListener('click', () => {
    btnBrowse.classList.add('active');
    btnUpload.classList.remove('active');
    viewBrowse.classList.add('active');
    viewUpload.classList.remove('active');
  });

  btnUpload.addEventListener('click', () => {
    btnUpload.classList.add('active');
    btnBrowse.classList.remove('active');
    viewUpload.classList.add('active');
    viewBrowse.classList.remove('active');
  });
}

async function loadHostInfo() {
  try {
    const res = await fetch('/portal/api/info');
    const data = await res.json();
    const infoEl = document.getElementById('portalHostInfo');
    if (infoEl) {
      infoEl.textContent = `Host: ${data.hostname} (${data.server_ip}) · Shared: ${data.shared_folder_name}`;
    }
    if (!data.allow_uploads) {
      const btnUpload = document.getElementById('tabBtnUpload');
      if (btnUpload) btnUpload.style.display = 'none';
    }
  } catch (e) {
    console.error('Failed to load host info:', e);
  }
}

async function loadDirectory(path = '') {
  const listEl = document.getElementById('fileList');
  listEl.innerHTML = '<li class="loading-item">Loading directory...</li>';

  try {
    const res = await fetch(`/portal/api/list?path=${encodeURIComponent(path)}`);
    const data = await res.json();

    if (!data.success && data.error) {
      listEl.innerHTML = `<li class="loading-item" style="color: #f87171;">${data.error}</li>`;
      return;
    }

    currentPath = data.current_path || '';
    allItems = data.items || [];
    renderBreadcrumbs(currentPath);
    renderFileList(allItems);
  } catch (e) {
    listEl.innerHTML = `<li class="loading-item" style="color: #f87171;">Failed to connect to host.</li>`;
  }
}

function renderBreadcrumbs(path) {
  const bar = document.getElementById('breadcrumbBar');
  bar.innerHTML = '';

  const rootCrumb = document.createElement('span');
  rootCrumb.className = `crumb ${!path ? 'active' : ''}`;
  rootCrumb.textContent = 'Home';
  rootCrumb.onclick = () => loadDirectory('');
  bar.appendChild(rootCrumb);

  if (!path) return;

  const parts = path.split('/');
  let accumulated = '';
  parts.forEach((part, idx) => {
    bar.appendChild(document.createTextNode(' / '));
    accumulated += (idx > 0 ? '/' : '') + part;
    const isLast = idx === parts.length - 1;

    const crumb = document.createElement('span');
    crumb.className = `crumb ${isLast ? 'active' : ''}`;
    crumb.textContent = part;
    const targetPath = accumulated;
    if (!isLast) {
      crumb.onclick = () => loadDirectory(targetPath);
    }
    bar.appendChild(crumb);
  });
}

function renderFileList(items) {
  const listEl = document.getElementById('fileList');
  listEl.innerHTML = '';

  if (currentPath !== '') {
    const upPath = currentPath.split('/').slice(0, -1).join('/');
    const upItem = document.createElement('li');
    upItem.className = 'file-item';
    upItem.innerHTML = `
      <div class="item-left">
        <span class="item-icon">⬅️</span>
        <span class="item-name" style="font-weight: 600;">.. (Go Up)</span>
      </div>
      <div class="item-right">
        <span class="item-size">Back</span>
      </div>
    `;
    upItem.onclick = () => loadDirectory(upPath);
    listEl.appendChild(upItem);
  }

  if (items.length === 0) {
    listEl.innerHTML += '<li class="loading-item">Folder is empty</li>';
    return;
  }

  items.forEach(item => {
    const li = document.createElement('li');
    li.className = 'file-item';
    const icon = item.is_dir ? '📁' : getFileIcon(item.name);
    const itemRelPath = currentPath ? `${currentPath}/${item.name}` : item.name;

    li.innerHTML = `
      <div class="item-left">
        <span class="item-icon">${icon}</span>
        <span class="item-name">${escapeHtml(item.name)}</span>
      </div>
      <div class="item-right">
        <span class="item-size">${item.size_display}</span>
        ${!item.is_dir ? `<a class="btn-download-pill" href="/portal/api/download?path=${encodeURIComponent(itemRelPath)}" download="${escapeHtml(item.name)}">Download</a>` : ''}
      </div>
    `;

    if (item.is_dir) {
      li.onclick = () => loadDirectory(itemRelPath);
    }

    listEl.appendChild(li);
  });
}

function setupSearch() {
  const input = document.getElementById('searchInput');
  input.addEventListener('input', () => {
    const term = input.value.trim().toLowerCase();
    if (!term) {
      renderFileList(allItems);
      return;
    }
    const filtered = allItems.filter(i => i.name.toLowerCase().includes(term));
    renderFileList(filtered);
  });
}

function setupUploadZone() {
  const dropZone = document.getElementById('dropZone');
  const fileInput = document.getElementById('fileInput');

  ['dragenter', 'dragover'].forEach(name => {
    dropZone.addEventListener(name, (e) => {
      e.preventDefault();
      dropZone.classList.add('dragover');
    });
  });

  ['dragleave', 'drop'].forEach(name => {
    dropZone.addEventListener(name, (e) => {
      e.preventDefault();
      dropZone.classList.remove('dragover');
    });
  });

  dropZone.addEventListener('drop', (e) => {
    const files = e.dataTransfer.files;
    if (files.length > 0) handleFileUpload(files);
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) handleFileUpload(fileInput.files);
  });
}

function handleFileUpload(files) {
  const progressWrap = document.getElementById('uploadProgressWrap');
  const progressBar = document.getElementById('uploadBar');
  const statusText = document.getElementById('uploadStatusText');
  const pctText = document.getElementById('uploadPctText');
  const resultsCard = document.getElementById('uploadResults');
  const uploadedList = document.getElementById('uploadedItemsList');

  progressWrap.classList.remove('hidden');
  progressBar.style.width = '0%';
  statusText.textContent = `Uploading ${files.length} file(s)...`;
  pctText.textContent = '0%';

  const formData = new FormData();
  for (let i = 0; i < files.length; i++) {
    formData.append('files', files[i]);
  }

  const xhr = new XMLHttpRequest();
  xhr.open('POST', '/portal/api/upload', true);

  xhr.upload.onprogress = (e) => {
    if (e.lengthComputable) {
      const pct = Math.round((e.loaded / e.total) * 100);
      progressBar.style.width = `${pct}%`;
      pctText.textContent = `${pct}%`;
    }
  };

  xhr.onload = () => {
    if (xhr.status === 200) {
      try {
        const res = JSON.parse(xhr.responseText);
        statusText.textContent = 'Upload complete!';
        resultsCard.classList.remove('hidden');
        uploadedList.innerHTML = '';
        if (res.uploaded) {
          res.uploaded.forEach(u => {
            const li = document.createElement('li');
            li.textContent = `✓ ${u.name} (${(u.size / 1024).toFixed(1)} KB)`;
            uploadedList.appendChild(li);
          });
        }
        // Refresh directory if in current path
        loadDirectory(currentPath);
      } catch (err) {
        statusText.textContent = 'Upload completed with status response error.';
      }
    } else {
      statusText.textContent = `Upload failed (Status ${xhr.status})`;
    }
  };

  xhr.onerror = () => {
    statusText.textContent = 'Upload failed due to network error.';
  };

  xhr.send(formData);
}

function getFileIcon(name) {
  const ext = name.split('.').pop().toLowerCase();
  if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'].includes(ext)) return '🖼️';
  if (['mp4', 'mkv', 'avi', 'mov'].includes(ext)) return '🎬';
  if (['mp3', 'wav', 'flac', 'aac'].includes(ext)) return '🎵';
  if (['zip', 'tar', 'gz', '7z', 'rar'].includes(ext)) return '📦';
  if (['pdf', 'doc', 'docx', 'txt', 'md'].includes(ext)) return '📄';
  if (['iso', 'img', 'bin'].includes(ext)) return '💿';
  return '📄';
}

function escapeHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
