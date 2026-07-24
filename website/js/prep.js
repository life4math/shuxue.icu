(function () {
  'use strict';

  const API_ROOT = '/api/v1';
  const state = {
    csrfToken: '',
    user: null,
    courses: [],
    lectures: [],
    course: null,
    lecture: null,
    selectedSectionId: '',
    selectedBlockId: '',
    dirty: false,
    saving: false,
    saveTimer: null,
    stageSlides: [],
    stageIndex: 0,
    stageReveal: false,
    pickerItems: [],
  };

  const blockLabels = {
    text: '正文',
    math: 'KaTeX 公式',
    callout: '要点提示',
    example: '例题',
    question_ref: '题目引用',
    knowledge_ref: '知识点引用',
    image: '图片',
  };

  function create(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }

  function uid(prefix) {
    const token = window.crypto && window.crypto.randomUUID
      ? window.crypto.randomUUID().replaceAll('-', '')
      : `${Date.now()}${Math.random().toString(16).slice(2)}`;
    return `${prefix}_${token}`;
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

  function statusText(value) {
    return {
      draft: '草稿',
      pending_review: '待审核',
      published: '已发布',
    }[value] || value || '未选择';
  }

  function setAutosaveStatus(message) {
    document.getElementById('autosave-status').textContent = message || '';
  }

  function localDraftKey() {
    return state.lecture ? `shuxue-prep-draft:${state.lecture.id}` : '';
  }

  function storeLocalDraft() {
    if (!state.lecture) return;
    try {
      sessionStorage.setItem(localDraftKey(), JSON.stringify({
        version: state.lecture.version,
        title: state.lecture.title,
        summary: state.lecture.summary,
        payload: state.lecture.payload,
        saved_at: new Date().toISOString(),
      }));
    } catch (_) {
      setAutosaveStatus('浏览器备份不可用');
    }
  }

  function restoreLocalDraft() {
    if (!state.lecture) return false;
    try {
      const stored = JSON.parse(sessionStorage.getItem(localDraftKey()) || 'null');
      if (!stored || stored.version !== state.lecture.version || !stored.payload) return false;
      state.lecture.title = stored.title || state.lecture.title;
      state.lecture.summary = stored.summary || '';
      state.lecture.payload = stored.payload;
      state.dirty = true;
      setAutosaveStatus('已恢复本浏览器尚未提交的草稿');
      return true;
    } catch (_) {
      return false;
    }
  }

  function clearLocalDraft() {
    try {
      if (localDraftKey()) sessionStorage.removeItem(localDraftKey());
    } catch (_) {
      // 存储不可用不影响服务端保存
    }
  }

  function markDirty() {
    if (!state.lecture) return;
    state.dirty = true;
    setAutosaveStatus('有未保存修改');
    storeLocalDraft();
    window.clearTimeout(state.saveTimer);
    state.saveTimer = window.setTimeout(() => saveDraft(true), 3000);
    renderPreview();
    renderOutline();
  }

  function renderCourses() {
    const target = document.getElementById('course-list');
    target.replaceChildren();
    if (!state.courses.length) {
      target.append(create('p', 'prep-muted', '暂无课程，请先创建课程。'));
      return;
    }
    state.courses.forEach(course => {
      const button = create('button', 'prep-list-item');
      button.type = 'button';
      button.classList.toggle('selected', course.id === state.course?.id);
      button.append(
        create('strong', '', course.title),
        create(
          'span',
          'prep-item-meta',
          `${course.grade_label || '未设置年级'} · ${course.lecture_count || 0} 个课次 · ${course.status}`,
        ),
      );
      button.addEventListener('click', () => selectCourse(course.id));
      target.append(button);
    });
  }

  function fillCourseForm() {
    const form = document.getElementById('course-form');
    form.hidden = !state.course;
    document.getElementById('lecture-new').disabled = !state.course || state.course.status !== 'active';
    if (!state.course) return;
    document.getElementById('course-title').value = state.course.title;
    document.getElementById('course-grade').value = state.course.grade_label || '';
    document.getElementById('course-description').value = state.course.description || '';
    document.getElementById('course-archive').textContent =
      state.course.status === 'archived' ? '恢复课程' : '归档';
  }

  async function loadCourses(preferredId = '') {
    const data = await api('/admin/lecture-courses');
    state.courses = data.items || [];
    const targetId = preferredId || state.course?.id || state.courses[0]?.id || '';
    state.course = state.courses.find(item => item.id === targetId) || null;
    renderCourses();
    fillCourseForm();
    await loadLectures();
  }

  async function selectCourse(courseId) {
    if (state.dirty && !window.confirm('当前讲义有未保存修改，仍要切换课程吗？')) return;
    state.course = state.courses.find(item => item.id === courseId) || null;
    state.lecture = null;
    state.dirty = false;
    renderCourses();
    fillCourseForm();
    await loadLectures();
  }

  function renderLectures() {
    const target = document.getElementById('lecture-list');
    target.replaceChildren();
    if (!state.lectures.length) {
      target.append(create('p', 'prep-muted', state.course ? '该课程还没有课次。' : '请先选择课程。'));
      return;
    }
    state.lectures.forEach(lecture => {
      const button = create('button', 'prep-list-item');
      button.type = 'button';
      button.classList.toggle('selected', lecture.id === state.lecture?.id);
      button.append(
        create('strong', '', lecture.title),
        create('span', 'prep-item-meta', `${statusText(lecture.status)} · v${lecture.version}`),
      );
      button.addEventListener('click', () => selectLecture(lecture.id));
      target.append(button);
    });
  }

  async function loadLectures(preferredId = '') {
    if (!state.course) {
      state.lectures = [];
      state.lecture = null;
      renderLectures();
      renderWorkspace();
      return;
    }
    const data = await api(`/admin/lectures?course_id=${encodeURIComponent(state.course.id)}`);
    state.lectures = data.items || [];
    renderLectures();
    const targetId = preferredId || state.lecture?.id || state.lectures[0]?.id || '';
    if (targetId) await selectLecture(targetId, true);
    else {
      state.lecture = null;
      renderWorkspace();
    }
  }

  async function selectLecture(lectureId, skipDirtyCheck = false) {
    if (!skipDirtyCheck && state.dirty && !window.confirm('当前讲义有未保存修改，仍要切换课次吗？')) return;
    const data = await api(`/admin/lectures/${encodeURIComponent(lectureId)}`);
    state.lecture = data.lecture;
    state.course = state.courses.find(item => item.id === state.lecture.course_id) || state.course;
    state.selectedSectionId = state.lecture.payload.sections[0]?.id || '';
    state.selectedBlockId = '';
    state.dirty = false;
    restoreLocalDraft();
    renderCourses();
    renderLectures();
    renderWorkspace();
    await loadVersions();
  }

  function currentSection() {
    return state.lecture?.payload.sections.find(item => item.id === state.selectedSectionId) || null;
  }

  function currentBlock() {
    return currentSection()?.blocks.find(item => item.id === state.selectedBlockId) || null;
  }

  function renderOutline() {
    const target = document.getElementById('lecture-outline');
    target.replaceChildren();
    const sections = state.lecture?.payload.sections || [];
    if (!sections.length) {
      target.append(create('p', 'prep-muted', '暂无小节。'));
      return;
    }
    sections.forEach((section, sectionIndex) => {
      const sectionButton = create('button', 'prep-outline-item');
      sectionButton.type = 'button';
      sectionButton.classList.toggle(
        'selected',
        state.selectedSectionId === section.id && !state.selectedBlockId,
      );
      sectionButton.append(
        create('strong', '', `${String(sectionIndex + 1).padStart(2, '0')} · ${section.title}`),
        create('span', 'prep-item-meta', `${section.blocks.length} 个内容块`),
      );
      sectionButton.addEventListener('click', () => {
        state.selectedSectionId = section.id;
        state.selectedBlockId = '';
        renderOutline();
        renderBlockEditor();
      });
      target.append(sectionButton);
      section.blocks.forEach(block => {
        const blockButton = create('button', 'prep-outline-item prep-outline-block');
        blockButton.type = 'button';
        blockButton.classList.toggle('selected', state.selectedBlockId === block.id);
        blockButton.append(
          create('strong', '', blockLabels[block.type] || block.type),
          create('span', 'prep-item-meta', blockSummary(block)),
        );
        blockButton.addEventListener('click', () => {
          state.selectedSectionId = section.id;
          state.selectedBlockId = block.id;
          renderOutline();
          renderBlockEditor();
        });
        target.append(blockButton);
      });
    });
  }

  function blockSummary(block) {
    const value = block.text || block.latex || block.title || block.stem || block.node_id
      || block.question_id || block.caption || block.url || '未填写';
    return String(value).replace(/\s+/g, ' ').slice(0, 44);
  }

  function addField(target, labelText, value, update, options = {}) {
    const label = create('label', 'prep-field', labelText);
    const control = options.select ? document.createElement('select')
      : document.createElement(options.multiline ? 'textarea' : 'input');
    if (options.select) {
      options.select.forEach(item => control.add(new Option(item.label, item.value)));
    }
    if (options.multiline) control.rows = options.rows || 5;
    control.value = value || '';
    control.addEventListener(options.select ? 'change' : 'input', () => {
      update(control.value);
      markDirty();
    });
    label.append(control);
    target.append(label);
    return control;
  }

  function actionButton(label, handler, className = 'btn-ghost') {
    const button = create('button', className, label);
    button.type = 'button';
    button.addEventListener('click', handler);
    return button;
  }

  function moveSelected(offset) {
    const section = currentSection();
    if (!section) return;
    if (state.selectedBlockId) {
      const index = section.blocks.findIndex(item => item.id === state.selectedBlockId);
      const next = index + offset;
      if (index < 0 || next < 0 || next >= section.blocks.length) return;
      [section.blocks[index], section.blocks[next]] = [section.blocks[next], section.blocks[index]];
    } else {
      const sections = state.lecture.payload.sections;
      const index = sections.findIndex(item => item.id === section.id);
      const next = index + offset;
      if (index < 0 || next < 0 || next >= sections.length) return;
      [sections[index], sections[next]] = [sections[next], sections[index]];
      sections.forEach((item, itemIndex) => { item.sort_order = itemIndex; });
    }
    markDirty();
    renderBlockEditor();
  }

  function deleteSelected() {
    const section = currentSection();
    if (!section) return;
    if (state.selectedBlockId) {
      if (!window.confirm('确认删除这个内容块？')) return;
      section.blocks = section.blocks.filter(item => item.id !== state.selectedBlockId);
      state.selectedBlockId = '';
    } else {
      if (state.lecture.payload.sections.length === 1) {
        window.alert('讲义至少需要保留一个小节。');
        return;
      }
      if (!window.confirm(`确认删除小节“${section.title}”及其全部内容块？`)) return;
      state.lecture.payload.sections = state.lecture.payload.sections.filter(item => item.id !== section.id);
      state.selectedSectionId = state.lecture.payload.sections[0]?.id || '';
    }
    markDirty();
    renderBlockEditor();
  }

  function renderBlockEditor() {
    const target = document.getElementById('block-editor');
    target.replaceChildren();
    if (!state.lecture) {
      target.append(create('p', 'prep-muted', '请先选择课次。'));
      return;
    }
    const section = currentSection();
    if (!section) {
      target.append(create('p', 'prep-muted', '请先添加小节。'));
      return;
    }
    const block = currentBlock();
    target.append(create('h3', '', block ? `编辑${blockLabels[block.type] || '内容块'}` : '编辑小节'));
    if (!block) {
      addField(target, '小节标题', section.title, value => { section.title = value; });
    } else if (block.type === 'text') {
      addField(target, '正文', block.text, value => { block.text = value; }, { multiline: true, rows: 10 });
    } else if (block.type === 'math') {
      addField(target, 'KaTeX 代码', block.latex, value => { block.latex = value; }, { multiline: true, rows: 7 });
      addField(target, '公式说明', block.caption, value => { block.caption = value; });
    } else if (block.type === 'callout') {
      addField(target, '标题', block.title, value => { block.title = value; });
      addField(target, '类型', block.tone, value => { block.tone = value; }, {
        select: [
          { value: 'note', label: '说明' },
          { value: 'key', label: '重点' },
          { value: 'warning', label: '易错提醒' },
        ],
      });
      addField(target, '内容', block.text, value => { block.text = value; }, { multiline: true, rows: 8 });
    } else if (block.type === 'example') {
      addField(target, '例题标题', block.title, value => { block.title = value; });
      addField(target, '题干', block.stem, value => { block.stem = value; }, { multiline: true, rows: 7 });
      addField(target, '解答', block.answer, value => { block.answer = value; }, { multiline: true, rows: 8 });
    } else if (block.type === 'question_ref') {
      addField(target, '题目编号', block.question_id, value => { block.question_id = value; });
      addField(target, '稳定代码', block.code, value => { block.code = value; });
      addField(target, '显示标题', block.title, value => { block.title = value; });
      addField(target, '题干快照', block.stem, value => { block.stem = value; }, { multiline: true, rows: 8 });
      addField(
        target,
        '选项快照（JSON）',
        JSON.stringify(block.options || [], null, 2),
        value => {
          try {
            block.options = JSON.parse(value);
          } catch (_) {
            setAutosaveStatus('选项 JSON 尚未完成');
          }
        },
        { multiline: true, rows: 6 },
      );
      addField(target, '答案快照', block.answer, value => { block.answer = value; }, { multiline: true, rows: 5 });
      addField(target, '解析快照', block.analysis, value => { block.analysis = value; }, { multiline: true, rows: 7 });
    } else if (block.type === 'knowledge_ref') {
      addField(target, '知识点 ID 或代码', block.node_id, value => { block.node_id = value; });
      addField(target, '显示标题', block.title, value => { block.title = value; });
      addField(target, '备课说明', block.note, value => { block.note = value; }, { multiline: true, rows: 6 });
    } else if (block.type === 'image') {
      addField(target, 'HTTPS 或站内图片地址', block.url, value => { block.url = value; });
      addField(target, '替代文字', block.alt, value => { block.alt = value; });
      addField(target, '图片说明', block.caption, value => { block.caption = value; });
    }
    const actions = create('div', 'prep-editor-actions');
    actions.append(
      actionButton('上移', () => moveSelected(-1)),
      actionButton('下移', () => moveSelected(1)),
      actionButton('删除', deleteSelected),
    );
    target.append(actions);
  }

  function renderPreview() {
    const courseLabel = state.course
      ? `${state.course.title}${state.course.grade_label ? ` · ${state.course.grade_label}` : ''}`
      : 'COURSE';
    document.getElementById('preview-course').textContent = courseLabel;
    document.getElementById('preview-title').textContent = state.lecture?.title || '讲义预览';
    document.getElementById('preview-summary').textContent = state.lecture?.summary || '';
    window.LectureRenderer.renderDocument(
      document.getElementById('lecture-preview'),
      state.lecture?.payload || { sections: [] },
      { revealAnswers: true, showEmpty: true },
    );
  }

  function updateLectureControls() {
    const exists = !!state.lecture;
    document.getElementById('lecture-save').disabled = !exists;
    document.getElementById('lecture-submit').disabled = !exists || state.lecture.status !== 'draft';
    document.getElementById('lecture-publish').disabled = !exists;
    document.getElementById('lecture-unpublish').disabled = !exists || state.lecture.status !== 'published';
    document.getElementById('section-new').disabled = !exists;
    document.getElementById('block-add').disabled = !exists;
    document.getElementById('question-pick').disabled = !exists;
    document.getElementById('lecture-rehearse').disabled = !exists;
    document.getElementById('lecture-status-badge').textContent =
      exists ? `${statusText(state.lecture.status)} · v${state.lecture.version}` : '未选择课次';
  }

  function renderWorkspace() {
    const exists = !!state.lecture;
    document.getElementById('lecture-empty').hidden = exists;
    document.getElementById('lecture-form').hidden = !exists;
    if (exists) {
      document.getElementById('lecture-title-input').value = state.lecture.title;
      document.getElementById('lecture-summary-input').value = state.lecture.summary || '';
      document.getElementById('lecture-slug').textContent =
        `https://shuxue.icu/lecture.html?id=${state.lecture.slug}`;
    } else {
      setAutosaveStatus('');
    }
    updateLectureControls();
    renderOutline();
    renderBlockEditor();
    renderPreview();
    if (!exists) document.getElementById('lecture-versions').replaceChildren();
  }

  async function saveDraft(automatic = false) {
    if (!state.lecture || !state.dirty || state.saving) return !state.dirty;
    state.saving = true;
    setAutosaveStatus(automatic ? '正在自动保存…' : '正在保存…');
    try {
      const data = await api(
        `/admin/lectures/${encodeURIComponent(state.lecture.id)}/draft`,
        jsonRequest('PUT', {
          version: state.lecture.version,
          title: state.lecture.title,
          summary: state.lecture.summary,
          sort_order: state.lecture.sort_order,
          payload: state.lecture.payload,
        }),
      );
      state.lecture = data.lecture;
      state.dirty = false;
      clearLocalDraft();
      setAutosaveStatus(`已保存 · ${new Date().toLocaleTimeString()}`);
      updateLectureControls();
      renderLectures();
      await loadVersions();
      return true;
    } catch (error) {
      if (error.status === 409 && error.data?.current_version) {
        setAutosaveStatus(`版本冲突：服务器已是 v${error.data.current_version}，请刷新后合并`);
      } else {
        setAutosaveStatus(`保存失败：${error.message}；草稿仍保存在本浏览器`);
      }
      storeLocalDraft();
      return false;
    } finally {
      state.saving = false;
    }
  }

  async function lectureAction(action) {
    if (!state.lecture) return;
    if (state.dirty && !(await saveDraft(false))) return;
    try {
      const data = await api(
        `/admin/lectures/${encodeURIComponent(state.lecture.id)}/${action}`,
        jsonRequest('POST', {}),
      );
      state.lecture = data.lecture;
      setAutosaveStatus(
        action === 'submit' ? '已提交审核'
          : action === 'publish' ? '已发布到公开讲义'
            : '已从公开网站撤下',
      );
      updateLectureControls();
      renderLectures();
    } catch (error) {
      setAutosaveStatus(`操作失败：${error.message}`);
    }
  }

  async function loadVersions() {
    const target = document.getElementById('lecture-versions');
    target.replaceChildren();
    if (!state.lecture) return;
    try {
      const data = await api(`/admin/lectures/${encodeURIComponent(state.lecture.id)}/versions`);
      (data.items || []).slice(0, 12).forEach(item => {
        const row = create('div', 'prep-version-item');
        row.append(create('span', '', `v${item.version} · ${item.change_reason}`));
        if (item.version !== state.lecture.version) {
          row.append(actionButton('回滚', () => rollbackVersion(item.version)));
        }
        target.append(row);
      });
    } catch (error) {
      target.append(create('p', 'prep-muted', error.message));
    }
  }

  async function rollbackVersion(version) {
    if (!state.lecture || !window.confirm(`确认以版本 v${version} 的内容创建一个新草稿？`)) return;
    if (state.dirty && !window.confirm('当前未保存修改会被浏览器备份，但不会进入回滚后的版本。继续吗？')) return;
    try {
      const data = await api(
        `/admin/lectures/${encodeURIComponent(state.lecture.id)}/rollback`,
        jsonRequest('POST', { version }),
      );
      state.lecture = data.lecture;
      state.dirty = false;
      clearLocalDraft();
      state.selectedSectionId = state.lecture.payload.sections[0]?.id || '';
      state.selectedBlockId = '';
      setAutosaveStatus(`已回滚 v${version}，并生成 v${state.lecture.version}`);
      renderWorkspace();
      await loadVersions();
    } catch (error) {
      setAutosaveStatus(`回滚失败：${error.message}`);
    }
  }

  function defaultBlock(type) {
    const block = { id: uid('blk'), type };
    if (type === 'text') block.text = '在这里输入讲解正文。';
    if (type === 'math') Object.assign(block, { latex: 'f(x)=ax^2+bx+c', caption: '' });
    if (type === 'callout') Object.assign(block, { title: '核心要点', text: '', tone: 'key' });
    if (type === 'example') Object.assign(block, { title: '例题', stem: '', answer: '' });
    if (type === 'question_ref') Object.assign(block, {
      question_id: '',
      code: '',
      title: '题目引用',
      stem: '',
      options: [],
      answer: '',
      analysis: '',
      question_type: 'solve',
      difficulty: 3,
    });
    if (type === 'knowledge_ref') Object.assign(block, { node_id: '', title: '', note: '' });
    if (type === 'image') Object.assign(block, { url: '', alt: '', caption: '' });
    return block;
  }

  function addSection() {
    if (!state.lecture) return;
    const title = window.prompt('小节标题', `第 ${state.lecture.payload.sections.length + 1} 部分`);
    if (!title?.trim()) return;
    const section = {
      id: uid('sec'),
      title: title.trim(),
      sort_order: state.lecture.payload.sections.length,
      blocks: [],
    };
    state.lecture.payload.sections.push(section);
    state.selectedSectionId = section.id;
    state.selectedBlockId = '';
    markDirty();
    renderBlockEditor();
  }

  function addBlock() {
    if (!state.lecture) return;
    let section = currentSection();
    if (!section) {
      section = state.lecture.payload.sections[0];
      if (!section) return;
      state.selectedSectionId = section.id;
    }
    const block = defaultBlock(document.getElementById('block-type').value);
    section.blocks.push(block);
    state.selectedBlockId = block.id;
    markDirty();
    renderBlockEditor();
  }

  function pickerQueryString() {
    const params = new URLSearchParams();
    const values = {
      query: document.getElementById('question-picker-query').value.trim(),
      module: document.getElementById('question-picker-module').value,
      question_type: document.getElementById('question-picker-type').value,
      difficulty: document.getElementById('question-picker-difficulty').value,
    };
    Object.entries(values).forEach(([key, value]) => {
      if (value) params.set(key, value);
    });
    params.set('limit', '60');
    return params.toString();
  }

  function renderQuestionPicker() {
    const target = document.getElementById('question-picker-results');
    target.replaceChildren();
    if (!state.pickerItems.length) {
      target.append(create('p', 'prep-muted', '没有找到已发布题目。请先在正式题库中创建并发布题目。'));
      return;
    }
    state.pickerItems.forEach(question => {
      const card = create('article', 'question-picker-item');
      card.append(
        create('h3', '', `${question.code} · ${question.stem.slice(0, 52)}`),
        create(
          'p',
          'question-picker-item-meta',
          `${question.module} · ${question.question_type} · 难度 ${question.difficulty} · v${question.version}`,
        ),
        create('p', '', question.stem.slice(0, 180)),
      );
      const button = actionButton('插入当前小节', () => insertQuestion(question), 'btn-accent');
      card.append(button);
      target.append(card);
    });
  }

  async function loadQuestionPicker() {
    const status = document.getElementById('question-picker-status');
    status.textContent = '正在读取已发布题目…';
    try {
      const data = await api(`/admin/question-picker?${pickerQueryString()}`);
      state.pickerItems = data.items || [];
      status.textContent = `共找到 ${state.pickerItems.length} 道题`;
      renderQuestionPicker();
    } catch (error) {
      state.pickerItems = [];
      status.textContent = `读取失败：${error.message}`;
      renderQuestionPicker();
    }
  }

  async function openQuestionPicker() {
    if (!state.lecture) return;
    const dialog = document.getElementById('question-picker-dialog');
    if (typeof dialog.showModal === 'function') dialog.showModal();
    else dialog.setAttribute('open', '');
    await loadQuestionPicker();
  }

  function closeQuestionPicker() {
    const dialog = document.getElementById('question-picker-dialog');
    if (typeof dialog.close === 'function') dialog.close();
    else dialog.removeAttribute('open');
  }

  function insertQuestion(question) {
    let section = currentSection();
    if (!section) section = state.lecture?.payload.sections[0];
    if (!section) return;
    state.selectedSectionId = section.id;
    const block = {
      id: uid('blk'),
      type: 'question_ref',
      question_id: question.id,
      code: question.code,
      title: question.code,
      stem: question.stem,
      options: question.options || [],
      answer: question.answer || '',
      analysis: question.analysis || '',
      question_type: question.question_type,
      difficulty: question.difficulty,
    };
    section.blocks.push(block);
    state.selectedBlockId = block.id;
    closeQuestionPicker();
    markDirty();
    renderBlockEditor();
    setAutosaveStatus(`已插入正式题目 ${question.code}，发布讲义时会冻结当前题目版本`);
  }

  function renderStage() {
    const target = document.getElementById('prep-stage-content');
    target.replaceChildren();
    if (!state.stageSlides.length) {
      target.append(create('p', 'prep-muted', '讲义没有可演示内容。'));
      return;
    }
    state.stageIndex = Math.max(0, Math.min(state.stageIndex, state.stageSlides.length - 1));
    const slide = state.stageSlides[state.stageIndex];
    target.append(create('h2', '', slide.section.title));
    if (slide.block) {
      target.append(window.LectureRenderer.renderBlock(slide.block, {
        revealAnswers: state.stageReveal,
        linkKnowledge: false,
      }));
    }
    document.getElementById('prep-stage-title').textContent = state.lecture.title;
    document.getElementById('prep-stage-progress').textContent =
      `${state.stageIndex + 1} / ${state.stageSlides.length}`;
    document.getElementById('prep-stage-prev').disabled = state.stageIndex === 0;
    document.getElementById('prep-stage-next').disabled =
      state.stageIndex === state.stageSlides.length - 1;
    document.getElementById('prep-stage-reveal').hidden =
      !slide.block || !['example', 'question_ref'].includes(slide.block.type);
  }

  function moveStage(offset) {
    state.stageIndex += offset;
    state.stageReveal = false;
    renderStage();
  }

  function openStage() {
    if (!state.lecture) return;
    state.stageSlides = window.LectureRenderer.flatten(state.lecture.payload);
    state.stageIndex = 0;
    state.stageReveal = false;
    document.getElementById('prep-stage').hidden = false;
    document.body.style.overflow = 'hidden';
    renderStage();
  }

  function closeStage() {
    document.getElementById('prep-stage').hidden = true;
    document.body.style.overflow = '';
  }

  async function initialize() {
    try {
      const auth = await api('/auth/me');
      state.user = auth.user;
      state.csrfToken = auth.csrf_token;
      document.getElementById('prep-user').textContent = `${state.user.name} · ${state.user.role}`;
      document.getElementById('prep-workspace').hidden = false;
      await loadCourses();
    } catch (_) {
      document.getElementById('prep-auth-required').hidden = false;
    }
  }

  document.getElementById('course-new').addEventListener('click', async () => {
    const title = window.prompt('课程名称', '高考数学专题课');
    if (!title?.trim()) return;
    try {
      const data = await api('/admin/lecture-courses', jsonRequest('POST', { title: title.trim() }));
      await loadCourses(data.course.id);
    } catch (error) {
      window.alert(error.message);
    }
  });

  document.getElementById('course-form').addEventListener('submit', async event => {
    event.preventDefault();
    if (!state.course) return;
    try {
      const data = await api(
        `/admin/lecture-courses/${encodeURIComponent(state.course.id)}`,
        jsonRequest('PATCH', {
          title: document.getElementById('course-title').value.trim(),
          grade_label: document.getElementById('course-grade').value.trim(),
          description: document.getElementById('course-description').value.trim(),
        }),
      );
      await loadCourses(data.course.id);
    } catch (error) {
      window.alert(error.message);
    }
  });

  document.getElementById('course-archive').addEventListener('click', async () => {
    if (!state.course) return;
    const status = state.course.status === 'archived' ? 'active' : 'archived';
    if (status === 'archived' && !window.confirm('归档后不能新增课次，已发布讲义仍可公开阅读。继续吗？')) return;
    try {
      const data = await api(
        `/admin/lecture-courses/${encodeURIComponent(state.course.id)}`,
        jsonRequest('PATCH', { status }),
      );
      await loadCourses(data.course.id);
    } catch (error) {
      window.alert(error.message);
    }
  });

  document.getElementById('lecture-new').addEventListener('click', async () => {
    if (!state.course) return;
    const title = window.prompt('课次标题', '新课讲义');
    if (!title?.trim()) return;
    try {
      const data = await api('/admin/lectures', jsonRequest('POST', {
        course_id: state.course.id,
        title: title.trim(),
      }));
      await loadCourses(state.course.id);
      await loadLectures(data.lecture.id);
    } catch (error) {
      window.alert(error.message);
    }
  });

  document.getElementById('lecture-title-input').addEventListener('input', event => {
    if (!state.lecture) return;
    state.lecture.title = event.target.value;
    markDirty();
  });
  document.getElementById('lecture-summary-input').addEventListener('input', event => {
    if (!state.lecture) return;
    state.lecture.summary = event.target.value;
    markDirty();
  });
  document.getElementById('section-new').addEventListener('click', addSection);
  document.getElementById('block-add').addEventListener('click', addBlock);
  document.getElementById('question-pick').addEventListener('click', openQuestionPicker);
  document.getElementById('question-picker-close').addEventListener('click', closeQuestionPicker);
  document.getElementById('question-picker-form').addEventListener('submit', event => {
    event.preventDefault();
    loadQuestionPicker();
  });
  document.getElementById('lecture-save').addEventListener('click', () => saveDraft(false));
  document.getElementById('lecture-submit').addEventListener('click', () => lectureAction('submit'));
  document.getElementById('lecture-publish').addEventListener('click', () => lectureAction('publish'));
  document.getElementById('lecture-unpublish').addEventListener('click', () => lectureAction('unpublish'));
  document.getElementById('lecture-rehearse').addEventListener('click', openStage);
  document.getElementById('prep-stage-close').addEventListener('click', closeStage);
  document.getElementById('prep-stage-prev').addEventListener('click', () => moveStage(-1));
  document.getElementById('prep-stage-next').addEventListener('click', () => moveStage(1));
  document.getElementById('prep-stage-reveal').addEventListener('click', () => {
    state.stageReveal = !state.stageReveal;
    renderStage();
  });
  document.addEventListener('keydown', event => {
    if (document.getElementById('prep-stage').hidden) return;
    if (event.key === 'Escape') closeStage();
    if (event.key === 'ArrowLeft') moveStage(-1);
    if (event.key === 'ArrowRight' || event.key === ' ') {
      event.preventDefault();
      moveStage(1);
    }
  });
  window.addEventListener('beforeunload', event => {
    if (!state.dirty) return;
    event.preventDefault();
    event.returnValue = '';
  });
  window.setInterval(() => {
    if (state.dirty) saveDraft(true);
  }, 30000);

  initialize();
}());
