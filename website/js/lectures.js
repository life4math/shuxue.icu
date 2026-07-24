(async function () {
  'use strict';

  const target = document.getElementById('lecture-catalog');

  function create(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function render(items) {
    target.replaceChildren();
    if (!items.length) {
      target.append(create('p', 'lecture-empty', '还没有已发布的讲义。'));
      return;
    }
    const groups = new Map();
    items.forEach(item => {
      const key = item.course_id;
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(item);
    });
    groups.forEach(group => {
      const section = create('section', 'lecture-course-group');
      const title = group[0].course_title || '未分组课程';
      const grade = group[0].course_grade_label ? ` · ${group[0].course_grade_label}` : '';
      section.append(create('h2', '', `${title}${grade}`));
      const grid = create('div', 'lecture-card-grid');
      group.forEach(item => {
        const link = create('a', 'lecture-card');
        link.href = `lecture.html?id=${encodeURIComponent(item.slug || item.id)}`;
        link.append(
          create('span', 'lecture-eyebrow', `VERSION ${item.version}`),
          create('h3', '', item.title),
          create('p', '', item.summary || '打开讲义查看完整内容。'),
        );
        grid.append(link);
      });
      section.append(grid);
      target.append(section);
    });
  }

  try {
    const response = await fetch('/api/v1/public/lectures', { credentials: 'same-origin' });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `请求失败 (${response.status})`);
    render(data.items || []);
  } catch (error) {
    target.replaceChildren(create('p', 'lecture-render-warning', `讲义加载失败：${error.message}`));
  }
}());
