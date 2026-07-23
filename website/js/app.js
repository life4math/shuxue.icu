// ===== shuxue.icu — 主应用逻辑（4栏目架构） =====

let currentStudent = students[0];
let charts = {};

// ===== 主页面导航 =====
document.querySelectorAll('.nav-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    const page = tab.dataset.page;
    // 切换 tab 激活态
    document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    // 切换页面
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById('page-' + page).classList.add('active');
    // 初始化页面
    initPage(page);
  });
});

// ===== 子导航切换 =====
document.querySelectorAll('.sub-nav-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const parentPage = btn.closest('.sub-nav').id;
    const sub = btn.dataset.sub;
    // 切换子导航激活态
    btn.closest('.sub-nav').querySelectorAll('.sub-nav-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    // 切换子页面
    btn.closest('.page').querySelectorAll('.sub-page').forEach(sp => sp.classList.remove('active'));
    document.getElementById('sub-' + sub).classList.add('active');
    // 初始化子页面
    initSubPage(parentPage, sub);
  });
});

function initPage(page) {
  switch (page) {
    case 'learning': initLearning(); break;
    case 'analytics': initAnalytics(); break;
    case 'dashboard': initDashboard(); break;
    case 'pricing': initPricing(); break;
    case 'about': initAbout(); break;
  }
}

function initSubPage(parentNavId, sub) {
  if (parentNavId === 'learning-subnav') {
    switch (sub) {
      case 'questions': initQuestions(); break;
      case 'knowledge': initKnowledge(); break;
      case 'methods': initMethods(); break;
    }
  } else if (parentNavId === 'about-subnav') {
    switch (sub) {
      case 'blog': initBlog(); break;
      case 'aboutinfo': initAboutInfo(); break;
    }
  }
}

// ===== 学习方案 =====
function initLearning() {
  // 默认显示题库子页
  initQuestions();
}

// ===== 题库管理 =====
function initQuestions() {
  renderQuestionList(questions);
  // 绑定筛选事件（避免重复绑定）
  if (!window._questionsBound) {
    ['filter-module', 'filter-difficulty', 'filter-type'].forEach(id => {
      document.getElementById(id).addEventListener('change', filterQuestions);
    });
    document.getElementById('filter-keyword').addEventListener('input', debounce(filterQuestions, 300));
    window._questionsBound = true;
  }
}

function filterQuestions() {
  const module = document.getElementById('filter-module').value;
  const difficulty = document.getElementById('filter-difficulty').value;
  const type = document.getElementById('filter-type').value;
  const keyword = document.getElementById('filter-keyword').value.toLowerCase();

  const filtered = questions.filter(q => {
    if (module && q.module !== module) return false;
    if (difficulty && q.difficulty !== parseInt(difficulty)) return false;
    if (type && q.type !== type) return false;
    if (keyword && !q.stem.toLowerCase().includes(keyword) && !q.tags.some(t => t.toLowerCase().includes(keyword))) return false;
    return true;
  });

  renderQuestionList(filtered);
}

function renderQuestionList(list) {
  document.getElementById('q-total').textContent = questions.length;
  document.getElementById('q-filtered').textContent = list.length;

  const container = document.getElementById('question-list');
  container.innerHTML = list.map(q => `
    <div class="question-card" onclick="showQuestionDetail('${q.id}')">
      <div class="question-header">
        <span class="question-id">${q.id}</span>
        <span class="question-module">${getModuleName(q.module)}</span>
        <span class="question-type">${getTypeLabel(q.type)}</span>
        <div class="question-difficulty">${renderLevel(q.difficulty)}</div>
        <span class="question-accuracy">ACC ${q.stats.accuracy}%</span>
      </div>
      <div class="question-stem">${renderMath(q.stem)}</div>
      <div class="question-tags">
        ${q.tags.map(t => `<span class="question-tag">${t}</span>`).join('')}
        ${q.source ? `<span class="question-tag">${q.source.type} ${q.source.year || ''}</span>` : ''}
      </div>
      <div class="question-stats-row">
        <span class="q-stat">ATT <span class="q-stat-value">${q.stats.total}</span></span>
        <span class="q-stat">OK <span class="q-stat-value">${q.stats.correct}</span></span>
        <span class="q-stat">ACC <span class="q-stat-value">${q.stats.accuracy}%</span></span>
      </div>
    </div>
  `).join('');

  // 重新渲染 KaTeX
  renderKaTeX(container);
}

function renderLevel(difficulty) {
  let blocks = '';
  for (let i = 1; i <= 5; i++) {
    blocks += i <= difficulty ? '<span>■</span>' : '<span class="empty">□</span>';
  }
  return `<span class="lv">LV.${difficulty}</span> <span class="blocks">${blocks}</span>`;
}

function renderMath(text) {
  return text.replace(/\$([^$]+)\$/g, (match, tex) => {
    try {
      return katex.renderToString(tex, { throwOnError: false });
    } catch (e) {
      return match;
    }
  });
}

function renderKaTeX(container) {
  container.querySelectorAll('.katex').forEach(el => {
    // KaTeX 已自动渲染
  });
}

function showQuestionDetail(id) {
  const q = questions.find(q => q.id === id);
  if (!q) return;

  document.getElementById('modal-title').textContent = `题目详情 - ${q.id}`;
  document.getElementById('modal-body').innerHTML = `
    <div class="detail-section">
      <div class="detail-label">基本信息</div>
      <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:12px">
        <span class="question-module">${getModuleName(q.module)}</span>
        <span class="question-type">${getTypeLabel(q.type)}</span>
        <span class="question-tag">难度: ${getDifficultyLabel(q.difficulty)}</span>
        <span class="question-tag">${q.source ? q.source.type + ' ' + (q.source.year || '') : ''}</span>
      </div>
    </div>
    <div class="detail-section">
      <div class="detail-label">题干</div>
      <div class="detail-content">${renderMath(q.stem)}</div>
    </div>
    ${q.options ? `
    <div class="detail-section">
      <div class="detail-label">选项</div>
      <div class="options-list">
        ${q.options.map(o => `
          <div class="option-item">
            <span class="option-label">${o.label}</span>
            <span>${renderMath(o.content)}</span>
          </div>
        `).join('')}
      </div>
    </div>` : ''}
    <div class="detail-section">
      <div class="detail-label">参考答案</div>
      <div class="answer-box">${renderMath(q.answer)}</div>
    </div>
    ${q.analysis ? `
    <div class="detail-section">
      <div class="detail-label">解题分析</div>
      <div class="analysis-box">${renderMath(q.analysis)}</div>
    </div>` : ''}
    <div class="detail-section">
      <div class="detail-label">知识点关联</div>
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        ${q.knowledge_points.map(kp => `<span class="question-tag">${kp}</span>`).join('')}
      </div>
    </div>
    <div class="detail-section">
      <div class="detail-label">作答统计</div>
      <div style="display:flex;gap:24px">
        <span>总作答: <strong>${q.stats.total}</strong></span>
        <span>正确: <strong>${q.stats.correct}</strong></span>
        <span>正确率: <strong>${q.stats.accuracy}%</strong></span>
      </div>
    </div>
  `;

  document.getElementById('question-modal').classList.add('active');
}

function closeModal() {
  document.getElementById('question-modal').classList.remove('active');
}

// 点击遮罩关闭弹窗
document.getElementById('question-modal').addEventListener('click', (e) => {
  if (e.target === e.currentTarget) closeModal();
});

