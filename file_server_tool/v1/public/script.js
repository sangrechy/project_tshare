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
        const li = document.createElement('li');
        li.textContent = '.. (go up)';
        li.onclick = () => loadFiles(upPath);
        list.appendChild(li);
      }

      data.items.forEach(item => {
        const li = document.createElement('li');
        li.textContent = item.name;
        if (item.isDir) {
          li.onclick = () => loadFiles(currentPath ? `${currentPath}/${item.name}` : item.name);
        } else {
          li.onclick = () => {
            const filePath = currentPath ? `${currentPath}/${item.name}` : item.name;
            window.location.href = `/download?path=${encodeURIComponent(filePath)}`;
          };
        }
        list.appendChild(li);
      });
    });
}

function updateBreadcrumb(path) {
  const breadcrumb = document.getElementById('breadcrumb');
  const parts = path.split('/');
  let fullPath = '';
  breadcrumb.innerHTML = '';

  parts.forEach((part, index) => {
    if (index > 0) breadcrumb.innerHTML += ' / ';
    fullPath += (index ? '/' : '') + part;
    const span = document.createElement('span');
    span.textContent = part || 'root';
    span.style.cursor = 'pointer';
    span.onclick = () => loadFiles(parts.slice(0, index + 1).join('/'));
    breadcrumb.appendChild(span);
  });

  if (!path) breadcrumb.innerHTML = 'root';
}

loadFiles();
