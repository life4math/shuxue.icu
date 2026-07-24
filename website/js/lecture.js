(async function () {
  'use strict';

  const params = new URLSearchParams(window.location.search);
  const lectureRef = params.get('id') || '';
  const classButton = document.getElementById('class-mode-button');
  const stage = document.getElementById('lecture-stage');
  const stageContent = document.getElementById('stage-content');
  let lecture = null;
  let slides = [];
  let slideIndex = 0;
  let revealAnswers = false;

  function renderStage() {
    stageContent.replaceChildren();
    if (!slides.length) {
      stageContent.textContent = '这份讲义还没有可演示的内容。';
      return;
    }
    slideIndex = Math.max(0, Math.min(slideIndex, slides.length - 1));
    const slide = slides[slideIndex];
    const heading = document.createElement('h2');
    heading.textContent = slide.section.title || `第 ${slide.sectionIndex + 1} 部分`;
    stageContent.append(heading);
    if (slide.block) {
      stageContent.append(window.LectureRenderer.renderBlock(slide.block, {
        revealAnswers,
        linkKnowledge: false,
      }));
    }
    document.getElementById('stage-title').textContent = lecture.title;
    document.getElementById('stage-progress').textContent = `${slideIndex + 1} / ${slides.length}`;
    document.getElementById('stage-prev').disabled = slideIndex === 0;
    document.getElementById('stage-next').disabled = slideIndex === slides.length - 1;
    document.getElementById('stage-reveal').hidden = !slide.block || slide.block.type !== 'example';
  }

  function moveStage(offset) {
    if (!slides.length) return;
    slideIndex = Math.max(0, Math.min(slides.length - 1, slideIndex + offset));
    revealAnswers = false;
    renderStage();
  }

  function openStage() {
    slides = window.LectureRenderer.flatten(lecture.payload);
    slideIndex = 0;
    revealAnswers = false;
    stage.hidden = false;
    document.body.style.overflow = 'hidden';
    renderStage();
  }

  function closeStage() {
    stage.hidden = true;
    document.body.style.overflow = '';
  }

  classButton.addEventListener('click', openStage);
  document.getElementById('stage-close').addEventListener('click', closeStage);
  document.getElementById('stage-prev').addEventListener('click', () => moveStage(-1));
  document.getElementById('stage-next').addEventListener('click', () => moveStage(1));
  document.getElementById('stage-reveal').addEventListener('click', () => {
    revealAnswers = !revealAnswers;
    renderStage();
  });
  document.addEventListener('keydown', event => {
    if (stage.hidden) return;
    if (event.key === 'Escape') closeStage();
    if (event.key === 'ArrowLeft') moveStage(-1);
    if (event.key === 'ArrowRight' || event.key === ' ') {
      event.preventDefault();
      moveStage(1);
    }
  });

  try {
    if (!lectureRef) throw new Error('缺少讲义编号');
    const response = await fetch(`/api/v1/public/lectures/${encodeURIComponent(lectureRef)}`, {
      credentials: 'same-origin',
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `请求失败 (${response.status})`);
    lecture = data.lecture;
    document.title = `${lecture.title} · shuxue.icu`;
    document.getElementById('lecture-course').textContent =
      `${lecture.course_title}${lecture.course_grade_label ? ` · ${lecture.course_grade_label}` : ''}`;
    document.getElementById('lecture-title').textContent = lecture.title;
    document.getElementById('lecture-summary').textContent = lecture.summary || '';
    document.getElementById('lecture-meta').textContent =
      `版本 ${lecture.version} · 发布于 ${new Date(lecture.published_at).toLocaleString()}`;
    window.LectureRenderer.renderDocument(
      document.getElementById('lecture-document'),
      lecture.payload,
      { revealAnswers: true },
    );
    classButton.disabled = false;
  } catch (error) {
    document.getElementById('lecture-title').textContent = '讲义不可用';
    document.getElementById('lecture-summary').textContent = error.message;
  }
}());