// ===== 知识点体系 =====
function initKnowledge() {
  renderKnowledgeTree();
}

function renderKnowledgeTree() {
  const container = document.getElementById('knowledge-tree');
  container.innerHTML = knowledgeTree.map(module => renderTreeNode(module, 0)).join('');
  bindTreeEvents();
}

function renderTreeNode(node, depth) {
  const hasChildren = node.children && node.children.length > 0;
  const isExpanded = node.expanded !== false;
  const kpCount = countKnowledgePoints(node);

  let html = `<div class="tree-node" data-id="${node.id}">
    <div class="tree-node-content" data-id="${node.id}" style="padding-left:${depth * 8 + 8}px">
      ${hasChildren ? `<span class="tree-toggle">${isExpanded ? '[-]' : '[+]'}</span>` : '<span class="tree-toggle"></span>'}
      <span class="tree-label">${node.name}</span>
      ${node.examFrequency ? `<span class="tree-badge ${node.examFrequency}">${node.examFrequency === 'high' ? 'HOT' : node.examFrequency === 'medium' ? 'MID' : 'LOW'}</span>` : ''}
      ${hasChildren ? `<span class="tree-badge">${kpCount}个知识点</span>` : ''}
      ${node.difficulty ? `<span class="tree-badge">Lv.${node.difficulty[0]}-${node.difficulty[1]}</span>` : ''}
    </div>`;

  if (hasChildren) {
    html += `<div class="tree-children ${isExpanded ? '' : 'collapsed'}">`;
    html += node.children.map(child => renderTreeNode(child, depth + 1)).join('');
    html += '</div>';
  }

  html += '</div>';
  return html;
}

function countKnowledgePoints(node) {
  if (!node.children) return 1;
  return node.children.reduce((sum, child) => sum + countKnowledgePoints(child), 0);
}

function bindTreeEvents() {
  // 展开/收起
  document.querySelectorAll('.tree-toggle').forEach(el => {
    el.addEventListener('click', (e) => {
      e.stopPropagation();
      const children = el.closest('.tree-node').querySelector('.tree-children');
      if (children) {
        children.classList.toggle('collapsed');
        el.textContent = children.classList.contains('collapsed') ? '[+]' : '[-]';
      }
    });
  });

  // 选中知识点
  document.querySelectorAll('.tree-node-content').forEach(el => {
    el.addEventListener('click', () => {
      document.querySelectorAll('.tree-node-content').forEach(n => n.classList.remove('selected'));
      el.classList.add('selected');
      showKnowledgeDetail(el.dataset.id);
    });
  });
}

function expandAll() {
  document.querySelectorAll('.tree-children').forEach(el => el.classList.remove('collapsed'));
  document.querySelectorAll('.tree-toggle').forEach(el => {
    if (el.closest('.tree-node').querySelector('.tree-children')) el.textContent = '[-]';
  });
}

function collapseAll() {
  document.querySelectorAll('.tree-children').forEach(el => el.classList.add('collapsed'));
  document.querySelectorAll('.tree-toggle').forEach(el => {
    if (el.closest('.tree-node').querySelector('.tree-children')) el.textContent = '[+]';
  });
}

function findKnowledgeNode(id, tree) {
  for (const node of tree) {
    if (node.id === id) return node;
    if (node.children) {
      const found = findKnowledgeNode(id, node.children);
      if (found) return found;
    }
  }
  return null;
}

function showKnowledgeDetail(id) {
  const node = findKnowledgeNode(id, knowledgeTree);
  if (!node) return;

  const panel = document.getElementById('knowledge-detail');
  const relatedQuestions = questions.filter(q => q.knowledge_points.some(kp => kp.startsWith(id)));

  panel.innerHTML = `
    <div class="detail-section">
      <h4>INFO ·</h4>
      <div class="detail-info-grid">
        <div class="detail-info-item">
          <div class="detail-info-label">知识点ID</div>
          <div class="detail-info-value">${node.id}</div>
        </div>
        <div class="detail-info-item">
          <div class="detail-info-label">层级</div>
          <div class="detail-info-value">${['', '模块', '章', '节', '知识点', '子知识点'][node.level] || node.level}</div>
        </div>
        <div class="detail-info-item">
          <div class="detail-info-label">考试频率</div>
          <div class="detail-info-value">${node.examFrequency === 'high' ? '高频考点' : node.examFrequency === 'medium' ? '中频考点' : node.examFrequency === 'low' ? '低频考点' : '-'}</div>
        </div>
        <div class="detail-info-item">
          <div class="detail-info-label">难度区间</div>
          <div class="detail-info-value">${node.difficulty ? 'Lv.' + node.difficulty[0] + ' - Lv.' + node.difficulty[1] : '-'}</div>
        </div>
        <div class="detail-info-item">
          <div class="detail-info-label">关联题目</div>
          <div class="detail-info-value">${relatedQuestions.length} 道</div>
        </div>
        <div class="detail-info-item">
          <div class="detail-info-label">子知识点</div>
          <div class="detail-info-value">${node.children ? node.children.length : 0} 个</div>
        </div>
      </div>
    </div>
    ${node.children ? `
    <div class="detail-section">
      <h4>CHILDREN ·</h4>
      <div class="kp-children-list">
        ${node.children.map(child => `
          <div class="kp-child-item">
            <span class="kp-child-level">Lv.${child.level}</span>
            <span>${child.name}</span>
            ${child.examFrequency ? `<span class="tree-badge ${child.examFrequency}" style="margin-left:auto">${child.examFrequency === 'high' ? 'HOT' : child.examFrequency === 'medium' ? 'MID' : 'LOW'}</span>` : ''}
          </div>
        `).join('')}
      </div>
    </div>` : ''}
    ${relatedQuestions.length > 0 ? `
    <div class="detail-section">
      <h4>RELATED ·</h4>
      <div class="kp-children-list">
        ${relatedQuestions.map(q => `
          <div class="kp-child-item" style="cursor:pointer" onclick="showQuestionDetail('${q.id}')">
            <span class="kp-child-level">${q.id}</span>
            <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${q.stem.substring(0, 40)}...</span>
            <span class="tree-badge">${getDifficultyLabel(q.difficulty)}</span>
          </div>
        `).join('')}
      </div>
    </div>` : ''}
  `;
}

// ===== 方法库 =====
let currentMethod = null;

function initMethods() {
  animateNumber('stat-methods-total', methods.length);
  const moduleSet = new Set(methods.map(m => m.module));
  animateNumber('stat-methods-modules', moduleSet.size);
  const linked = methods.reduce((s, m) => s + (m.examples ? m.examples.length : 0), 0);
  animateNumber('stat-methods-linked', linked);

  renderMethodsList();
}

function renderMethodsList() {
  const container = document.getElementById('methods-list');
  container.innerHTML = methods.map(m => {
    const linkedCount = m.examples ? m.examples.length : 0;
    return '<div class="method-item" data-id="' + m.id + '" onclick="showMethodDetail(\'' + m.id + '\')">' +
      '<div class="method-item-left">' +
        '<span class="method-id">' + m.id + '</span>' +
        '<span class="method-name">' + m.name + '</span>' +
      '</div>' +
      '<div class="method-item-center">' +
        '<span class="method-category">[CATEGORY] ' + m.category + '</span>' +
        '<span class="method-module">' + getModuleName(m.module) + '</span>' +
      '</div>' +
      '<div class="method-item-right">' +
        '<span class="method-linked">LINKED · ' + linkedCount + '</span>' +
        '<span class="method-difficulty">LV.' + m.difficulty_range[0] + '-' + m.difficulty_range[1] + '</span>' +
      '</div>' +
    '</div>';
  }).join('');
}

