// ===== shuxue.icu — MULTI-THEME CHARTS =====
// Three themes: PKU / TSINGHUA / CYAN — reads from currentTheme (themes.js)

const STATIC = {
  axis:    'rgba(255,255,255,.10)',
  split:   'rgba(255,255,255,.08)',
  label:   '#6e6e73',
  text:    '#ffffff',
  tipBg:   '#0a0a0a',
  font:    '"Space Grotesk","Inter","PingFang SC","Microsoft YaHei",system-ui,sans-serif'
};

function baseOption() {
  return {
    backgroundColor: 'transparent',
    textStyle: { color: STATIC.text, fontFamily: STATIC.font },
    title: { textStyle: { color: STATIC.text, fontFamily: STATIC.font } }
  };
}

function tipOpt(extra) {
  return Object.assign({
    backgroundColor: STATIC.tipBg,
    borderColor: currentTheme.accentLine,
    borderWidth: 1,
    textStyle: { color: STATIC.text, fontFamily: STATIC.font, fontSize: 12 },
    extraCssText: 'box-shadow:none;border-radius:0;'
  }, extra || {});
}

function axisOpt() {
  return {
    axisLine: { lineStyle: { color: STATIC.axis, width: 1 } },
    axisTick: { lineStyle: { color: STATIC.axis } },
    axisLabel: { color: STATIC.label, fontFamily: STATIC.font, fontSize: 10 },
    splitLine: { lineStyle: { color: STATIC.split, type: 'dashed' } }
  };
}

function legendOpt(data) {
  return {
    data: data,
    textStyle: { color: STATIC.label, fontFamily: STATIC.font, fontSize: 10 },
    icon: 'rect',
    itemWidth: 10,
    itemHeight: 10,
    itemGap: 12,
    bottom: 0
  };
}

let _resizeChartIds = new Set();
let _charts = {};

function initChart(id, option) {
  const el = document.getElementById(id);
  if (!el) return null;
  // dispose existing chart if present
  if (_charts[id]) { _charts[id].dispose(); }
  const chart = echarts.init(el, null, { renderer: 'canvas' });
  chart.setOption(option);
  const handler = () => chart.resize();
  window.addEventListener('resize', handler);
  chart._resizeHandler = handler;
  _charts[id] = chart;
  return chart;
}

function redrawAllCharts() {
  // Re-render all charts with current theme
  const student = getSelectedStudent();
  if (student) {
    initRadarChart(student);
    initStudentTrendChart(student);
    initDifficultyBarChart(student);
  }
  // Dashboard charts
  if (typeof renderDashboardCharts === 'function') renderDashboardCharts();
}

function registerCurrentTheme(theme) {
  // Called by themes.js — currentTheme is already set, charts read from it
}

// ===== Student Analytics Charts =====

function initRadarChart(student) {
  const T = currentTheme.chart;
  return initChart('chart-radar', Object.assign(baseOption(), {
    tooltip: tipOpt({}),
    radar: {
      indicator: student.moduleScores.map(m => ({ name: m.module, max: 100 })),
      shape: 'polygon',
      splitNumber: 4,
      axisName: { color: STATIC.label, fontFamily: STATIC.font, fontSize: 10 },
      splitLine: { lineStyle: { color: STATIC.split, type: 'dashed' } },
      splitArea: { areaStyle: { color: ['rgba(255,255,255,0.01)', 'rgba(255,255,255,0.02)', 'rgba(255,255,255,0.03)', 'rgba(255,255,255,0.04)'] } },
      axisLine: { lineStyle: { color: STATIC.axis } }
    },
    series: [{
      type: 'radar',
      data: [
        { name: student.name, value: student.moduleScores.map(m => m.score),
          lineStyle: { color: T.color[0], width: 2 }, itemStyle: { color: T.color[0] },
          areaStyle: { color: T.areaFill }, symbol: 'circle', symbolSize: 4 },
        { name: 'MASTER 80', value: student.moduleScores.map(() => 80),
          lineStyle: { color: STATIC.label, width: 1, type: 'dashed' }, itemStyle: { color: STATIC.label }, symbol: 'none' },
        { name: 'ALERT 60', value: student.moduleScores.map(() => 60),
          lineStyle: { color: '#ff453a', width: 1, type: 'dashed' }, itemStyle: { color: '#ff453a' }, symbol: 'none' }
      ]
    }],
    legend: legendOpt([student.name, 'MASTER 80', 'ALERT 60'])
  }));
}

function initStudentTrendChart(student) {
  const T = currentTheme.chart;
  return initChart('chart-student-trend', Object.assign(baseOption(), {
    tooltip: tipOpt({
      trigger: 'axis',
      formatter: (params) => { const p = params[0]; return `${p.name}<br/>ACC: ${p.value}%`; }
    }),
    grid: { left: 48, right: 16, top: 16, bottom: 36 },
    xAxis: Object.assign({ type: 'category', data: student.accuracyTrend.map(d => d.date) }, axisOpt(), { axisLabel: { color: STATIC.label, fontFamily: STATIC.font, fontSize: 10, rotate: 45 } }),
    yAxis: Object.assign({ type: 'value', min: Math.max(0, Math.min(...student.accuracyTrend.map(d => d.accuracy)) - 10), max: 100, axisLine: { show: false } }, axisOpt(), { axisLabel: { color: STATIC.label, fontFamily: STATIC.font, fontSize: 10, formatter: '{value}%' } }),
    series: [{
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 4,
      lineStyle: { width: 2, color: T.color[0] },
      itemStyle: { color: T.color[0], borderColor: '#0a0a0a', borderWidth: 1 },
      areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: T.areaFill }, { offset: 1, color: T.areaFill2 }] } },
      data: student.accuracyTrend.map(d => d.accuracy),
      markLine: {
        silent: true,
        lineStyle: { color: T.color[0], type: 'dashed', width: 1 },
        data: [{ yAxis: 80, label: { show: true, position: 'end', formatter: 'MASTER', color: T.color[0], fontSize: 9, fontFamily: STATIC.font } }]
      }
    }]
  }));
}

function initDifficultyBarChart(student) {
  const T = currentTheme.chart;
  return initChart('chart-difficulty-bar', Object.assign(baseOption(), {
    tooltip: tipOpt({
      trigger: 'axis',
      formatter: (params) => {
        const p = params[0];
        const d = student.difficultyAccuracy[p.dataIndex];
        return `${d.label} LV.${d.difficulty}<br/>ACC: ${d.accuracy}%<br/>COUNT: ${d.count}`;
      }
    }),
    grid: { left: 48, right: 16, top: 20, bottom: 30 },
    xAxis: Object.assign({ type: 'category', data: student.difficultyAccuracy.map(d => d.label + '\nLV.' + d.difficulty) }, axisOpt(), { axisLabel: { color: STATIC.label, fontFamily: STATIC.font, fontSize: 9, interval: 0 } }),
    yAxis: Object.assign({ type: 'value', min: 0, max: 100, axisLine: { show: false } }, axisOpt(), { axisLabel: { color: STATIC.label, fontFamily: STATIC.font, fontSize: 10, formatter: '{value}%' } }),
    series: [{
      type: 'bar',
      barWidth: 36,
      itemStyle: { borderRadius: 0, color: (params) => T.ramp[params.dataIndex] || STATIC.label },
      label: { show: true, position: 'top', color: STATIC.text, fontFamily: STATIC.font, fontSize: 10, formatter: '{c}%' },
      data: student.difficultyAccuracy.map(d => d.accuracy)
    }]
  }));
}
