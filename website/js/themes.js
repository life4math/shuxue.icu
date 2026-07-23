/* ============================================================
   shuxue.icu  —  THEME SWITCHER
   Three themes: PKU / TSINGHUA / CYAN
   Default: CYAN (赛博青)
   ============================================================ */

const THEMES = {
  PKU: {
    name: 'PKU',
    label: 'PKU',
    desc: '北大红',
    accent: '#B91C1C',
    warn: '#DC2626',
    accentDim: 'rgba(185,28,28,.08)',
    accentLine: 'rgba(185,28,28,.25)',
    accentHover: 'rgba(185,28,28,.15)',
    difficulty: ['#450a0a', '#7f1d1d', '#B91C1C', '#DC2626', '#F87171'],
    level: { mastered: '#B91C1C', partial: '#DC2626', unmastered: '#ff453a' },
    priority: { P0: '#ff453a', P1: '#DC2626', P2: '#86868b' },
    legacy: {
      accentBlue: '#B91C1C', accentGreen: '#B91C1C', accentPurple: '#B91C1C',
      accentOrange: '#DC2626', accentYellow: '#DC2626'
    },
    chart: {
      color: ['#B91C1C', '#86868b', '#6e6e73', '#ff453a', '#DC2626'],
      ramp: ['#6e6e73', '#86868b', '#7f1d1d', '#B91C1C', '#F87171'],
      heat: ['#0a0a0a', '#1a1a1a', '#450a0a', '#7f1d1d', '#B91C1C'],
      line: '#B91C1C', areaFill: 'rgba(185,28,28,.10)', areaFill2: 'rgba(220,38,38,.06)'
    }
  },
  TSINGHUA: {
    name: 'TSINGHUA',
    label: 'TSINGHUA',
    desc: '清华紫',
    accent: '#7B2FA0',
    warn: '#A855F7',
    accentDim: 'rgba(123,47,160,.08)',
    accentLine: 'rgba(123,47,160,.25)',
    accentHover: 'rgba(123,47,160,.15)',
    difficulty: ['#3b0764', '#5b21b6', '#7B2FA0', '#A855F7', '#C084FC'],
    level: { mastered: '#7B2FA0', partial: '#A855F7', unmastered: '#ff453a' },
    priority: { P0: '#ff453a', P1: '#A855F7', P2: '#86868b' },
    legacy: {
      accentBlue: '#7B2FA0', accentGreen: '#7B2FA0', accentPurple: '#7B2FA0',
      accentOrange: '#A855F7', accentYellow: '#A855F7'
    },
    chart: {
      color: ['#7B2FA0', '#86868b', '#6e6e73', '#ff453a', '#A855F7'],
      ramp: ['#6e6e73', '#86868b', '#5b21b6', '#7B2FA0', '#C084FC'],
      heat: ['#0a0a0a', '#1a1a1a', '#3b0764', '#5b21b6', '#7B2FA0'],
      line: '#7B2FA0', areaFill: 'rgba(123,47,160,.10)', areaFill2: 'rgba(168,85,247,.06)'
    }
  },
  CYAN: {
    name: 'CYAN',
    label: 'CYAN',
    desc: '赛博青',
    accent: '#00d4ff',
    warn: '#0ea5e9',
    accentDim: 'rgba(0,212,255,.08)',
    accentLine: 'rgba(0,212,255,.25)',
    accentHover: 'rgba(0,212,255,.15)',
    difficulty: ['#003d5c', '#0284c7', '#00d4ff', '#38bdf8', '#7dd3fc'],
    level: { mastered: '#00d4ff', partial: '#0ea5e9', unmastered: '#ff453a' },
    priority: { P0: '#ff453a', P1: '#0ea5e9', P2: '#86868b' },
    legacy: {
      accentBlue: '#00d4ff', accentGreen: '#00d4ff', accentPurple: '#00d4ff',
      accentOrange: '#0ea5e9', accentYellow: '#0ea5e9'
    },
    chart: {
      color: ['#00d4ff', '#86868b', '#6e6e73', '#ff453a', '#0ea5e9'],
      ramp: ['#6e6e73', '#86868b', '#0284c7', '#00d4ff', '#7dd3fc'],
      heat: ['#0a0a0a', '#1a1a1a', '#003d5c', '#0284c7', '#00d4ff'],
      line: '#00d4ff', areaFill: 'rgba(0,212,255,.10)', areaFill2: 'rgba(14,165,233,.06)'
    }
  }
};