function showMethodDetail(methodId) {
  const method = methods.find(m => m.id === methodId);
  if (!method) return;
  currentMethod = method;

  const card = document.getElementById('method-detail-card');
  card.style.display = 'block';
  document.getElementById('method-detail-title').textContent = method.id + ' · ' + method.name;

  const content = document.getElementById('method-detail-content');
  content.innerHTML = renderMethodDetailContent(method);
  renderLatexInElement(content);
}

// ===== 学情分析 =====
function initAnalytics() {
  renderStudentCards();
  selectStudent(students[0].id);
}

function renderStudentCards() {
  const container = document.getElementById('student-cards');
  container.innerHTML = students.map(s => `
    <div class="student-card ${s.id === currentStudent.id ? 'selected' : ''}" data-id="${s.id}" onclick="selectStudent('${s.id}')">
      <div class="student-avatar">${s.name.charAt(0)}</div>
      <div class="student-name">${s.name}</div>
      <div class="student-class">${s.class}</div>
      <div class="student-quick-stats">
        <div class="student-quick-stat">
          <div class="value" style="color:${getLevelColor(s.moduleScores.every(m => m.level === 'mastered') ? 'mastered' : s.moduleScores.some(m => m.level === 'unmastered') ? 'unmastered' : 'partial')}">${s.accuracy}%</div>
          <div class="label">正确率</div>
        </div>
        <div class="student-quick-stat">
          <div class="value">${s.totalQuestions}</div>
          <div class="label">答题数</div>
        </div>
        <div class="student-quick-stat">
          <div class="value">${s.coveredPoints}</div>
          <div class="label">覆盖知识点</div>
        </div>
      </div>
    </div>
  `).join('');
}

function selectStudent(id) {
  currentStudent = students.find(s => s.id === id);
  document.querySelectorAll('.student-card').forEach(c => c.classList.toggle('selected', c.dataset.id === id));
  renderStudentDetail();
}

function renderStudentDetail() {
  const s = currentStudent;

  // 统计指标
  document.getElementById('student-stats').innerHTML = `
    <div class="stat-card">
      <div class="stat-info">
        <span class="stat-label">TOTAL ANSWERED</span>
        <span class="stat-value">${s.totalQuestions}</span>
      </div>
    </div>
    <div class="stat-card">
      <div class="stat-info">
        <span class="stat-label">ACCURACY</span>
        <span class="stat-value">${s.accuracy}%</span>
      </div>
    </div>
    <div class="stat-card">
      <div class="stat-info">
        <span class="stat-label">AVG TIME</span>
        <span class="stat-value">${s.avgTime}s</span>
      </div>
    </div>
    <div class="stat-card">
      <div class="stat-info">
        <span class="stat-label">KNOWLEDGE COV</span>
        <span class="stat-value">${s.coveredPoints}/${s.totalPoints}</span>
      </div>
    </div>
  `;

  // 图表
  setTimeout(() => {
    if (charts.radar) charts.radar.dispose();
    if (charts.studentTrend) charts.studentTrend.dispose();
    if (charts.diffBar) charts.diffBar.dispose();
    charts.radar = initRadarChart(s);
    charts.studentTrend = initStudentTrendChart(s);
    charts.diffBar = initDifficultyBarChart(s);
  }, 100);

  // 知识点掌握度列表
  renderMasteryList(s);

  // 薄弱项
  renderWeakPoints(s);

  // 学习建议
  renderRecommendations(s);
}

function renderMasteryList(s) {
  const container = document.getElementById('knowledge-mastery');
  container.innerHTML = s.moduleScores.map(m => `
    <div class="mastery-item">
      <span class="mastery-name">${m.module}</span>
      <div class="mastery-bar">
        <div class="mastery-fill" style="width:${m.score}%;background:${getLevelColor(m.level)}"></div>
      </div>
      <span class="mastery-score" style="color:${getLevelColor(m.level)}">${m.score}%</span>
      <span class="mastery-level" style="color:${getLevelColor(m.level)};border-color:${getLevelColor(m.level)}">${getLevelLabel(m.level) === '已掌握' ? '[MASTERED]' : getLevelLabel(m.level) === '部分掌握' ? '[PARTIAL]' : '[WEAK]'}</span>
    </div>
  `).join('');
}

function renderWeakPoints(s) {
  const container = document.getElementById('weak-points');
  container.innerHTML = s.weakPoints.map(wp => `
    <div class="weak-point-card ${wp.priority}">
      <div class="weak-priority ${wp.priority}">${wp.priority}</div>
      <div class="weak-info">
        <div class="weak-name">${wp.name}</div>
        <div class="weak-module">${wp.module} · ${wp.id}</div>
        <div class="weak-reason">${wp.reason}</div>
        ${wp.consecutiveErrors > 0 ? `<div style="margin-top:8px;font-size:12px;color:#ff453a;font-family:var(--font-display);letter-spacing:.04em">[!] CONSECUTIVE ERRORS: ${wp.consecutiveErrors}</div>` : ''}
      </div>
      <div class="weak-score">
        <div class="score-value" style="color:${getLevelColor(wp.level)}">${wp.score}%</div>
        <div class="score-label">MASTERY</div>
      </div>
    </div>
  `).join('');
}

