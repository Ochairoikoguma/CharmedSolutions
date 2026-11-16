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
let clientBusy = false;
let clientReady = false;
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
  dom.id.value = isDraft ? 'Assigned when Saved' : c ? c.id : '';
  dom.name.value = c ? c.name : '';
  dom.rate.value = c && c.rate != null ? c.rate : '';
  dom.date.value = c ? mdy(c.created) : mdy(iso(new Date()));
  dom.form.querySelector('button[type="submit"]').textContent =
    isDraft ? 'Create Client' : 'Save Changes';
  setClientBusy(clientBusy);
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

// Keep edits, selection, creation and deletion from overlapping.
function setClientBusy(value) {
  clientBusy = value;
  dom.del.disabled = value || !clientReady || isDraft || !current();
  dom.create.disabled = value || !clientReady;
  dom.form.querySelector('button[type="submit"]').disabled =
    value || !clientReady || (!isDraft && !current());
  dom.name.readOnly = value || !clientReady;
  dom.rate.readOnly = value || !clientReady;
}

async function clientResponse(response) {
  const data = await response.json().catch(() => ({ error: 'The server returned an unexpected response. Check the server terminal.' }));
  if (!response.ok) throw new Error(data.error || 'Client request failed.');
  return data;
}

/* ---------- Events ---------- */
dom.rate.step = '0.01';                                                 // allow rates like 12.5

dom.list.addEventListener('click', e => {
  if (clientBusy || !clientReady) return;
  const b = e.target.closest('.client-name'); if (!b) return;
  isDraft = false; curId = +b.dataset.client; renderClients();
});
dom.create.addEventListener('click', () => {
  if (clientBusy || !clientReady) return;
  isDraft = true; curId = null; renderClients(); dom.name.focus();
});

dom.form.addEventListener('submit', async e => {
  e.preventDefault();
  if (clientBusy || !clientReady) return;

  const creating = isDraft;
  const c = creating ? null : current();

  if (!creating && !c) {
    return toast('Select a client first.', 'error');
  }

  const name = dom.name.value.trim().replace(/\s+/g, ' ');
  const rate = dom.rate.value.trim();

  if (!name) {
    return toast('Enter a client name.', 'error');
  }

  if (name.length > 150) {
    return toast('Client name is too long.', 'error');
  }

  if (rate !== '' && (
    !/^\d{1,2}(\.\d{1,2})?$/.test(rate) ||
    Number(rate) > 99.99
  )) {
    return toast('Commission rate must be between 0 and 99.99.', 'error');
  }

  const saveButton = dom.form.querySelector('button[type="submit"]');
  setClientBusy(true);

  try {
    const url = creating
      ? '/api/clients/create/'
      : `/api/clients/${c.id}/`;

    const response = await fetch(url, {
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

    if (creating) {
      // MySQL assigns the new client ID.
      S.clients.push({
        id: data.id,
        name: data.name,
        rate: data.rate === null ? null : Number(data.rate),
        created: data.created
      });

      curId = data.id;
      isDraft = false;

    } else {
      // Update the existing client on the page.
      c.name = data.name;
      c.rate = data.rate === null ? null : Number(data.rate);
    }

    renderClients();

    toast(creating
      ? 'New client created in MySQL.'
      : 'Client saved to database.');

  } catch (error) {
    toast(error.message, 'error');
  } finally {
    setClientBusy(false);
  }
});

dom.del.addEventListener('click', async () => {
  const c = current();
  if (!c || isDraft || clientBusy || !clientReady) return;
  setClientBusy(true);
  try {
    const preview = await clientResponse(await fetch(`/api/clients/${c.id}/delete-preview/`, {
      cache: 'no-store', credentials: 'same-origin'
    }));
    const counts = preview.counts;
    const approved = confirm(
      `Permanently delete "${preview.name}"?\n\n` +
      `This deletes ${counts.accounts} accounts, ${counts.payments} payments, ` +
      `${counts.costs} costs, and ${counts.reports} saved PDF reports.\n\n` +
      'Import history is retained. This cannot be undone.'
    );
    if (!approved) return;
    const token = dom.form.querySelector('[name=csrfmiddlewaretoken]')?.value;
    if (!token) throw new Error('Security token missing. Refresh the page.');
    await clientResponse(await fetch(`/api/clients/${c.id}/delete/`, {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': token },
      body: JSON.stringify({ confirmation: preview.confirmation })
    }));
    // Refresh from MySQL instead of changing the old browser-only demo store.
    curId = null;
    isDraft = false;
    const loaded = await loadDatabaseClients();
    if (loaded) toast('Client and associated accounting records deleted.');
  } catch (error) {
    toast(error.message, 'error');
  } finally {
    setClientBusy(false);
  }
});

async function loadDatabaseClients() {
  // Disable editing while the database client list loads.
  clientReady = false;
  setClientBusy(true);
  dom.form.querySelector('button[type="submit"]').disabled = true;
  dom.create.disabled = true;
  dom.del.disabled = true;
  dom.name.readOnly = true;
  dom.rate.readOnly = true;
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
    clientReady = true;
    renderClients();
    return true;
    
  } catch (error) {
    dom.list.textContent = "Unable to load clients.";
    toast(error.message, "error");
    return false;
  } finally {
    setClientBusy(false);
  }
}

loadDatabaseClients();
