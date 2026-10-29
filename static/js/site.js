'use strict';
let indexPromise;
// A failed load is forgotten so the next search can retry it. The lowercased
// search text is built once here rather than on every keystroke.
const loadIndex = () => indexPromise ||= fetch('/index.json').then(r => { if (!r.ok) throw new Error('Index unavailable'); return r.json(); }).then(index => { index.articles.forEach(a => { a.haystack = (a.title + ' ' + a.text).toLocaleLowerCase('da'); }); return index; }).catch(error => { indexPromise = undefined; throw error; });
const query = new URLSearchParams(location.search);
const legacyId = query.get('p') || query.get('page_id') || query.get('attachment_id');
if (legacyId && /^\d+$/.test(legacyId)) {
  fetch('/wordpress-ids.json').then(r => r.json()).then(ids => { const target = ids[legacyId]; if (target && target.startsWith('/')) location.replace(target + location.hash); }).catch(() => {});
}
// Reimplementation of the battery-life calculator from the original article.
const calculator = document.querySelector('.calculator');
if (calculator) {
  const field = id => document.getElementById(id);
  const duration = hours => {
    if (!Number.isFinite(hours) || hours < 0) return '—';
    const mins = Math.floor(hours * 60);
    return `${Math.floor(mins / 1440)} days ${Math.floor(mins / 60) % 24} hours ${mins % 60} mins`;
  };
  const recalc = () => {
    field('deeplifetime').textContent = duration(Number(field('capacity').value) / Number(field('deepconsumption').value));
    field('lightlifetime').textContent = duration(Number(field('capacity').value) / Number(field('lightconsumption').value));
  };
  calculator.addEventListener('input', event => {
    if (event.target.id === 'numbatts') {
      field('capacity').value = Number(event.target.value) * 2000;
      const image = field('batteryimgs').querySelector('img');
      if (image) field('batteryimgs').replaceChildren(...Array.from({length: Number(event.target.value)}, () => image.cloneNode()));
    }
    if (event.target.id === 'deepinterval') field('deepconsumption').value = 1 + 100 * 10 / (Number(event.target.value) * 60);
    recalc();
  });
  field('deepconsumption').value = 1 + 100 * 10 / (Number(field('deepinterval').value) * 60);
  recalc();
}
const search = document.getElementById('search');
if (search) {
  let timer;
  search.addEventListener('input', () => {
    clearTimeout(timer);
    timer = setTimeout(async () => {
      const value = search.value.trim().toLocaleLowerCase('da');
      const results = document.getElementById('search-results');
      const status = document.getElementById('search-status');
      results.replaceChildren(); status.textContent = '';
      if (value.length < 2) return;
      try {
        const index = await loadIndex();
        if (value !== search.value.trim().toLocaleLowerCase('da')) return;
        const words = value.split(/\s+/);
        const matches = index.articles.filter(a => words.every(w => a.haystack.includes(w)));
        status.textContent = matches.length + ' artikler fundet';
        matches.forEach(a => { const li = document.createElement('li'); const link = document.createElement('a'); link.href = a.url; link.textContent = a.title; li.append(link); results.append(li); });
      } catch (_) { status.textContent = 'Søgning kunne ikke indlæses. Prøv igen.'; }
    }, 180);
  });
}