function renderRecommendations(s) {
  const container = document.getElementById('recommendations');
  const sorted = [...s.weakPoints].sort((a, b) => {
    const pOrder = { P0: 0, P1: 1, P2: 2 };
    return pOrder[a.priority] - pOrder[b.priority] || a.score - b.score;
  });

  container.innerHTML = sorted.map((wp, i) => {
    const suggestions = {
      P0: '立即进行专项训练，从基础题开始，逐步提升难度',
      P1: '本周重点复习，配合典型例题巩固',
      P2: '定期回顾，保持练习频率'
    };
    const difficulty = wp.score < 40 ? [1, 2] : wp.score < 60 ? [2, 3] : [3, 4];
    const time = wp.score < 40 ? '2-3 周' : wp.score < 60 ? '1-2 周' : '1 周';

    return `
      <div class="rec-card">
        <div class="rec-rank">${String(i + 1).padStart(2, '0')}</div>
        <div class="rec-info">
          <div class="rec-name">${wp.name}</div>
          <div class="rec-reason">${suggestions[wp.priority]}</div>
        </div>
        <div class="rec-meta">
          <div class="rec-meta-item">
            <div class="value" style="color:${getPriorityColor(wp.priority)}">${wp.priority}</div>
            <div class="label">PRIORITY</div>
          </div>
          <div class="rec-meta-item">
            <div class="value">LV.${difficulty[0]}-${difficulty[1]}</div>
            <div class="label">LEVEL</div>
          </div>
          <div class="rec-meta-item">
            <div class="value">${time}</div>
            <div class="label">ETA</div>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

// ===== DASHBOARD（概览 + 上传管线 + 审核） =====
function initDashboard() {
  // 概览统计
  animateNumber('stat-total-questions', questions.length);
  animateNumber('stat-knowledge-points', 52);
  const pending = reviewQueue.filter(i => i.status === 'pending');
  animateNumber('stat-pending', pending.length);
  const avgConf = pending.length > 0
    ? (pending.reduce((s, i) => s + i.aiConfidence, 0) / pending.length * 100).toFixed(0)
    : '0';
  document.getElementById('stat-confidence').textContent = avgConf + '%';

  // 高频错题表格（使用 students 数据生成）
  renderErrorTable();

  // 初始化上传区
  setupUploadZone();
  renderPipeline('idle');

  // 审核列表
  renderReviewList(pending);
}

function animateNumber(id, target, suffix = '') {
  const el = document.getElementById(id);
  if (!el) return;
  let current = 0;
  const step = target / 40;
  const timer = setInterval(() => {
    current += step;
    if (current >= target) {
      current = target;
      clearInterval(timer);
    }
    el.textContent = (suffix === '%' ? current.toFixed(1) : Math.round(current)) + suffix;
  }, 30);
}

function renderErrorTable() {
  const tbody = document.querySelector('#error-table tbody');
  if (!tbody) return;
  // 从 students 数据中生成高频错题
  const errorData = [];
  questions.forEach(q => {
    const errRate = 100 - q.stats.accuracy;
    if (errRate > 0) {
      errorData.push({
        stem: q.stem, module: getModuleName(q.module),
        errorRate: errRate, errorCount: q.stats.total - q.stats.correct,
        id: q.id
      });
    }
  });
  errorData.sort((a, b) => b.errorRate - a.errorRate);
  const top5 = errorData.slice(0, 5);

  tbody.innerHTML = top5.map((q, i) => {
    const rankClass = i === 0 ? 'top1' : i === 1 ? 'top2' : i === 2 ? 'top3' : 'normal';
    return `<tr>
      <td><span class="error-rank ${rankClass}">${String(i + 1).padStart(2, '0')}</span></td>
      <td style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${q.stem.substring(0, 50)}</td>
      <td>${q.module}</td>
      <td>
        <div class="error-rate-bar">
          <div class="error-rate-fill"><div class="fill" style="width:${q.errorRate}%;background:${q.errorRate > 70 ? '#ff453a' : q.errorRate > 50 ? currentTheme.warn : currentTheme.accent}"></div></div>
          <span class="error-rate-text">${q.errorRate}%</span>
        </div>
      </td>
      <td>${q.errorCount}</td>
      <td>${q.errorRate > 80 ? '<span class="tag err">[CRIT]</span> 高危' : q.errorRate > 60 ? '<span class="tag warn">[WARN]</span> 警告' : '<span class="tag ok">[OK]</span> 正常'}</td>
    </tr>`;
  }).join('');
}

// ===== 审核队列 =====
let currentReviewItem = null;

function renderReviewList(items) {
  const container = document.getElementById('review-list');
  if (!items || !items.length) {
    container.innerHTML = '<div style="padding:20px;text-align:center;color:var(--tx-3)">NO ITEMS IN QUEUE</div>';
    return;
  }
  container.innerHTML = items.map(item => {
    const isMethod = item.data.methodType === 'method';
    const badge = isMethod ? '[METHOD]' : '[QUESTION]';
    const badgeClass = isMethod ? 'method' : 'question';
    const preview = isMethod
      ? item.data.name || ''
      : (item.data.stem || '').substring(0, 60).replace(/\$.*?\$/g, '...');
    const source = item.sourceFile || 'unknown';
    const conf = (item.aiConfidence * 100).toFixed(0) + '%';
    const confColor = item.aiConfidence >= 0.9 ? currentTheme.accent : item.aiConfidence >= 0.8 ? currentTheme.warn : '#ff453a';

    return '<div class="review-item" data-id="' + item.id + '" onclick="showReviewDetail(\'' + item.id + '\')">' +
      '<div class="review-item-left">' +
        '<span class="review-badge ' + badgeClass + '">' + badge + '</span>' +
        '<span class="review-id">' + item.id + '</span>' +
      '</div>' +
      '<div class="review-item-center">' +
        '<span class="review-preview">' + preview + '</span>' +
        '<span class="review-source">SRC · ' + source + '</span>' +
      '</div>' +
      '<div class="review-item-right">' +
        '<span class="review-confidence" style="color:' + confColor + '">' + conf + '</span>' +
        '<span class="review-module">' + getModuleName(item.data.module || '') + '</span>' +
      '</div>' +
    '</div>';
  }).join('');
}

function showReviewDetail(itemId) {
  const item = reviewQueue.find(i => i.id === itemId);
  if (!item) return;
  currentReviewItem = item;

  const card = document.getElementById('review-detail-card');
  card.style.display = 'block';
  document.getElementById('review-detail-title').textContent = item.id + ' · ' + (item.data.methodType === 'method' ? 'METHOD' : 'QUESTION');

  const isMethod = item.data.methodType === 'method';
  const content = document.getElementById('review-detail-content');

  if (isMethod) {
    content.innerHTML = renderMethodDetailContent(item.data);
  } else {
    content.innerHTML = renderQuestionDetailContent(item.data);
  }

  // 渲染 LaTeX
  renderLatexInElement(content);
}

function renderQuestionDetailContent(data) {
  let html = '<div class="detail-grid">';
  html += '<div class="detail-row"><span class="detail-label">MODULE</span><span class="detail-value">' + getModuleName(data.module) + '</span></div>';
  html += '<div class="detail-row"><span class="detail-label">TYPE</span><span class="detail-value">' + getTypeLabel(data.type) + '</span></div>';
  html += '<div class="detail-row"><span class="detail-label">DIFFICULTY</span><span class="detail-value">LV.' + data.difficulty + ' ' + getDifficultyLabel(data.difficulty) + '</span></div>';
  html += '<div class="detail-row"><span class="detail-label">POINTS</span><span class="detail-value">' + (data.knowledge_points || []).join(' · ') + '</span></div>';
  html += '</div>';

  html += '<div class="detail-section"><h4>STEM</h4><div class="detail-text">' + (data.stem || '') + '</div></div>';

  if (data.options && data.options.length) {
    html += '<div class="detail-section"><h4>OPTIONS</h4><div class="detail-options">';
    data.options.forEach(opt => {
      html += '<div class="detail-option"><span class="opt-label">' + opt.label + '</span><span class="opt-content">' + opt.content + '</span></div>';
    });
    html += '</div></div>';
  }

  html += '<div class="detail-section"><h4>ANSWER</h4><div class="detail-text">' + (data.answer || '') + '</div></div>';
  html += '<div class="detail-section"><h4>ANALYSIS</h4><div class="detail-text">' + (data.analysis || '') + '</div></div>';

  if (data.tags && data.tags.length) {
    html += '<div class="detail-section"><h4>TAGS</h4><div class="detail-tags">';
    data.tags.forEach(tag => { html += '<span class="tag">' + tag + '</span>'; });
    html += '</div></div>';
  }

  if (data.source) {
    html += '<div class="detail-section"><h4>SOURCE</h4><div class="detail-text">' +
      data.source.type + (data.source.year ? ' · ' + data.source.year : '') +
      (data.source.region ? ' · ' + data.source.region : '') + '</div></div>';
  }

  return html;
}

function renderMethodDetailContent(data) {
  let html = '<div class="detail-grid">';
  html += '<div class="detail-row"><span class="detail-label">NAME</span><span class="detail-value">' + (data.name || '') + '</span></div>';
  html += '<div class="detail-row"><span class="detail-label">CATEGORY</span><span class="detail-value">' + (data.category || '') + '</span></div>';
  html += '<div class="detail-row"><span class="detail-label">MODULE</span><span class="detail-value">' + getModuleName(data.module || '') + '</span></div>';
  html += '<div class="detail-row"><span class="detail-label">APPLICABLE</span><span class="detail-value">' + (data.applicable_types || []).map(getTypeLabel).join(' · ') + '</span></div>';
  html += '<div class="detail-row"><span class="detail-label">DIFFICULTY</span><span class="detail-value">LV.' + (data.difficulty_range || [0,0]).join('-') + '</span></div>';
  html += '</div>';

  html += '<div class="detail-section"><h4>PRINCIPLE</h4><div class="detail-text">' + (data.principle || '') + '</div></div>';

  if (data.steps && data.steps.length) {
    html += '<div class="detail-section"><h4>STEPS</h4><div class="detail-steps">';
    data.steps.forEach((step, i) => {
      html += '<div class="detail-step"><span class="step-num">' + (i + 1) + '</span><span class="step-text">' + step + '</span></div>';
    });
    html += '</div></div>';
  }

  if (data.common_forms && data.common_forms.length) {
    html += '<div class="detail-section"><h4>COMMON FORMS</h4><div class="detail-text">';
    data.common_forms.forEach(f => { html += '<div class="detail-formula">' + f + '</div>'; });
    html += '</div></div>';
  }

  if (data.pitfalls && data.pitfalls.length) {
    html += '<div class="detail-section"><h4>PITFALLS</h4><div class="detail-warnings">';
    data.pitfalls.forEach(p => { html += '<div class="detail-warning">[!] ' + p + '</div>'; });
    html += '</div></div>';
  }

  if (data.keywords && data.keywords.length) {
    html += '<div class="detail-section"><h4>KEYWORDS</h4><div class="detail-tags">';
    data.keywords.forEach(k => { html += '<span class="tag">' + k + '</span>'; });
    html += '</div></div>';
  }

  return html;
}

function approveItem() {
  if (!currentReviewItem) return;
  currentReviewItem.status = 'approved';
  const pending = reviewQueue.filter(i => i.status === 'pending');
  animateNumber('stat-pending', pending.length);
  renderReviewList(pending);
  document.getElementById('review-detail-card').style.display = 'none';
  currentReviewItem = null;
}

function rejectItem() {
  if (!currentReviewItem) return;
  currentReviewItem.status = 'rejected';
  const pending = reviewQueue.filter(i => i.status === 'pending');
  animateNumber('stat-pending', pending.length);
  renderReviewList(pending);
  document.getElementById('review-detail-card').style.display = 'none';
  currentReviewItem = null;
}

function editItem() {
  alert('[EDIT] FUNCTION IN DEVELOPMENT');
}

function renderLatexInElement(el) {
  if (typeof katex === 'undefined') return;
  const textNodes = [];
  const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, null, false);
  while (walker.nextNode()) textNodes.push(walker.currentNode);

  textNodes.forEach(node => {
    const text = node.nodeValue;
    const parts = text.split(/(\$[^$]+\$)/);
    if (parts.length <= 1) return;
    const frag = document.createDocumentFragment();
    parts.forEach(part => {
      if (part.startsWith('$') && part.endsWith('$')) {
        const latex = part.slice(1, -1);
        try {
          const span = document.createElement('span');
          katex.render(latex, span, { throwOnError: false, displayMode: false });
          frag.appendChild(span);
        } catch (e) {
          frag.appendChild(document.createTextNode(part));
        }
      } else {
        frag.appendChild(document.createTextNode(part));
      }
    });
    node.parentNode.replaceChild(frag, node);
  });
}

// ===== UPLOAD :: 文件上传与处理管线 =====
const API_BASE = window.location.origin;
let uploadedFiles = [];
let extractedResults = [];
let currentEditorType = null;

function setupUploadZone() {
  const zone = document.getElementById('upload-zone');
  if (!zone) return;
  const input = document.getElementById('file-input');

  zone.addEventListener('click', () => input.click());
  input.addEventListener('change', (e) => handleFiles(e.target.files));

  zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('drag-over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', (e) => {
    e.preventDefault(); zone.classList.remove('drag-over');
    handleFiles(e.dataTransfer.files);
  });
}

async function handleFiles(fileList) {
  const files = Array.from(fileList);
  renderPipeline('uploading');
  document.getElementById('uploaded-files-card').style.display = 'block';

  for (const file of files) {
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    const size = file.size;
    const fileItem = {
      name: file.name, ext: ext, size: size,
      status: 'uploading', result: null
    };
    uploadedFiles.push(fileItem);
    renderFileList();

    try {
      const formData = new FormData();
      formData.append('file', file);

      const resp = await fetch(API_BASE + '/api/upload', { method: 'POST', body: formData });
      const data = await resp.json();

      if (data.success) {
        fileItem.serverName = data.filename;
        fileItem.status = 'uploaded';
        fileItem.originalName = data.original_name;
      } else {
        fileItem.status = 'error';
        fileItem.error = data.error;
      }
    } catch (e) {
      fileItem.status = 'uploaded';
      fileItem.serverName = file.name;
    }

    renderFileList();
  }

  renderPipeline('uploaded');
}

function renderFileList() {
  const container = document.getElementById('file-list');
  container.innerHTML = uploadedFiles.map((f, i) => {
    const sizeStr = f.size > 1024 * 1024 ? (f.size / 1024 / 1024).toFixed(1) + 'MB' : (f.size / 1024).toFixed(0) + 'KB';
    const statusClass = f.status;
    const statusText = { uploading: 'UPLOADING...', uploaded: 'UPLOADED', error: 'ERROR', processing: 'PROCESSING...', done: 'DONE' }[f.status] || f.status;

    return '<div class="file-item">' +
      '<div class="file-item-left">' +
        '<span class="file-ext">' + f.ext.toUpperCase().replace('.', '') + '</span>' +
        '<span class="file-name">' + f.name + '</span>' +
      '</div>' +
      '<div class="file-size">' + sizeStr + '</div>' +
      '<div class="file-status ' + statusClass + '">' + statusText + '</div>' +
    '</div>';
  }).join('');
}

async function processAllFiles() {
  if (!uploadedFiles.length) return;

  renderPipeline('processing');
  uploadedFiles.forEach(f => { f.status = 'processing'; });
  renderFileList();

  let allItems = [];

  for (const f of uploadedFiles) {
    if (f.status !== 'processing') continue;

    try {
      const resp = await fetch(API_BASE + '/api/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: f.serverName })
      });
      const data = await resp.json();

      if (data.success) {
        allItems = allItems.concat(data.items);
        f.status = 'done';
        extractedResults = extractedResults.concat(data.items);
      } else {
        f.status = 'error';
        f.error = data.error || 'process failed';
      }
    } catch (e) {
      const mockItems = _generateMockResults(f);
      allItems = allItems.concat(mockItems);
      f.status = 'done';
      extractedResults = extractedResults.concat(mockItems);
    }

    renderFileList();
  }

  renderPipeline('extracted');
  document.getElementById('process-results-card').style.display = 'block';
  document.getElementById('results-count-badge').textContent = extractedResults.length + ' ITEMS';
  renderResultsList();
}

function _generateMockResults(fileItem) {
  const ext = fileItem.ext;
  const sourceMap = {
    '.png': 'image_ocr', '.jpg': 'image_ocr', '.jpeg': 'image_ocr',
    '.pdf': 'pdf_parse', '.docx': 'docx_parse', '.doc': 'docx_parse',
    '.txt': 'text_parse', '.md': 'text_parse'
  };
  const source = sourceMap[ext] || 'manual';
  const rid = 'R' + String(extractedResults.length + 1).padStart(3, '0');

  return [
    {
      id: rid, status: 'pending', source: source,
      sourceFile: fileItem.name,
      extractedAt: new Date().toISOString(),
      data: {
        module: 'FUNC', knowledge_points: ['FUNC-02-02-01'],
        difficulty: 3, type: 'choice',
        stem: '[模拟提取] 从 "' + fileItem.name + '" 中提取的题目',
        options: [{ label: 'A', content: '$1$' }, { label: 'B', content: '$2$' }],
        answer: 'A', analysis: '模拟解析',
        tags: ['模拟', '函数'], source: { type: '自编' }
      },
      aiConfidence: 0.85, reviewNotes: ''
    }
  ];
}

function renderResultsList() {
  const container = document.getElementById('results-list');
  container.innerHTML = extractedResults.map((item, i) => {
    const isMethod = item.data.methodType === 'method';
    const badgeClass = isMethod ? 'method' : 'question';
    const badgeText = isMethod ? '[METHOD]' : '[QUESTION]';
    const preview = isMethod ? (item.data.name || '') : (item.data.stem || '').substring(0, 60).replace(/\$.*?\$/g, '...');
    const conf = (item.aiConfidence * 100).toFixed(0) + '%';
    const confClass = item.aiConfidence >= 0.9 ? 'high' : item.aiConfidence >= 0.8 ? 'mid' : 'low';

    return '<div class="result-item" onclick="openEditor(' + i + ')">' +
      '<span class="result-badge ' + badgeClass + '">' + badgeText + '</span>' +
      '<span class="result-preview">' + preview + '</span>' +
      '<span class="result-confidence ' + confClass + '">' + conf + '</span>' +
    '</div>';
  }).join('');
}

function openEditor(index) {
  const item = extractedResults[index];
  if (!item) return;

  currentEditorType = item.data.methodType === 'method' ? 'method' : 'question';
  const card = document.getElementById('format-editor-card');
  card.style.display = 'block';

  document.getElementById('editor-title').textContent = item.id + ' · FORMAT EDITOR';

  if (currentEditorType === 'question') {
    document.getElementById('question-editor').style.display = 'block';
    document.getElementById('method-editor').style.display = 'none';
    fillQuestionForm(item.data);
  } else {
    document.getElementById('question-editor').style.display = 'none';
    document.getElementById('method-editor').style.display = 'block';
    fillMethodForm(item.data);
  }
}

function fillQuestionForm(data) {
  document.getElementById('ed-id').value = data.id || '';
  document.getElementById('ed-module').value = data.module || 'FUNC';
  document.getElementById('ed-difficulty').value = data.difficulty || 3;
  document.getElementById('ed-type').value = data.type || 'choice';
  document.getElementById('ed-stem').value = data.stem || '';
  document.getElementById('ed-answer').value = data.answer || '';
  document.getElementById('ed-analysis').value = data.analysis || '';
  document.getElementById('ed-tags').value = (data.tags || []).join(', ');
  document.getElementById('ed-kp').value = (data.knowledge_points || []).join(', ');
  document.getElementById('ed-source-type').value = (data.source && data.source.type) || '自编';
  document.getElementById('ed-source-year').value = (data.source && data.source.year) || 2024;
  document.getElementById('ed-source-region').value = (data.source && data.source.region) || '';

  const options = data.options || [];
  const optInputs = document.querySelectorAll('.option-input');
  optInputs.forEach((input, i) => {
    input.value = options[i] ? options[i].content : '';
  });

  document.getElementById('options-section').style.display = data.type === 'choice' ? 'block' : 'none';
  updateLatexPreview();
}

function fillMethodForm(data) {
  document.getElementById('ed-m-id').value = data.id || '';
  document.getElementById('ed-m-name').value = data.name || '';
  document.getElementById('ed-m-category').value = data.category || '';
  document.getElementById('ed-m-module').value = data.module || 'FUNC';
  document.getElementById('ed-m-principle').value = data.principle || '';
  document.getElementById('ed-m-keywords').value = (data.keywords || []).join(', ');
  document.getElementById('ed-m-types').value = (data.applicable_types || []).join(', ');
  document.getElementById('ed-m-drange').value = data.difficulty_range ? data.difficulty_range.join('-') : '';
  document.getElementById('ed-m-forms').value = (data.common_forms || []).join('\n');
  document.getElementById('ed-m-pitfalls').value = (data.pitfalls || []).join('\n');

  const steps = data.steps || [];
  const stepsContainer = document.getElementById('ed-m-steps');
  stepsContainer.innerHTML = steps.map((s, i) =>
    '<div class="step-row"><span class="step-num">' + String(i + 1).padStart(2, '0') + '</span>' +
    '<input type="text" class="step-input" value="' + s + '"></div>'
  ).join('');
}

function addStep() {
  const container = document.getElementById('ed-m-steps');
  const count = container.querySelectorAll('.step-row').length;
  container.innerHTML += '<div class="step-row"><span class="step-num">' + String(count + 1).padStart(2, '0') + '</span>' +
    '<input type="text" class="step-input" placeholder="新增步骤"></div>';
}

function updateLatexPreview() {
  const stem = document.getElementById('ed-stem').value;
  const preview = document.getElementById('stem-preview');
  if (typeof katex !== 'undefined' && stem) {
    let html = '';
    const parts = stem.split(/(\$[^$]+\$)/);
    parts.forEach(part => {
      if (part.startsWith('$') && part.endsWith('$')) {
        try {
          const span = document.createElement('span');
          katex.render(part.slice(1, -1), span, { throwOnError: false, displayMode: false });
          html += span.innerHTML;
        } catch (e) { html += part; }
      } else { html += part; }
    });
    preview.innerHTML = html;
  } else {
    preview.textContent = stem;
  }
}

// 题干输入时实时预览 LaTeX
document.addEventListener('input', (e) => {
  if (e.target.id === 'ed-stem') updateLatexPreview();
  if (e.target.id === 'ed-type') {
    document.getElementById('options-section').style.display = e.target.value === 'choice' ? 'block' : 'none';
  }
});

async function saveFromEditor() {
  if (currentEditorType === 'question') {
    const data = collectQuestionData();
    try {
      const resp = await fetch(API_BASE + '/api/save-question', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      const result = await resp.json();
      if (result.success) {
        _showToast('QUESTION ' + result.id + ' SAVED', 'success');
        closeEditor();
      } else {
        _showToast('SAVE FAILED: ' + (result.errors || []).join(', '), 'error');
      }
    } catch (e) {
      data.id = 'Q' + String(questions.length + 1).padStart(3, '0');
      data.status = 'active';
      data.stats = { total: 0, correct: 0, accuracy: 0 };
      questions.push(data);
      _showToast('QUESTION ' + data.id + ' SAVED (LOCAL)', 'success');
      closeEditor();
    }
  } else {
    const data = collectMethodData();
    try {
      const resp = await fetch(API_BASE + '/api/save-method', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      const result = await resp.json();
      if (result.success) {
        _showToast('METHOD ' + result.id + ' SAVED', 'success');
        closeEditor();
      } else {
        _showToast('SAVE FAILED: ' + (result.errors || []).join(', '), 'error');
      }
    } catch (e) {
      data.id = 'M' + String(methods.length + 1).padStart(3, '0');
      data.status = 'active';
      methods.push(data);
      _showToast('METHOD ' + data.id + ' SAVED (LOCAL)', 'success');
      closeEditor();
    }
  }
}

function collectQuestionData() {
  const options = [];
  if (document.getElementById('ed-type').value === 'choice') {
    document.querySelectorAll('.option-input').forEach(input => {
      if (input.value.trim()) {
        options.push({ label: input.dataset.label, content: input.value.trim() });
      }
    });
  }
  return {
    id: document.getElementById('ed-id').value || '',
    module: document.getElementById('ed-module').value,
    difficulty: parseInt(document.getElementById('ed-difficulty').value),
    type: document.getElementById('ed-type').value,
    stem: document.getElementById('ed-stem').value,
    options: options,
    answer: document.getElementById('ed-answer').value,
    analysis: document.getElementById('ed-analysis').value,
    tags: document.getElementById('ed-tags').value.split(',').map(s => s.trim()).filter(Boolean),
    knowledge_points: document.getElementById('ed-kp').value.split(',').map(s => s.trim()).filter(Boolean),
    source: {
      type: document.getElementById('ed-source-type').value,
      year: parseInt(document.getElementById('ed-source-year').value) || 2024,
      region: document.getElementById('ed-source-region').value
    }
  };
}

function collectMethodData() {
  const steps = [];
  document.querySelectorAll('#ed-m-steps .step-input').forEach(input => {
    if (input.value.trim()) steps.push(input.value.trim());
  });
  const drange = document.getElementById('ed-m-drange').value.split('-').map(n => parseInt(n.trim()));
  return {
    id: document.getElementById('ed-m-id').value || '',
    name: document.getElementById('ed-m-name').value,
    category: document.getElementById('ed-m-category').value,
    module: document.getElementById('ed-m-module').value,
    principle: document.getElementById('ed-m-principle').value,
    steps: steps,
    keywords: document.getElementById('ed-m-keywords').value.split(',').map(s => s.trim()).filter(Boolean),
    applicable_types: document.getElementById('ed-m-types').value.split(',').map(s => s.trim()).filter(Boolean),
    difficulty_range: drange.length === 2 ? drange : [3, 5],
    common_forms: document.getElementById('ed-m-forms').value.split('\n').filter(Boolean),
    pitfalls: document.getElementById('ed-m-pitfalls').value.split('\n').filter(Boolean)
  };
}

function closeEditor() {
  document.getElementById('format-editor-card').style.display = 'none';
  document.getElementById('question-editor').style.display = 'none';
  document.getElementById('method-editor').style.display = 'none';
  currentEditorType = null;
}

function clearUploads() {
  uploadedFiles = [];
  extractedResults = [];
  renderFileList();
  document.getElementById('uploaded-files-card').style.display = 'none';
  document.getElementById('process-results-card').style.display = 'none';
  document.getElementById('format-editor-card').style.display = 'none';
  renderPipeline('idle');
}

function renderPipeline(state) {
  const steps = ['pipe-upload', 'pipe-ocr', 'pipe-llm', 'pipe-review', 'pipe-store'];
  const connectors = document.querySelectorAll('.pipeline-connector');
  const stateMap = {
    idle: { statuses: ['IDLE', 'IDLE', 'IDLE', 'IDLE', 'IDLE'], classes: ['', '', '', '', ''] },
    uploading: { statuses: ['ACTIVE', 'IDLE', 'IDLE', 'IDLE', 'IDLE'], classes: ['active', '', '', '', ''] },
    uploaded: { statuses: ['DONE', 'IDLE', 'IDLE', 'IDLE', 'IDLE'], classes: ['done', '', '', '', ''] },
    processing: { statuses: ['DONE', 'ACTIVE', 'ACTIVE', 'IDLE', 'IDLE'], classes: ['done', 'active', 'active', '', ''] },
    extracted: { statuses: ['DONE', 'DONE', 'DONE', 'IDLE', 'IDLE'], classes: ['done', 'done', 'done', '', ''] },
    reviewing: { statuses: ['DONE', 'DONE', 'DONE', 'ACTIVE', 'IDLE'], classes: ['done', 'done', 'done', 'active', ''] },
    stored: { statuses: ['DONE', 'DONE', 'DONE', 'DONE', 'DONE'], classes: ['done', 'done', 'done', 'done', 'done'] },
  };

  const cfg = stateMap[state] || stateMap.idle;
  steps.forEach((stepId, i) => {
    const el = document.getElementById(stepId);
    const statusEl = document.getElementById(stepId + '-status');
    if (!el || !statusEl) return;
    statusEl.textContent = cfg.statuses[i];
    statusEl.className = 'pipe-status ' + cfg.classes[i];
  });

  connectors.forEach((c, i) => {
    c.className = 'pipeline-connector' + (i < steps.length && cfg.classes[i] === 'done' ? ' active' : '');
  });
}

function _showToast(msg, type) {
  const toast = document.createElement('div');
  toast.style.cssText = 'position:fixed;bottom:20px;left:50%;transform:translateX(-50%);padding:10px 24px;font-family:var(--font-display);font-size:13px;z-index:9999;' +
    (type === 'success' ? `background:#0a0a0a;color:${currentTheme.accent};border:1px solid ${currentTheme.accentLine};` : 'background:#0a0a0a;color:#ff453a;border:1px solid rgba(255,69,58,.40);');
  toast.textContent = msg;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3000);
}

/* Global showToast for pricing page onclick */
function showToast(msg) { _showToast(msg, 'success'); }

/* ===== Pricing / 订阅计划 ===== */
function initPricing() {
  // Restore billing toggle state
  const billing = localStorage.getItem('shuxue-billing') || 'monthly';
  switchBilling(billing);
  // Add tier indicator to pricing cards
  updatePricingCardHighlight();
}

function switchBilling(type) {
  const btns = document.querySelectorAll('.tier-toggle button');
  btns.forEach(b => b.classList.remove('active'));
  if (type === 'monthly') {
    btns[0].classList.add('active');
    const proPrice = document.getElementById('pro-price');
    const proPeriod = document.getElementById('pro-period');
    const proUnit = document.getElementById('pro-unit');
    const teamPrice = document.getElementById('team-price');
    const teamPeriod = document.getElementById('team-period');
    const teamUnit = document.getElementById('team-unit');
    if (proPrice) proPrice.textContent = '49';
    if (proPeriod) proPeriod.textContent = '/月';
    if (proUnit) proUnit.textContent = '单座席 · 按月计费';
    if (teamPrice) teamPrice.textContent = '199';
    if (teamPeriod) teamPeriod.textContent = '/月';
    if (teamUnit) teamUnit.textContent = '5 座席 · 含管理后台';
  } else {
    btns[1].classList.add('active');
    const proPrice = document.getElementById('pro-price');
    const proPeriod = document.getElementById('pro-period');
    const proUnit = document.getElementById('pro-unit');
    const teamPrice = document.getElementById('team-price');
    const teamPeriod = document.getElementById('team-period');
    const teamUnit = document.getElementById('team-unit');
    if (proPrice) proPrice.textContent = '490';
    if (proPeriod) proPeriod.textContent = '/年';
    if (proUnit) proUnit.textContent = '年付省 ¥98 · 相当 17% OFF';
    if (teamPrice) teamPrice.textContent = '1,990';
    if (teamPeriod) teamPeriod.textContent = '/年';
    if (teamUnit) teamUnit.textContent = '年付省 ¥398 · 相当 17% OFF';
  }
  localStorage.setItem('shuxue-billing', type);
}

function updatePricingCardHighlight() {
  document.querySelectorAll('.pricing-card').forEach(card => {
    const tierName = card.querySelector('.tier-name');
    if (!tierName) return;
    // Check if this card matches current tier
    const tierMap = { 'TIER 01': 'free', 'TIER 02': 'pro', 'TIER 03': 'team', 'TIER 04': 'api' };
    const cardTier = tierMap[tierName.textContent];
    if (cardTier === currentTier) {
      card.style.borderColor = 'var(--accent)';
    }
  });
}

/* ===== Subscription System Enhancement ===== */
function addTierIndicatorToNavbar() {
  const navUser = document.querySelector('.nav-user');
  if (!navUser) return;
  // Add tier badge after date
  const badge = document.createElement('span');
  badge.id = 'tier-badge';
  badge.className = 'tier-badge ' + currentTier;
  badge.textContent = SUBSCRIPTION_TIERS[currentTier].name;
  badge.style.marginLeft = '8px';
  navUser.insertBefore(badge, navUser.querySelector('.user-avatar'));
}

function addUsageIndicators() {
  // Add usage limit bars to question stats
  const statsBar = document.querySelector('.question-stats');
  if (!statsBar) return;
  const limit = checkTierLimit('questionsPerDay');
  if (limit.limit && limit.limit !== Infinity) {
    const usageEl = document.createElement('span');
    usageEl.className = 'usage-limit-bar';
    const pct = Math.min((limit.remaining / limit.limit) * 100, 100);
    usageEl.innerHTML = `DAILY: ${limit.remaining}/${limit.limit} LEFT <span class="usage-limit-fill"><span class="used" style="width:${pct}%"></span></span>`;
    statsBar.appendChild(usageEl);
  }
}

function enforceTierOnFeatureButtons() {
  // Lock Pro-only features for free tier
  document.querySelectorAll('[data-tier-lock]').forEach(el => {
    const requiredTier = el.dataset.tierLock;
    const tierOrder = ['free', 'pro', 'team', 'api'];
    const currentIdx = tierOrder.indexOf(currentTier);
    const requiredIdx = tierOrder.indexOf(requiredTier);
    if (currentIdx < requiredIdx) {
      el.classList.add('feature-lock');
      el.style.opacity = '.5';
      el.style.cursor = 'not-allowed';
      el.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        _showToast('此功能需升级至 ' + SUBSCRIPTION_TIERS[requiredTier].name + ' · ¥' + SUBSCRIPTION_TIERS[requiredTier].priceMonthly + '/月', 'error');
      }, true);
    }
  });
}



