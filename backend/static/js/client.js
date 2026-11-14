
if (typeof S === 'undefined') {
  const m = document.getElementById('clientMessage');
  if (m) { m.className = 'message message-error'; m.textContent = 'main.js must be loaded before client.js.'; }
  throw new Error('main.js must be loaded before client.js');
}

const dom = {
  list: $('#clientList'), form: $('#clientForm'), id: $('#clientId'), name: $('#clientName'),
  rate: $('#commissionRate'), date: $('#dateAdded'), del: $('#deleteClientBtn'),
  create: $('#createClientBtn'), history: $('#reportHistory')
};
let curId = +new URLSearchParams(location.search).get('id') || null;   // /client/?id=3 opens that client
let isDraft = false;                                                    // true while filling in a new client
const sortedClients = () => [...S.clients].sort((a, b) => a.name.localeCompare(b.name));
const current = () => S.clients.find(x => x.id == curId);
const note = t => `<p style="padding:12px;margin:0;color:#5A6266">${t}</p>`;

function renderList() {
  dom.list.innerHTML = sortedClients().map(c =>
    `<button type="button" class="client-name ${!isDraft && c.id == curId ? 'active' : ''}" data-client="${c.id}">${esc(c.name) || '(unnamed)'}</button>`
  ).join('') || note('No clients yet.');
}
function renderForm() {
  const c = isDraft ? null : current();
  dom.id.value = isDraft ? 'Assigned on save' : c ? c.id : '';
  dom.name.value = c ? c.name : '';
  dom.rate.value = c && c.rate != null ? c.rate : '';
  dom.date.value = isDraft ? mdy(iso(new Date())) : c ? mdy(c.created) : '';
  dom.del.disabled = !c;
}
function renderHistory() {
  const c = isDraft ? null : current();
  if (!c) { dom.history.innerHTML = note(isDraft ? 'Save the client to start building report history.' : 'Select a client to see their reports.'); return; }
  const reports = S.reports.filter(r => r.clientId == c.id).sort((a, b) => b.period.localeCompare(a.period));
  dom.history.innerHTML = reports.map(r =>
    `<a href="#" class="report-history-item" data-period="${r.period}"><span>${label(r.period)}</span></a>`
  ).join('') || note('No reports yet. Generate one from the dashboard.');
}
function renderClients() {
  if (!isDraft && !current()) curId = sortedClients()[0]?.id ?? null;   // default to the first client
  renderList(); renderForm(); renderHistory();
}

/* ---------- Events ---------- */
dom.rate.step = '0.01';                                                 // allow rates like 12.5

dom.list.addEventListener('click', e => {
  const b = e.target.closest('.client-name'); if (!b) return;
  isDraft = false; curId = +b.dataset.client; renderClients();
});
dom.create.addEventListener('click', () => {
  isDraft = true; curId = null; renderClients(); dom.name.focus();
});
dom.form.addEventListener('submit', e => {
  e.preventDefault();
  const name = dom.name.value.trim().replace(/\s+/g, ' ');
  const rate = dom.rate.value === '' ? null : +dom.rate.value;
  if (!name) return toast('Enter a client name.', 'error');
  if (S.clients.some(x => norm(x.name) == norm(name) && x.id != curId)) return toast('A client with that name already exists.', 'error');
  if (rate !== null && (isNaN(rate) || rate < 0 || rate > 100)) return toast('Commission rate must be between 0 and 100.', 'error');
  if (isDraft) {
    const c = { id: id(), name, rate, created: iso(new Date()) };
    S.clients.push(c); curId = c.id; isDraft = false;
  } else {
    const c = current(); c.name = name; c.rate = rate;
  }
  save(); renderClients(); toast('Client saved.');
});
dom.del.addEventListener('click', () => {
  const c = current(); if (!c) return;
  if (!confirm(`Confirm Client Delete\n\nDelete "${c.name}" along with all of their accounts and transactions? This cannot be undone.`)) return;
  S.clients = S.clients.filter(x => x.id != c.id);
  ['accounts', 'payments', 'costs', 'reports'].forEach(k => S[k] = S[k].filter(x => x.clientId != c.id));
  curId = null; save(); renderClients(); toast('Client deleted.');
});
dom.history.addEventListener('click', async e => {
  const a = e.target.closest('.report-history-item'); if (!a) return;
  e.preventDefault();
  const r = S.reports.find(x => x.clientId == curId && x.period == a.dataset.period); if (!r) return;
  const w = window.open('', '_blank');                                  // open first so the popup isn't blocked
  const blob = await (await fetch(r.data)).blob();
  w.location = URL.createObjectURL(blob);
});

renderClients();