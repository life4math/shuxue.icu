const API_ROOT = '/api/v1';
let csrfToken = '';

function setAuthenticated(user, token) {
  csrfToken = token || '';
  document.getElementById('login-panel').hidden = true;
  document.getElementById('console-panel').hidden = false;
  document.getElementById('logout-button').hidden = false;
  document.getElementById('admin-user').textContent = `${user.name} · ${user.role.toUpperCase()}`;
}

function setLoggedOut() {
  csrfToken = '';
  document.getElementById('login-panel').hidden = false;
  document.getElementById('console-panel').hidden = true;
  document.getElementById('logout-button').hidden = true;
  document.getElementById('admin-user').textContent = '';
}

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (csrfToken && options.method && options.method !== 'GET') {
    headers.set('X-CSRF-Token', csrfToken);
  }
  const response = await fetch(API_ROOT + path, { ...options, headers, credentials: 'same-origin' });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || `请求失败 (${response.status})`);
  return data;
}

async function restoreSession() {
  try {
    const data = await api('/auth/me');
    setAuthenticated(data.user, data.csrf_token);
    await refreshConsole();
  } catch (_) {
    setLoggedOut();
  }
}

document.getElementById('login-form').addEventListener('submit', async event => {
  event.preventDefault();
  const error = document.getElementById('login-error');
  error.textContent = '';
  try {
    const data = await api('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: document.getElementById('login-email').value,
        password: document.getElementById('login-password').value
      })
    });
    setAuthenticated(data.user, data.csrf_token);
    event.target.reset();
    await refreshConsole();
  } catch (err) {
    error.textContent = err.message;
  }
});

document.getElementById('logout-button').addEventListener('click', async () => {
  try {
    await api('/auth/logout', { method: 'POST' });
  } finally {
    setLoggedOut();
  }
});

document.getElementById('upload-form').addEventListener('submit', async event => {
  event.preventDefault();
  const status = document.getElementById('upload-status');
  const file = document.getElementById('upload-file').files[0];
  if (!file) return;
  status.textContent = '正在上传…';
  try {
    const form = new FormData();
    form.append('file', file);
    const uploaded = await api('/admin/uploads', { method: 'POST', body: form });
    status.textContent = uploaded.duplicate ? '检测到相同文件，使用已有上传记录。' : '上传完成，正在创建任务…';
    const result = await api('/admin/jobs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ upload_id: uploaded.upload.id })
    });
    status.textContent = `任务已创建：${result.job.status}`;
    event.target.reset();
    await loadJobs();
  } catch (err) {
    status.textContent = `失败：${err.message}`;
  }
});

document.getElementById('refresh-button').addEventListener('click', refreshConsole);

async function refreshConsole() {
  await Promise.all([loadJobs(), loadReviews()]);
}

async function loadJobs() {
  const target = document.getElementById('job-list');
  try {
    const data = await api('/admin/jobs');
    target.replaceChildren(...data.items.map(renderJob));
    if (!data.items.length) target.textContent = '暂无任务';
  } catch (err) {
    target.textContent = err.message;
  }
}

function renderJob(job) {
  const row = document.createElement('div');
  row.className = 'admin-row';
  const title = document.createElement('strong');
  title.textContent = job.status;
  const meta = document.createElement('div');
  meta.className = 'admin-row-meta';
  meta.append(document.createTextNode(job.id), document.createTextNode(`${job.progress}%`));
  row.append(title, meta);
  if (job.error) {
    const error = document.createElement('p');
    error.className = 'admin-error';
    error.textContent = job.error;
    row.append(error);
  }
  return row;
}

async function loadReviews() {
  const target = document.getElementById('review-list');
  try {
    const data = await api('/admin/reviews');
    target.replaceChildren(...data.items.map(renderReview));
    if (!data.items.length) target.textContent = '暂无待审核内容';
  } catch (err) {
    target.textContent = err.message;
  }
}

function renderReview(item) {
  const row = document.createElement('div');
  row.className = 'admin-row';
  const heading = document.createElement('strong');
  heading.textContent = item.entity_type === 'question'
    ? (item.payload.stem || '未命名题目')
    : (item.payload.name || '未命名方法');
  const meta = document.createElement('div');
  meta.className = 'admin-row-meta';
  meta.append(
    document.createTextNode(`${item.entity_type} · ${item.status}`),
    document.createTextNode(`AI ${Math.round(item.ai_confidence * 100)}%`)
  );
  row.append(heading, meta);
  if (item.status === 'pending_review') {
    const actions = document.createElement('div');
    actions.className = 'admin-row-actions';
    const approve = document.createElement('button');
    approve.className = 'btn-accent';
    approve.textContent = '批准发布';
    approve.addEventListener('click', () => reviewAction(item.id, 'approve'));
    const reject = document.createElement('button');
    reject.className = 'btn-ghost';
    reject.textContent = '拒绝';
    reject.addEventListener('click', () => reviewAction(item.id, 'reject'));
    actions.append(approve, reject);
    row.append(actions);
  }
  return row;
}

async function reviewAction(id, action) {
  try {
    await api(`/admin/reviews/${id}/${action}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    });
    await loadReviews();
  } catch (err) {
    window.alert(err.message);
  }
}

restoreSession();