function debounce(fn, delay) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

// ===== 关于我们 =====
function initAbout() {
  // 默认显示博客子页
  initBlog();
}

function initBlog() {
  populateBlogFilters();
  renderBlogList();
}

function initAboutInfo() {
  // 静态页面，无需动态逻辑
}

function populateBlogFilters() {
  const tagSelect = document.getElementById('blog-tag-filter');
  const catSelect = document.getElementById('blog-cat-filter');
  while (tagSelect.options.length > 1) tagSelect.remove(1);
  while (catSelect.options.length > 1) catSelect.remove(1);

  const tags = {};
  const cats = {};
  blogPosts.forEach(p => {
    p.tags.forEach(t => { tags[t] = (tags[t] || 0) + 1; });
    cats[p.category] = (cats[p.category] || 0) + 1;
  });

  Object.entries(tags).sort((a,b) => b[1]-a[1]).forEach(([name, count]) => {
    const opt = document.createElement('option');
    opt.value = name; opt.textContent = `${name} (${count})`;
    tagSelect.appendChild(opt);
  });
  Object.entries(cats).sort((a,b) => b[1]-a[1]).forEach(([name, count]) => {
    const opt = document.createElement('option');
    opt.value = name; opt.textContent = `${name} (${count})`;
    catSelect.appendChild(opt);
  });

  tagSelect.onchange = () => renderBlogList();
  catSelect.onchange = () => renderBlogList();
}

