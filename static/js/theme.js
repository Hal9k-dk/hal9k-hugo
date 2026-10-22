'use strict';
// Loaded synchronously in <head> so a saved theme is applied before first paint.
(() => {
  const root = document.documentElement;
  const system = window.matchMedia('(prefers-color-scheme: dark)');
  let choice = null;
  try {
    const saved = localStorage.getItem('hal9k-theme');
    if (saved === 'light' || saved === 'dark') choice = saved;
  } catch (_) { /* Theme switching still works when storage is unavailable. */ }
  if (choice) root.dataset.theme = choice;
  const isDark = () => (choice || (system.matches ? 'dark' : 'light')) === 'dark';
  const updateButton = () => {
    const button = document.getElementById('theme-toggle');
    if (!button) return;
    button.hidden = false;
    button.setAttribute('aria-pressed', String(isDark()));
    button.title = isDark() ? 'Skift til lyst tema' : 'Skift til mørkt tema';
    button.querySelector('[data-theme-icon]').textContent = isDark() ? '☾' : '☀';
  };
  document.addEventListener('DOMContentLoaded', () => {
    const button = document.getElementById('theme-toggle');
    if (!button) return;
    updateButton();
    button.addEventListener('click', () => {
      choice = isDark() ? 'light' : 'dark';
      root.dataset.theme = choice;
      try { localStorage.setItem('hal9k-theme', choice); } catch (_) {}
      updateButton();
    });
  });
  system.addEventListener('change', updateButton);
  window.addEventListener('storage', event => {
    if (event.key !== 'hal9k-theme' && event.key !== null) return;
    choice = event.newValue === 'dark' || event.newValue === 'light' ? event.newValue : null;
    if (choice) root.dataset.theme = choice;
    else delete root.dataset.theme;
    updateButton();
  });
})();
