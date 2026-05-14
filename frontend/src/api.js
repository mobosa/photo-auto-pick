const API_BASE = '/api';

async function _fetch(url, options = {}) {
  const res = await fetch(url, options);
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function uploadPhotos(files) {
  const formData = new FormData();
  for (const file of files) formData.append('files', file);
  return _fetch(`${API_BASE}/upload`, { method: 'POST', body: formData });
}

export async function scanFolder(folderPath) {
  return _fetch(`${API_BASE}/scan-folder`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ folder_path: folderPath }),
  });
}

export async function getTaskStatus(taskId) {
  return _fetch(`${API_BASE}/status/${taskId}`);
}

export async function getResults(taskId, filters = {}) {
  const params = new URLSearchParams();
  if (filters.minScore) params.set('min_score', filters.minScore);
  if (filters.grade) params.set('grade', filters.grade);
  if (filters.sortBy) params.set('sort_by', filters.sortBy);
  if (filters.limit) params.set('limit', filters.limit);
  if (filters.offset) params.set('offset', filters.offset);
  return _fetch(`${API_BASE}/results/${taskId}?${params}`);
}

export async function exportPhotos(taskId, minScore = 70) {
  return _fetch(`${API_BASE}/results/${taskId}/export?min_score=${minScore}`);
}

export async function getHistory() {
  return _fetch(`${API_BASE}/history`);
}

export async function deleteTask(taskId) {
  return _fetch(`${API_BASE}/history/${taskId}`, { method: 'DELETE' });
}

export async function deletePhotos(ids, deleteSource = true) {
  return _fetch(`${API_BASE}/photos/delete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ids, delete_source: deleteSource }),
  });
}

export async function browseFolder(path = '') {
  return _fetch(`${API_BASE}/browse?path=${encodeURIComponent(path)}`);
}

export async function clearCache() {
  return _fetch(`${API_BASE}/clear-cache`, { method: 'POST' });
}

export async function cacheInfo() {
  return _fetch(`${API_BASE}/cache-info`);
}

export function thumbnailUrl(taskId, filename) {
  return `${API_BASE}/thumbnail/${taskId}/${encodeURIComponent(filename)}`;
}