let currentTheme = THEMES.CYAN;
let themeUIInitialized = false;

function getSavedTheme() {
  try {
    const saved = localStorage.getItem('shuxue-theme');
    return THEMES[saved] ? saved : 'CYAN';
  } catch (_) {
    return 'CYAN';
  }
}

function saveTheme(themeName) {
  try {
    localStorage.setItem('shuxue-theme', themeName);
  } catch (_) {
    // 无痕模式或禁用存储时仍允许当前页面切换主题
  }
}

/* --- Apply Theme --- */
function applyTheme(themeName) {
  const t = THEMES[themeName];
  if (!t) return;
  currentTheme = t;

  const root = document.documentElement.style;
  root.setProperty('--accent', t.accent);
  root.setProperty('--accent-dim', t.accentDim);
  root.setProperty('--accent-line', t.accentLine);
  root.setProperty('--accent-hover', t.accentHover);
  root.setProperty('--warn', t.warn);
  root.setProperty('--accent-blue', t.legacy.accentBlue);
  root.setProperty('--accent-green', t.legacy.accentGreen);
  root.setProperty('--accent-purple', t.legacy.accentPurple);
  root.setProperty('--accent-orange', t.legacy.accentOrange);
  root.setProperty('--accent-yellow', t.legacy.accentYellow);

  // Update data.js color functions
  if (typeof setThemeColors === 'function') setThemeColors(t);

  // Update charts theme
  if (typeof registerCurrentTheme === 'function') registerCurrentTheme(t);

  // Redraw all ECharts instances
  if (typeof redrawAllCharts === 'function') redrawAllCharts();

  // Update about page accent display
  updateAccentDisplay(t);

  // Highlight active theme in switcher
  updateThemeSwitcher(t.name);

  // Highlight active theme in brand dropdown
  updateBrandDropdown(t.name);

  // Save to localStorage
  document.documentElement.dataset.theme = t.name;
  saveTheme(t.name);
}

/* --- Init Theme (restore from localStorage) --- */
function initTheme() {
  applyTheme(getSavedTheme());

  // Cross-tab sync: listen for localStorage changes from other tabs
  if (!window._shuxueThemeStorageBound) window.addEventListener('storage', (e) => {
    if (e.key === 'shuxue-theme' && e.newValue) {
      applyTheme(e.newValue);
    }
  });
  window._shuxueThemeStorageBound = true;
}

/* --- Theme Switcher UI (about page) --- */
function updateThemeSwitcher(activeName) {
  document.querySelectorAll('.theme-option').forEach(el => {
    const isActive = el.dataset.theme === activeName;
    el.classList.toggle('active', isActive);
    el.style.borderColor = isActive ? 'var(--accent)' : 'var(--line-strong)';
  });
}

function updateAccentDisplay(t) {
  const specVal = document.getElementById('spec-accent-val');
  if (specVal) specVal.textContent = t.accent;
}

/* --- Build Theme Switcher HTML (about page) --- */
function buildThemeSwitcher() {
  const container = document.getElementById('theme-switcher');
  if (!container) return;
  const order = ['PKU', 'TSINGHUA', 'CYAN'];
  container.innerHTML = order.map(name => {
    const t = THEMES[name];
    return `
      <button class="theme-option" data-theme="${name}" onclick="applyTheme('${name}')">
        <span class="theme-dot" style="background:${t.accent};"></span>
        <span class="theme-name">${t.label}</span>
      </button>`;
  }).join('');
  updateThemeSwitcher(currentTheme.name);
}

