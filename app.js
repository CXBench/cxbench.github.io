'use strict';

const menu = document.querySelector('.menu-toggle');
const navigation = document.querySelector('#navigation');
menu.addEventListener('click', () => {
  const expanded = menu.getAttribute('aria-expanded') !== 'true';
  menu.setAttribute('aria-expanded', String(expanded));
  menu.setAttribute('aria-label', expanded ? 'Close navigation' : 'Open navigation');
  navigation.classList.toggle('open', expanded);
});
navigation.addEventListener('click', (event) => {
  if (!event.target.closest('a')) return;
  menu.setAttribute('aria-expanded', 'false');
  menu.setAttribute('aria-label', 'Open navigation');
  navigation.classList.remove('open');
});
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && navigation.classList.contains('open')) {
    menu.click();
    menu.focus();
  }
});

document.querySelectorAll('[data-lens]').forEach(button => {
  button.addEventListener('click', () => {
    const hybrid = button.dataset.lens === 'hybrid';
    document.querySelectorAll('[data-lens]').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
    document.querySelector('#trace-pair').classList.toggle('hybrid', hybrid);
    document.querySelector('.verdict-a').textContent = hybrid ? 'Both-pass' : 'Outcome pass';
    document.querySelector('.verdict-b').textContent = hybrid ? 'False-pass' : 'Outcome pass';
    document.querySelector('#example-insight').textContent = hybrid
      ? 'Trace B is a false-pass: the business outcome is correct, but the required disclosure is missing.'
      : 'Both traces reach the same final state. An outcome-only check accepts both.';
  });
});

const percent = (value, denominator) => `${(value / denominator * 100).toFixed(2)}%`;
fetch('assets/data/results.json').then(response => {
  if (!response.ok) throw new Error('Results unavailable');
  return response.json();
}).then(data => {
  const chart = document.querySelector('#model-chart');
  function renderChart(sort = 'both') {
    chart.replaceChildren();
    const rows = [...data.models].sort((a, b) => sort === 'name' ? a.name.localeCompare(b.name) : b[sort] - a[sort]);
    for (const model of rows) {
      const row = document.createElement('div');
      row.className = 'model-row';
      const name = document.createElement('span');
      name.className = 'model-name';
      name.textContent = model.name;
      const bars = document.createElement('div');
      bars.className = 'model-bars';
      for (const metric of ['outcome', 'both']) {
        const bar = document.createElement('div');
        bar.className = `model-bar ${metric}`;
        bar.style.width = percent(model[metric], data.protocol.records_per_model);
        const label = document.createElement('span');
        label.textContent = percent(model[metric], data.protocol.records_per_model);
        bar.setAttribute('aria-label', `${metric === 'outcome' ? 'Outcome-pass' : 'Both-pass'}: ${label.textContent}`);
        bar.append(label);
        bars.append(bar);
      }
      row.append(name, bars);
      chart.append(row);
    }
  }
  renderChart();
  document.querySelector('#result-sort').addEventListener('change', event => renderChart(event.target.value));

  const tabs = [...document.querySelectorAll('[data-domain]')];
  function selectDomain(tab) {
    const domain = data.domains.find(item => item.id === tab.dataset.domain);
    for (const item of tabs) {
      item.setAttribute('aria-selected', String(item === tab));
      item.tabIndex = item === tab ? 0 : -1;
    }
    document.querySelector('#domain-panel').setAttribute('aria-labelledby', tab.id);
    document.querySelector('#domain-kicker').textContent = `${domain.name.toUpperCase()} / 140 EVALUATIONS`;
    document.querySelector('#domain-title').textContent = domain.title;
    document.querySelector('#domain-description').textContent = domain.description;
    for (const metric of ['outcome', 'both']) {
      const value = percent(domain[metric], data.protocol.records_per_domain);
      document.querySelector(`#domain-${metric}`).textContent = value;
      document.querySelector(`#domain-${metric}-bar`).style.width = value;
    }
  }
  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => selectDomain(tab));
    tab.addEventListener('keydown', event => {
      let next;
      if (['ArrowRight', 'ArrowDown'].includes(event.key)) next = (index + 1) % tabs.length;
      if (['ArrowLeft', 'ArrowUp'].includes(event.key)) next = (index + tabs.length - 1) % tabs.length;
      if (event.key === 'Home') next = 0;
      if (event.key === 'End') next = tabs.length - 1;
      if (next === undefined) return;
      event.preventDefault();
      selectDomain(tabs[next]);
      tabs[next].focus();
    });
  });
}).catch(() => {
  document.querySelector('#model-chart').textContent = 'The chart could not load. Exact results are available in the table below.';
  document.querySelector('.result-detail').open = true;
  document.querySelector('#result-sort').disabled = true;
});

document.querySelector('#copy-citation').addEventListener('click', async event => {
  const button = event.currentTarget;
  const citation = document.querySelector('#citation');
  try {
    await navigator.clipboard.writeText(citation.textContent);
    button.textContent = 'Copied';
    document.querySelector('#copy-status').textContent = 'Citation copied to clipboard.';
  } catch {
    const selection = window.getSelection();
    const range = document.createRange();
    range.selectNodeContents(citation);
    selection.removeAllRanges();
    selection.addRange(range);
    button.textContent = 'Text selected';
    document.querySelector('#copy-status').textContent = 'Citation selected. Use your browser copy command.';
  }
  setTimeout(() => { button.textContent = 'Copy BibTeX'; }, 2500);
});

if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
  document.querySelector('.trajectory').pauseAnimations();
}
