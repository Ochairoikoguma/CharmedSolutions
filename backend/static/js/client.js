
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
  // Keep deletion disabled until it is connected to Django.
  dom.del.disabled = true;
}
async function renderHistory() {
  const c = isDraft ? null : current();

  if (!c) {
    dom.history.innerHTML = note(
      'Select a client to see their reports.'
    );
    return;
  }

  const clientId = c.id;

  dom.history.innerHTML = note('Loading report history...');

  try {
    const response = await fetch(
      `/api/clients/${clientId}/reports/`,
      { cache: 'no-store' }
    );

    if (!response.ok) {
      throw new Error('Could not load report history.');
    }

    const data = await response.json();

    // Prevent an old request from updating a newly selected client.
    if (isDraft || curId != clientId) return;

    if (data.reports.length === 0) {
      dom.history.innerHTML = note('No saved reports yet.');
      return;
    }

    dom.history.innerHTML = data.reports.map(r => `
      <a
        href="/reports/history/${r.id}/download/"
        class="report-history-item"
      >
        <span>${label(r.period)}</span>
      </a>
    `).join('');

  } catch (error) {
    if (!isDraft && curId == clientId) {
      dom.history.innerHTML = note(
        'Unable to load report history.'
      );
    }
  }
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
dom.form.addEventListener('submit', async e => {
  e.preventDefault();

  const c = current();

  if (!c || isDraft) {
    return toast('Select an existing client first.', 'error');
  }

  const name = dom.name.value.trim().replace(/\s+/g, ' ');
  const rate = dom.rate.value.trim();

  if (!name) {
    return toast('Enter a client name.', 'error');
  }

  if (rate !== '' && (
    !/^\d{1,2}(\.\d{1,2})?$/.test(rate) ||
    Number(rate) > 99.99
  )) {
    return toast('Commission rate must be between 0 and 99.99.', 'error');
  }

  const saveButton = dom.form.querySelector('button[type="submit"]');
  saveButton.disabled = true;

  try {
    const response = await fetch(`/api/clients/${c.id}/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': dom.form.querySelector(
          '[name=csrfmiddlewaretoken]'
        ).value
      },
      body: JSON.stringify({
        name: name,
        rate: rate === '' ? null : rate
      })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Could not save client.');
    }

    c.name = data.name;
    c.rate = data.rate === null ? null : Number(data.rate);

    renderClients();
    toast('Client saved to database.');

  } catch (error) {
    toast(error.message, 'error');
  } finally {
    saveButton.disabled = false;
  }
});
dom.del.addEventListener('click', () => {
  const c = current(); if (!c) return;
  if (!confirm(`Confirm Client Delete\n\nDelete "${c.name}" along with all of their accounts and transactions? This cannot be undone.`)) return;
  S.clients = S.clients.filter(x => x.id != c.id);
  ['accounts', 'payments', 'costs', 'reports'].forEach(k => S[k] = S[k].filter(x => x.clientId != c.id));
  curId = null; save(); renderClients(); toast('Client deleted.');
});

async function loadDatabaseClients() {
  // Disable editing until these buttons are connected to Django.
  dom.form.querySelector('button[type="submit"]').disabled = true;
  dom.create.disabled = true;
  dom.del.disabled = true;
  dom.name.readOnly = false;
  dom.rate.readOnly = false;
  dom.rate.max = '99.99';

  dom.list.textContent = "Loading clients...";

  try {
    // Request the actual clients stored in MySQL.
    const response = await fetch("/api/clients/", {
      cache: "no-store",
    });

    if (!response.ok) {
      throw new Error("Could not load clients from the database.");
    }

    const data = await response.json();

    // Replace browser sample data in memory.
    // Do not combine sample transactions with database client IDs.
    S = {
      clients: data.clients.map(client => ({
        ...client,
        rate: client.rate === null ? null : Number(client.rate),
      })),
      accounts: [],
      payments: [],
      costs: [],
      reports: [],
      nextId: 0,
    };

    isDraft = false;
    renderClients();

    // Client selection calls renderForm again, so keep Delete disabled.
    dom.del.disabled = true;
    dom.form.querySelector('button[type="submit"]').disabled = false;
    toast("Database clients loaded. Editing and history are not connected yet.", "info");
    
  } catch (error) {
    dom.list.textContent = "Unable to load clients.";
    toast(error.message, "error");
  }
}

loadDatabaseClients();