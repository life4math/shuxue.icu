const API_ROOT = '/api/v1';
let csrfToken = '';
let currentUser = null;
let knowledgeDocuments = [];
let users = [];

function isAdmin() {
  return currentUser && currentUser.role === 'admin';
}

function setAuthenticated(user, token) {
  currentUser = user;
  csrfToken = token || '';
  document.getElementById('login-panel').hidden = true;
  document.getElementById('console-panel').hidden = false;
  document.getElementById('logout-button').hidden = false;
  document.getElementById('admin-user').textContent = `${user.name} · ${user.role.toUpperCase()}`;

  const userCard = document.getElementById('users-admin-card');
  if (userCard) {
    userCard.hidden = !isAdmin();
  }
}

function setLoggedOut() {
  currentUser = null;
  csrfToken = '';
  document.getElementById('login-panel').hidden = false;
  document.getElementById('console-panel').hidden = true;
  document.getElementById('logout-button').hidden = true;
  document.getElementById('admin-user').textContent = '';

  const userCard = document.getElementById('users-admin-card');
  if (userCard) {
    userCard.hidden = true;
  }
  knowledgeDocuments = [];
  users = [];
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
        password: document.getElementById('login-password').value,
      }),
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
      body: JSON.stringify({ upload_id: uploaded.upload.id }),
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
  const tasks = [loadJobs(), loadReviews(), loadKnowledgeDocuments()];
  if (isAdmin()) tasks.push(loadUsers());
  await Promise.all(tasks);
}

async function loadKnowledgeDocuments() {
  const target = document.getElementById('knowledge-admin-list');
  if (!target) return;
  try {
    const data = await api('/admin/knowledge');
    knowledgeDocuments = data.items || [];
    target.replaceChildren(...knowledgeDocuments.map(renderKnowledgeDocument));
    if (!knowledgeDocuments.length) {
      target.textContent = '暂无数据库知识正文，请先运行 seed_knowledge.py';
      return;
    }
    if (!document.getElementById('knowledge-admin-node-id').value) {
      selectKnowledgeDocument(knowledgeDocuments[0].node_id);
    }
  } catch (err) {
    target.textContent = err.message;
  }
}

function renderKnowledgeDocument(item) {
  const row = document.createElement('div');
  row.className = 'admin-row';
  row.dataset.nodeId = item.node_id;
  row.addEventListener('click', () => selectKnowledgeDocument(item.node_id));
  const heading = document.createElement('strong');
  heading.textContent = item.title || item.node_id;
  const meta = document.createElement('div');
  meta.className = 'admin-row-meta';
  meta.append(document.createTextNode(item.node_id), document.createTextNode(item.status));
  row.append(heading, meta);
  return row;
}

function selectKnowledgeDocument(nodeId) {
  const item = knowledgeDocuments.find(entry => entry.node_id === nodeId);
  if (!item) return;
  document.getElementById('knowledge-admin-node-id').value = item.node_id;
  document.getElementById('knowledge-admin-title').value = item.title || '';
  document.getElementById('knowledge-admin-payload').value = JSON.stringify(item.payload || {}, null, 2);
  document.querySelectorAll('#knowledge-admin-list .admin-row').forEach(row => {
    row.classList.toggle('selected', row.dataset.nodeId === nodeId);
  });
}

function readKnowledgeForm() {
  const payload = JSON.parse(document.getElementById('knowledge-admin-payload').value);
  payload.title = document.getElementById('knowledge-admin-title').value.trim();
  return payload;
}

async function knowledgeMutation(action) {
  const nodeId = document.getElementById('knowledge-admin-node-id').value;
  if (!nodeId) return;
  const status = document.getElementById('knowledge-admin-status');
  try {
    const data = action === 'save'
      ? await api(`/admin/knowledge/${encodeURIComponent(nodeId)}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(readKnowledgeForm()),
        })
      : await api(`/admin/knowledge/${encodeURIComponent(nodeId)}/${action}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: '{}',
        });
    status.textContent = `已${action === 'save' ? '保存草稿' : action === 'submit' ? '提交审核' : '发布'} · ${data.knowledge.status}`;
    await loadKnowledgeDocuments();
  } catch (err) {
    status.textContent = `失败：${err.message}`;
  }
}

document.getElementById('knowledge-admin-form')?.addEventListener('submit', event => {
  event.preventDefault();
  knowledgeMutation('save');
});
document.getElementById('knowledge-admin-preview')?.addEventListener('click', () => {
  const status = document.getElementById('knowledge-admin-status');
  try {
    readKnowledgeForm();
    status.textContent = 'JSON 结构有效';
  } catch (_) {
    status.textContent = 'JSON 格式错误，请检查公式字符串和逗号';
  }
});
document.getElementById('knowledge-admin-submit')?.addEventListener('click', () => knowledgeMutation('submit'));
document.getElementById('knowledge-admin-publish')?.addEventListener('click', () => knowledgeMutation('publish'));

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
  meta.append(document.createTextNode(`${item.entity_type} · ${item.status}`), document.createTextNode(`AI ${Math.round(item.ai_confidence * 100)}%`));
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
      body: JSON.stringify({}),
    });
    await loadReviews();
  } catch (err) {
    window.alert(err.message);
  }
}

async function loadUsers() {
  const target = document.getElementById('user-admin-list');
  const status = document.getElementById('user-admin-status');
  if (!target || !isAdmin()) {
    if (target) target.textContent = '';
    if (status) status.textContent = '';
    return;
  }

  try {
    const data = await api('/admin/users');
    users = data.items || [];
    target.replaceChildren(...users.map(renderUser));
    status.textContent = '';

    if (!users.length) {
      target.textContent = '暂无账号';
      return;
    }

    const selected = document.getElementById('user-admin-id').value;
    if (!selected) {
      selectUser(users[0].id);
    }
  } catch (err) {
    status.textContent = `加载账号失败：${err.message}`;
  }
}