function renderBlogList() {
  const tagFilter = document.getElementById('blog-tag-filter').value;
  const catFilter = document.getElementById('blog-cat-filter').value;
  const list = document.getElementById('blog-list');
  const detail = document.getElementById('blog-detail');

  detail.style.display = 'none';
  list.style.display = 'grid';

  let filtered = blogPosts;
  if (tagFilter) filtered = filtered.filter(p => p.tags.includes(tagFilter));
  if (catFilter) filtered = filtered.filter(p => p.category === catFilter);

  document.getElementById('blog-count').textContent = filtered.length;

  list.innerHTML = filtered.map(post => `
    <div class="blog-card" onclick="showBlogDetail('${post.id}')">
      <div class="blog-card-meta">
        <span class="blog-label">${post.label}</span>
        <span>${post.date}</span>
        <span>${post.readTime} MIN</span>
        <span>${post.category}</span>
      </div>
      <div class="blog-card-body">
        <h3>${post.title}</h3>
        <p class="blog-excerpt">${post.excerpt}</p>
        <div class="blog-card-tags">
          ${post.tags.map(t => `<span class="tag">${t}</span>`).join('')}
        </div>
      </div>
    </div>
  `).join('');
}

function showBlogDetail(postId) {
  const post = blogPosts.find(p => p.id === postId);
  if (!post) return;

  const list = document.getElementById('blog-list');
  const detail = document.getElementById('blog-detail');

  list.style.display = 'none';
  detail.style.display = 'block';

  const htmlContent = simpleMarkdown(post.content);

  detail.innerHTML = `
    <span class="blog-detail-back" onclick="closeBlogDetail()">[-] BACK TO LIST</span>
    <div class="blog-detail-meta">
      <span>${post.label}</span>
      <span>${post.date}</span>
      <span>${post.readTime} MIN READ</span>
      <span>${post.category}</span>
    </div>
    <h2>${post.title}</h2>
    <div class="blog-card-tags" style="margin-bottom:20px;">
      ${post.tags.map(t => `<span class="tag">${t}</span>`).join('')}
    </div>
    <div class="blog-detail-content">${htmlContent}</div>
  `;
}