/* --- Brand Dropdown (navbar hover — JS-based for reliability) --- */
function buildBrandDropdown() {
  const container = document.getElementById('brand-dropdown');
  if (!container) return;
  const order = ['PKU', 'TSINGHUA', 'CYAN'];
  container.innerHTML = order.map(name => {
    const t = THEMES[name];
    return `
      <button class="brand-dropdown-item" data-theme="${name}" onclick="applyTheme('${name}')">
        <span class="brand-dropdown-dot" style="background:${t.accent};"></span>
        <span>${t.desc} · ${t.label}</span>
        <span class="brand-dropdown-check">✓</span>
      </button>`;
  }).join('');
  updateBrandDropdown(currentTheme.name);

  // JS hover control — much more reliable than pure CSS hover
  const trigger = document.querySelector('.nav-brand');
  setupDropdownHover(trigger, container);
}

function updateBrandDropdown(activeName) {
  document.querySelectorAll('.brand-dropdown-item').forEach(el => {
    el.classList.toggle('active', el.dataset.theme === activeName);
  });
}

/* --- Side Brand Dropdown (student.html hover — JS-based) --- */
function buildSideBrandDropdown() {
  const container = document.getElementById('side-brand-dropdown');
  if (!container) return;
  const order = ['PKU', 'TSINGHUA', 'CYAN'];
  container.innerHTML = order.map(name => {
    const t = THEMES[name];
    return `
      <button class="brand-dropdown-item" data-theme="${name}" onclick="applyTheme('${name}')">
        <span class="brand-dropdown-dot" style="background:${t.accent};"></span>
        <span>${t.desc} · ${t.label}</span>
        <span class="brand-dropdown-check">✓</span>
      </button>`;
  }).join('');
  updateBrandDropdown(currentTheme.name);

  // JS hover control
  const trigger = document.querySelector('.side-brand-wrap');
  setupDropdownHover(trigger, container);
}

/* --- Shared Dropdown Hover Controller --- */
function setupDropdownHover(trigger, dropdown) {
  if (!trigger || !dropdown || dropdown.dataset.hoverBound === 'true') return;
  dropdown.dataset.hoverBound = 'true';
  let closeTimeout = null;
  const CLOSE_DELAY = 250; // ms buffer to allow mouse travel from trigger to dropdown

  function openDropdown() {
    clearTimeout(closeTimeout);
    dropdown.classList.add('open');
    trigger.setAttribute('aria-expanded', 'true');
  }

  function scheduleClose() {
    closeTimeout = setTimeout(() => {
      dropdown.classList.remove('open');
      trigger.setAttribute('aria-expanded', 'false');
    }, CLOSE_DELAY);
  }

  trigger.setAttribute('aria-haspopup', 'menu');
  trigger.setAttribute('aria-expanded', 'false');
  if (!trigger.hasAttribute('tabindex')) trigger.tabIndex = 0;
  dropdown.setAttribute('role', 'menu');
  trigger.addEventListener('mouseenter', openDropdown);
  trigger.addEventListener('mouseleave', scheduleClose);
  trigger.addEventListener('focusin', openDropdown);
  trigger.addEventListener('focusout', scheduleClose);
  dropdown.addEventListener('mouseenter', () => clearTimeout(closeTimeout));
  dropdown.addEventListener('mouseleave', scheduleClose);
  dropdown.addEventListener('focusin', openDropdown);
  dropdown.addEventListener('focusout', scheduleClose);
  dropdown.addEventListener('click', scheduleClose);
  trigger.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      dropdown.classList.remove('open');
      trigger.setAttribute('aria-expanded', 'false');
      trigger.focus();
    } else if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      openDropdown();
      dropdown.querySelector('button')?.focus();
    }
  });
}

/* --- Standalone bootstrap: theme UI must not depend on app.js succeeding --- */
function initThemeUI() {
  if (themeUIInitialized) return;
  themeUIInitialized = true;
  initTheme();
  buildThemeSwitcher();
  buildBrandDropdown();
  buildSideBrandDropdown();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initThemeUI, { once: true });
} else {
  initThemeUI();
}

