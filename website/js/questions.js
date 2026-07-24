(function () {
  'use strict';

  const API_ROOT = '/api/v1';
  const state = {
    csrfToken: '',
    user: null,
    questions: [],
    knowledgeNodes: [],
    question: null,
  };

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }

  async function api(path, options = {}) {
    const headers = new Headers(options.headers || {});
    if (state.csrfToken && options.method && options.method !== 'GET') {
      headers.set('X-CSRF-Token', state.csrfToken);
    }
    const response = await fetch(API_ROOT + path, {
      ...options,
      headers,
      credentials: 'same-origin',
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(data.error || `请求失败 (${response.status})`);
      error.status = response.status;
      error.data = data;
      throw error;
    }
    return data;
  }

  function jsonRequest(method, body) {
    return {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body || {}),
    };
  }

  function statusLabel(value) {
    return {
      draft: '草稿',
      pending_review: '待审核',
      published: '已发布',
      archived: '已归档',
      merged: '已合并',
    }[value] || value || '新题目';
  }

  function setStatus(message) {
    document.getElementById('question-status').textContent = message || '';
  }

  function renderList() {
    const target = document.getElementById('question-list');
    target.replaceChildren();
    if (!state.questions.length) {
      target.append(element('p', 'question-preview-note', '当前筛选条件下没有题目。'));
      return;
    }
    state.questions.forEach(question => {
      const button = element('button', 'question-list-item');
      button.type = 'button';
      button.classList.toggle('selected', state.question?.id === question.id);
      button.append(
        element('strong', '', `${question.code} · ${question.stem.slice(0, 38)}`),
        element(
          'span',
          '',
          `${question.module} · ${question.question_type} · 难度 ${question.difficulty} · ${statusLabel(question.status)} · v${question.version}`,
        ),
      );
      button.addEventListener('click', () => selectQuestion(question.id));
      target.append(button);
    });
  }

  function queryString() {
    const params = new URLSearchParams();
    const query = document.getElementById('question-filter-query').value.trim();
    const module = document.getElementById('question-filter-module').value;
    const status = document.getElementById('question-filter-status').value;
    if (query) params.set('query', query);
    if (module) params.set('module', module);
    if (status) params.set('status', status);
    params.set('limit', '200');
    return params.toString();
  }

  async function loadQuestions(preferredId = '') {
    const data = await api(`/admin/questions?${queryString()}`);
    state.questions = data.items || [];
    renderList();
    const targetId = preferredId || state.question?.id;
    if (targetId && state.questions.some(item => item.id === targetId)) {
      await selectQuestion(targetId);
    }
  }

  async function loadKnowledgeNodes() {
    const data = await api('/admin/knowledge/nodes');
    state.knowledgeNodes = (data.items || []).filter(
      item => !['archived', 'merged'].includes(item.status),
    );
    const select = document.getElementById('question-knowledge');
    select.replaceChildren();
    state.knowledgeNodes.forEach(item => {
      select.add(new Option(`${item.code} · ${item.title}`, item.id));
    });
  }

  function selectedKnowledgeIds() {
    return [...document.getElementById('question-knowledge').selectedOptions]
      .map(option => option.value);
  }

  function fillForm(question) {
    state.question = question || null;
    document.getElementById('question-code').value = question?.code || '';
    document.getElementById('question-code').readOnly = !!question;
    document.getElementById('question-module').value = question?.module || 'FUNC';
    document.getElementById('question-type').value = question?.question_type || 'solve';
    document.getElementById('question-difficulty').value = String(question?.difficulty || 3);
    document.getElementById('question-stem').value = question?.stem || '';
    document.getElementById('question-options').value =
      JSON.stringify(question?.options || [], null, 2);
    document.getElementById('question-answer').value = question?.answer || '';
    document.getElementById('question-analysis').value = question?.analysis || '';
    document.getElementById('question-tags').value = (question?.tags || []).join(', ');
    document.getElementById('question-source').value =
      JSON.stringify(question?.source || {}, null, 2);
    document.getElementById('question-change-reason').value = '';
    const selectedIds = new Set(question?.knowledge_node_ids || []);
    [...document.getElementById('question-knowledge').options].forEach(option => {
      option.selected = selectedIds.has(option.value);
    });
    document.getElementById('question-status-badge').textContent = question
      ? `${statusLabel(question.status)} · v${question.version}`
      : '新题目';
    document.getElementById('question-submit').disabled =
      !question || question.status !== 'draft';
    document.getElementById('question-publish').disabled =
      !question || ['archived', 'merged'].includes(question.status);
    document.getElementById('question-archive').disabled =
      !question || question.status === 'merged';
    setStatus('');
    renderList();
    renderPreview();
    loadVersions();
  }

  async function selectQuestion(questionId) {
    try {
      const data = await api(`/admin/questions/${encodeURIComponent(questionId)}`);
      fillForm(data.question);
    } catch (error) {
      setStatus(error.message);
    }
  }

  function parseJsonField(id, fallback) {
    const raw = document.getElementById(id).value.trim();
    if (!raw) return fallback;
    return JSON.parse(raw);
  }

  function formPayload() {
    const tags = document.getElementById('question-tags').value
      .split(/[,，]/)
      .map(item => item.trim())
      .filter((item, index, array) => item && array.indexOf(item) === index);
    return {
      code: document.getElementById('question-code').value.trim(),
      module: document.getElementById('question-module').value,
      question_type: document.getElementById('question-type').value,
      difficulty: Number(document.getElementById('question-difficulty').value),
      stem: document.getElementById('question-stem').value.trim(),
      options: parseJsonField('question-options', []),
      answer: document.getElementById('question-answer').value.trim(),
      analysis: document.getElementById('question-analysis').value.trim(),
      tags,
      source: parseJsonField('question-source', {}),
      knowledge_node_ids: selectedKnowledgeIds(),
      change_reason: document.getElementById('question-change-reason').value.trim(),
    };
  }

  function previewBlock() {
    let options = [];
    try {
      options = parseJsonField('question-options', []);
    } catch (_) {
      options = [];
    }
    return {
      id: 'question-preview',
      type: 'question_ref',
      question_id: state.question?.id || '',
      code: document.getElementById('question-code').value.trim(),
      title: document.getElementById('question-code').value.trim() || '题目预览',
      stem: document.getElementById('question-stem').value,
      options,
      answer: document.getElementById('question-answer').value,
      analysis: document.getElementById('question-analysis').value,
      difficulty: Number(document.getElementById('question-difficulty').value),
      question_type: document.getElementById('question-type').value,
    };
  }

  function renderPreview() {
    const target = document.getElementById('question-preview-content');
    target.replaceChildren(
      window.LectureRenderer.renderBlock(previewBlock(), { revealAnswers: true }),
    );
  }

  async function saveQuestion(event) {
    event.preventDefault();
    try {
      const payload = formPayload();
      let data;
      if (state.question) {
        payload.version = state.question.version;
        data = await api(
          `/admin/questions/${encodeURIComponent(state.question.id)}`,
          jsonRequest('PATCH', payload),
        );
      } else {
        data = await api('/admin/questions', jsonRequest('POST', payload));
      }
      setStatus('草稿已保存');
      await loadQuestions(data.question.id);
      if (!state.questions.some(item => item.id === data.question.id)) {
        await selectQuestion(data.question.id);
      }
    } catch (error) {
      setStatus(
        error.data?.duplicate_id
          ? `保存失败：检测到重复题目 ${error.data.duplicate_id}`
          : `保存失败：${error.message}`,
      );
    }
  }

  async function questionAction(action) {
    if (!state.question) return;
    if (action === 'archive' && !window.confirm('归档后将从公开题库和备课选择器撤下。继续吗？')) {
      return;
    }
    try {
      const data = await api(
        `/admin/questions/${encodeURIComponent(state.question.id)}/${action}`,
        jsonRequest('POST', {}),
      );
      fillForm(data.question);
      setStatus(
        action === 'submit' ? '已提交审核'
          : action === 'publish' ? '已发布到正式题库'
            : '已归档',
      );
      await loadQuestions(data.question.id);
    } catch (error) {
      setStatus(`操作失败：${error.message}`);
    }
  }

  async function loadVersions() {
    const target = document.getElementById('question-versions');
    target.replaceChildren();
    if (!state.question) {
      target.append(element('p', 'question-preview-note', '保存题目后会生成不可变版本记录。'));
      return;
    }
    try {
      const data = await api(
        `/admin/questions/${encodeURIComponent(state.question.id)}/versions`,
      );
      (data.items || []).slice(0, 20).forEach(item => {
        const row = element('div', 'question-version-row');
        row.append(element('span', '', `v${item.version} · ${item.change_reason}`));
        if (item.version !== state.question.version) {
          const button = element('button', 'btn-ghost', '回滚');
          button.type = 'button';
          button.addEventListener('click', () => rollbackVersion(item.version));
          row.append(button);
        }
        target.append(row);
      });
    } catch (error) {
      target.append(element('p', 'question-preview-note', error.message));
    }
  }

  async function rollbackVersion(version) {
    if (!state.question || !window.confirm(`确认以 v${version} 创建一个新草稿版本？`)) return;
    try {
      const data = await api(
        `/admin/questions/${encodeURIComponent(state.question.id)}/rollback`,
        jsonRequest('POST', { version }),
      );
      fillForm(data.question);
      setStatus(`已回滚到 v${version}，当前为 v${data.question.version}`);
      await loadQuestions(data.question.id);
    } catch (error) {
      setStatus(`回滚失败：${error.message}`);
    }
  }

  async function initialize() {
    try {
      const auth = await api('/auth/me');
      state.user = auth.user;
      state.csrfToken = auth.csrf_token;
      document.getElementById('question-user').textContent =
        `${state.user.name} · ${state.user.role}`;
      document.getElementById('question-workspace').hidden = false;
      await loadKnowledgeNodes();
      await loadQuestions();
      fillForm(null);
    } catch (_) {
      document.getElementById('question-auth-required').hidden = false;
    }
  }

  document.getElementById('question-filter-form').addEventListener('submit', async event => {
    event.preventDefault();
    await loadQuestions();
  });
  document.getElementById('question-new').addEventListener('click', () => fillForm(null));
  document.getElementById('question-form').addEventListener('submit', saveQuestion);
  document.getElementById('question-form').addEventListener('input', renderPreview);
  document.getElementById('question-form').addEventListener('change', renderPreview);
  document.getElementById('question-submit').addEventListener('click', () => questionAction('submit'));
  document.getElementById('question-publish').addEventListener('click', () => questionAction('publish'));
  document.getElementById('question-archive').addEventListener('click', () => questionAction('archive'));

  initialize();
}());
