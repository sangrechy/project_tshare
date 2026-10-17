let currentPath = '';

function loadFiles(path = '') {
  fetch(`/api/list?path=${encodeURIComponent(path)}`)
    .then(res => res.json())
    .then(data => {
      currentPath = data.currentPath;
      updateBreadcrumb(currentPath);

      const list = document.getElementById('fileList');
      list.innerHTML = '';

      if (currentPath !== '') {
        const upPath = currentPath.split('/').slice(0, -1).join('/');
        const backItem = createFileItem('⬅️ Go Back', () => loadFiles(upPath), '📁');
        list.appendChild(backItem);
      }

      data.items.forEach(item => {
        const icon = item.isDir ? '📁' : '📄';
        const filePath = currentPath ? `${currentPath}/${item.name}` : item.name;

        const itemElement = createFileItem(item.name, () => {
          if (item.isDir) {
            loadFiles(filePath);
          } else {
            window.location.href = `/download?path=${encodeURIComponent(filePath)}`;
          }
        }, icon);

        list.appendChild(itemElement);
      });
    });
}

function createFileItem(name, onClick, icon) {
  const li = document.createElement('li');
  li.className = 'file-item';
  li.onclick = onClick;

  const iconSpan = document.createElement('span');
  iconSpan.className = 'file-icon';
  iconSpan.textContent = icon;

  const nameSpan = document.createElement('span');
  nameSpan.className = 'file-name';
  nameSpan.textContent = name;

  li.appendChild(iconSpan);
  li.appendChild(nameSpan);

  return li;
}

function updateBreadcrumb(path) {
  const container = document.getElementById('breadcrumb');
  container.innerHTML = '';
  const parts = path.split('/');
  parts.forEach((part, i) => {
    if (i > 0) container.innerHTML += ' / ';
    const span = document.createElement('span');
    span.textContent = part || 'root';
    span.onclick = () => loadFiles(parts.slice(0, i + 1).join('/'));
    container.appendChild(span);
  });

  if (!path) container.innerHTML = '<span>root</span>';
}

loadFiles();