function closeBlogDetail() {
  document.getElementById('blog-list').style.display = 'grid';
  document.getElementById('blog-detail').style.display = 'none';
}

function simpleMarkdown(md) {
  let html = md;
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^# (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
  html = html.replace(/^\|(.+)\|$/gm, (match) => {
    const cells = match.split('|').filter(c => c.trim());
    const isHeader = cells.some(c => c.trim().match(/^[\-:]+$/));
    if (isHeader) return '';
    const tag = 'td';
    return '<tr>' + cells.map(c => `<${tag}>${c.trim()}</${tag}>`).join('') + '</tr>';
  });
  html = html.replace(/((<tr>[\s\S]*?<\/tr>\n)+)/g, '<table>$1</table>');
  html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
  html = html.replace(/(<li>[\s\S]*?<\/li>\n?)+/g, '<ul>$&</ul>');
  html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');
  html = html.replace(/^(?!<[hupltroc]|<li|<tr|<table|<pre|<strong|<code)(.+)$/gm, '<p>$1</p>');
  html = html.replace(/<p>\s*<\/p>/g, '');
  return html;
}

// ===== 初始化 =====
document.addEventListener('DOMContentLoaded', () => {
  initThemeUI();
  addTierIndicatorToNavbar();
  enforceTierOnFeatureButtons();
  initLearning();
});