function renderUser(user) {
  const row = document.createElement('div');
  row.className = 'admin-row';
  row.dataset.userId = user.id;
  row.addEventListener('click', () => selectUser(user.id));

  const heading = document.createElement('strong');
  heading.textContent = `${user.name} (${user.email})`;

  const meta = document.createElement('div');
  meta.className = 'admin-row-meta';
  const roleText = user.role === 'admin' ? '管理员' : '教师';
  meta.append(document.createTextNode(roleText), document.createTextNode(user.is_active ? '启用' : '停用'));

  const actions = document.createElement('div');
  actions.className = 'admin-row-actions';

  const activeButton = document.createElement('button');
  activeButton.className = 'btn-ghost';
  activeButton.textContent = user.is_active ? '停用' : '启用';
  activeButton.addEventListener('click', event => {
    event.preventDefault();
    event.stopPropagation();
    toggleUserStatus(user.id, !user.is_active);
  });

  const resetButton = document.createElement('button');
  resetButton.className = 'btn-ghost';
  resetButton.textContent = '重置密码';
  resetButton.addEventListener('click', event => {
    event.preventDefault();
    event.stopPropagation();
    selectUser(user.id);
    resetUserPassword();
  });

  actions.append(activeButton, resetButton);

  row.append(heading, meta, actions);
  return row;
}

function selectUser(userId) {
  const user = users.find(entry => entry.id === userId);
  if (!user) return;

  document.getElementById('user-admin-id').value = user.id;
  document.getElementById('user-admin-email').value = user.email;
  document.getElementById('user-admin-email').readOnly = true;
  document.getElementById('user-admin-name').value = user.name || '';
  document.getElementById('user-admin-password').value = '';
  document.getElementById('user-admin-role').value = user.role;
  document.getElementById('user-admin-active').checked = !!user.is_active;
  document.querySelectorAll('#user-admin-list .admin-row').forEach(row => {
    row.classList.toggle('selected', row.dataset.userId === userId);
  });
}

function clearUserForm() {
  document.getElementById('user-admin-id').value = '';
  document.getElementById('user-admin-email').value = '';
  document.getElementById('user-admin-email').readOnly = false;
  document.getElementById('user-admin-name').value = '';
  document.getElementById('user-admin-password').value = '';
  document.getElementById('user-admin-role').value = 'teacher';
  document.getElementById('user-admin-active').checked = true;
  document.querySelectorAll('#user-admin-list .admin-row').forEach(row => {
    row.classList.remove('selected');
  });
}

function readUserForm() {
  return {
    id: document.getElementById('user-admin-id').value,
    email: document.getElementById('user-admin-email').value.trim().toLowerCase(),
    display_name: document.getElementById('user-admin-name').value.trim(),
    password: document.getElementById('user-admin-password').value,
    role: document.getElementById('user-admin-role').value,
    is_active: document.getElementById('user-admin-active').checked,
  };
}

async function saveUser() {
  const status = document.getElementById('user-admin-status');
  const values = readUserForm();

  if (!values.display_name) {
    status.textContent = '姓名不能为空';
    return;
  }

  try {
    if (!values.id) {
      if (!values.email || !values.password) {
        status.textContent = '新增账号需要填写邮箱与密码';
        return;
      }
      if (values.password.length < 12) {
        status.textContent = '密码必须不少于12位';
        return;
      }
      await api('/admin/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: values.email,
          display_name: values.display_name,
          password: values.password,
          role: values.role,
          is_active: values.is_active,
        }),
      });
      status.textContent = '账号创建成功';
    } else {
      await api(`/admin/users/${encodeURIComponent(values.id)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          display_name: values.display_name,
          role: values.role,
          is_active: values.is_active,
        }),
      });
      status.textContent = '账号信息已更新';
    }

    await loadUsers();
    clearUserForm();
  } catch (err) {
    status.textContent = `失败：${err.message}`;
  }
}

async function toggleUserStatus(userId, isActive) {
  if (!isAdmin()) return;
  const user = users.find(entry => entry.id === userId);
  if (!user) return;

  try {
    await api(`/admin/users/${encodeURIComponent(userId)}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ is_active: isActive }),
    });
    await loadUsers();
  } catch (err) {
    document.getElementById('user-admin-status').textContent = `失败：${err.message}`;
  }
}

async function resetUserPassword() {
  const status = document.getElementById('user-admin-status');
  const userId = document.getElementById('user-admin-id').value;
  if (!userId) {
    status.textContent = '请先选择账号';
    return;
  }

  const manual = document.getElementById('user-admin-password').value.trim();
  if (manual) {
    if (manual.length < 12) {
      status.textContent = '密码必须不少于12位';
      return;
    }
    try {
      await api(`/admin/users/${encodeURIComponent(userId)}/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password: manual }),
      });
      status.textContent = '密码重置成功';
      await loadUsers();
      document.getElementById('user-admin-password').value = '';
    } catch (err) {
      status.textContent = `失败：${err.message}`;
    }
    return;
  }

  status.textContent = '请在“密码”输入框填写新密码后再重置';
}

document.getElementById('user-admin-form')?.addEventListener('submit', event => {
  event.preventDefault();
  if (!isAdmin()) {
    document.getElementById('user-admin-status').textContent = '权限不足';
    return;
  }
  saveUser();
});

document.getElementById('user-admin-clear')?.addEventListener('click', () => {
  if (!isAdmin()) return;
  clearUserForm();
});

document.getElementById('user-admin-password-reset')?.addEventListener('click', () => {
  if (!isAdmin()) return;
  resetUserPassword();
});

restoreSession();
