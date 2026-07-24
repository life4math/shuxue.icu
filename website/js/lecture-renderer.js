(function () {
  'use strict';

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }

  function appendMultiline(target, value) {
    const text = String(value || '');
    if (!text) return;
    target.append(element('p', 'lecture-block-text', text));
  }

  function renderMath(target, latex, displayMode = true) {
    const source = String(latex || '');
    if (!source) return;
    const host = element('div', displayMode ? 'lecture-math-display' : 'lecture-math-inline');
    if (window.katex) {
      try {
        window.katex.render(source, host, {
          displayMode,
          throwOnError: false,
          strict: 'ignore',
        });
      } catch (_) {
        host.textContent = source;
      }
    } else {
      host.textContent = source;
    }
    target.append(host);
  }

  function safeImageUrl(value) {
    const url = String(value || '').trim();
    if (!url) return '';
    if (url.startsWith('https://')) return url;
    if (url.startsWith('//') || url.startsWith('\\')) return '';
    const firstSegment = url.split('/')[0];
    return firstSegment.includes(':') ? '' : url;
  }

  function renderBlock(block, options = {}) {
    const item = block && typeof block === 'object' ? block : {};
    const type = item.type || 'text';
    const card = element('article', `lecture-block lecture-block-${type}`);
    card.dataset.blockId = item.id || '';
    card.dataset.blockType = type;

    if (type === 'text') {
      appendMultiline(card, item.text);
    } else if (type === 'math') {
      renderMath(card, item.latex, true);
      if (item.caption) card.append(element('p', 'lecture-caption', item.caption));
    } else if (type === 'callout') {
      card.dataset.tone = item.tone || 'note';
      card.append(element('span', 'lecture-block-label', item.title || '要点'));
      appendMultiline(card, item.text);
    } else if (type === 'example') {
      card.append(element('span', 'lecture-block-label', item.title || '例题'));
      appendMultiline(card, item.stem);
      if (item.answer) {
        const answer = element('div', 'lecture-answer');
        answer.hidden = options.revealAnswers === false;
        answer.append(element('strong', '', '解答'));
        appendMultiline(answer, item.answer);
        card.append(answer);
      }
    } else if (type === 'question_ref') {
      card.append(element('span', 'lecture-block-label', item.title || '题目引用'));
      if (item.question_id) card.append(element('code', 'lecture-ref-code', item.question_id));
      appendMultiline(card, item.stem || '题目将在正式题库接入后显示。');
    } else if (type === 'knowledge_ref') {
      card.append(element('span', 'lecture-block-label', '知识点'));
      const title = item.title || item.node_id || '未命名知识点';
      if (item.node_id && options.linkKnowledge !== false) {
        const link = element('a', 'lecture-knowledge-link', title);
        link.href = `index.html?knowledge=${encodeURIComponent(item.node_id)}`;
        card.append(link);
      } else {
        card.append(element('strong', '', title));
      }
      appendMultiline(card, item.note);
    } else if (type === 'image') {
      const url = safeImageUrl(item.url);
      if (url) {
        const image = element('img', 'lecture-image');
        image.src = url;
        image.alt = item.alt || '';
        image.loading = 'lazy';
        card.append(image);
      } else {
        card.append(element('p', 'lecture-render-warning', '图片地址无效'));
      }
      if (item.caption) card.append(element('p', 'lecture-caption', item.caption));
    } else {
      card.append(element('p', 'lecture-render-warning', `暂不支持的内容块：${type}`));
    }
    return card;
  }

  function orderedSections(payload) {
    const sections = payload && Array.isArray(payload.sections) ? payload.sections : [];
    return [...sections].sort((a, b) => Number(a.sort_order || 0) - Number(b.sort_order || 0));
  }

  function renderDocument(target, payload, options = {}) {
    target.replaceChildren();
    const sections = orderedSections(payload);
    if (!sections.length) {
      target.append(element('p', 'lecture-empty', '这份讲义还没有内容。'));
      return;
    }
    sections.forEach((section, index) => {
      const sectionNode = element('section', 'lecture-section');
      const heading = element('div', 'lecture-section-heading');
      heading.append(
        element('span', 'lecture-section-number', String(index + 1).padStart(2, '0')),
        element('h2', '', section.title || `第 ${index + 1} 部分`),
      );
      sectionNode.append(heading);
      (section.blocks || []).forEach(block => sectionNode.append(renderBlock(block, options)));
      if (!(section.blocks || []).length && options.showEmpty) {
        sectionNode.append(element('p', 'lecture-empty', '本节暂无内容块。'));
      }
      target.append(sectionNode);
    });
  }

  function flatten(payload) {
    const slides = [];
    orderedSections(payload).forEach((section, sectionIndex) => {
      const blocks = Array.isArray(section.blocks) ? section.blocks : [];
      if (!blocks.length) {
        slides.push({ section, sectionIndex, block: null, blockIndex: 0 });
      } else {
        blocks.forEach((block, blockIndex) => {
          slides.push({ section, sectionIndex, block, blockIndex });
        });
      }
    });
    return slides;
  }

  window.LectureRenderer = {
    flatten,
    renderBlock,
    renderDocument,
  };
}());
