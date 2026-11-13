
/* ---------- Config ---------- */
const FIRM = { name: 'Your Law Firm, PLLC', addr: '123 Main Street, Houston, TX 77002' };
const PAGE_SIZE = 10;
const KEY = 'remittance_db';

/* ---------- Data layer ---------- */
let S = { clients: [], accounts: [], payments: [], costs: [], reports: [], nextId: 100 };
const id = () => ++S.nextId;
function save() {
  try { localStorage.setItem(KEY, JSON.stringify(S)); }
  catch (e) { toast('Could not save: browser storage is full.', 'error'); }
}
function load() {
  try { const r = localStorage.getItem(KEY); if (r) { S = JSON.parse(r); return true; } } catch (e) {}
  return false;
}

/* ---------- Helpers ---------- */
const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const money = c => (c / 100).toLocaleString('en-US', { style: 'currency', currency: 'USD' });
const pad = n => String(n).padStart(2, '0');
const iso = d => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
const mdy = s => { const [y, m, d] = s.split('-'); return `${m}/${d}/${y}`; };
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const label = p => `${MONTHS[+p.slice(5, 7) - 1]}, ${p.slice(0, 4)}`;
const mmyyyy = p => `${p.slice(5, 7)}/${p.slice(0, 4)}`;
const nextMonth = p => { let y = +p.slice(0, 4), m = +p.slice(5, 7) + 1; if (m > 12) { m = 1; y++; } return `${y}-${pad(m)}-01`; };
const PERIOD = iso(new Date()).slice(0, 7) + '-01';
const norm = s => s.trim().replace(/\s+/g, ' ').toLowerCase();
const sum = a => a.reduce((x, y) => x + y.amount, 0);
function toast(t, type = 'success') {            // type: success | error | info
  const e = $('#messageBox') || $('#clientMessage') || $('#toast'); if (!e) return;
  e.textContent = t; e.className = 'message message-' + (type == 'info' ? 'loading' : type);
  clearTimeout(toast.t); toast.t = setTimeout(() => e.className = 'message hidden', 4000);
}
function initShell(active) { const e = $('#t-' + active); if (e) e.classList.add('active-nav'); }

/* ---------- Per-client numbers for the current period ---------- */
function stats(c, p = PERIOD) {
  const rec = sum(S.payments.filter(x => x.clientId == c.id && x.date.slice(0, 7) == p.slice(0, 7)));
  const cost = sum(S.costs.filter(x => x.clientId == c.id && x.due == p));
  const comm = c.rate == null ? 0 : Math.round(rec * c.rate / 100);
  return { rec, cost, comm, net: rec - cost - comm, red: cost * 5 > rec };
}

/* ---------- Rollover ---------- */
function rollover(ids) {
  let n = 0;
  ids.forEach(cid => {
    const c = S.clients.find(x => x.id == cid);
    if (!c || !stats(c).red) return;                 // does nothing to non-red clients
    const cap = Math.floor(stats(c).rec / 5);        // 20% ceiling, whole cents, rounded down
    let total = 0;
    S.costs.filter(k => k.clientId == cid && k.due == PERIOD)
      .sort((a, b) => a.date.localeCompare(b.date) || a.id - b.id)
      .forEach(k => { if (total + k.amount <= cap) total += k.amount; else k.due = nextMonth(k.due); });
    n++;
  });
  selected.clear(); save(); renderHome();
  toast(n ? `Rolled over ${n} client${n > 1 ? 's' : ''}.` : 'No red-flagged clients to roll over.', n ? 'success' : 'info');
}
const rollSel = () => rollover([...selected]);
const rollAll = () => rollover(S.clients.filter(c => stats(c).red).map(c => c.id));

/* ---------- PDF reports ---------- */
// Set REPORT_URL to use your Django report view instead of the in-browser PDF, e.g.
//   const REPORT_URL = id => `/reports/clients/${id}/download/`;
const REPORT_URL = null;
const loadPDF = () => window.jspdf ? Promise.resolve() : new Promise((ok, fail) => {
  const el = document.createElement('script');
  el.src = 'https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js';
  el.onload = ok; el.onerror = () => fail(new Error('Could not load the PDF library. Check your internet connection.'));
  document.head.appendChild(el);
});
function table(doc, title, heads, xs, al, rows, tot) {
  doc.addPage(); let y = 60;
  doc.setFont('helvetica', 'bold').setFontSize(14); doc.text(title, 54, y); y += 28;
  const line = (cells, b) => {
    if (y > 730) { doc.addPage(); y = 60; }
    doc.setFont('helvetica', b ? 'bold' : 'normal').setFontSize(10);
    cells.forEach((t, i) => doc.text(String(t), xs[i], y, { align: al[i] === 'r' ? 'right' : 'left' }));
    y += 18;
  };
  line(heads, 1); rows.forEach(r => line(r)); if (tot) { y += 6; line(tot, 1); }
}
async function makeReport(c, download = true) {
  if (c.rate == null) return false;                  // blocked until a commission rate is set
  if (REPORT_URL) {                                  // backend builds the PDF
    const a = document.createElement('a'); a.href = REPORT_URL(c.id); a.click(); return true;
  }
  await loadPDF();
  const pm = PERIOD.slice(0, 7);
  const pays = S.payments.filter(x => x.clientId == c.id && x.date.slice(0, 7) == pm).sort((a, b) => a.date.localeCompare(b.date));
  const costs = S.costs.filter(x => x.clientId == c.id && x.due == PERIOD).sort((a, b) => a.date.localeCompare(b.date) || a.id - b.id);
  const st = stats(c), R = c.rate;
  const doc = new jspdf.jsPDF({ unit: 'pt', format: 'letter' });
  doc.setFont('helvetica', 'bold').setFontSize(18).text(FIRM.name, 54, 60);
  doc.setFont('helvetica', 'normal').setFontSize(11).text(FIRM.addr, 54, 78);
  doc.setFont('helvetica', 'bold').setFontSize(15).text('Remittance Report', 54, 130);
  doc.setFont('helvetica', 'normal').setFontSize(12).text(`Client: ${c.name}`, 54, 155).text(`Reporting period: ${label(PERIOD)}`, 54, 173);
  [['Gross Recoveries', st.rec], ['Less Costs', -st.cost], ['Net Recoveries', st.rec - st.cost], [`Less Commission at ${R}%`, -st.comm], ['Net Remit to Client', st.net]]
    .forEach(([t, v], i) => {
      const y = 220 + i * 26;
      doc.setFont('helvetica', i == 4 || i == 2 ? 'bold' : 'normal').text(t, 54, y).text(money(v), 558, y, { align: 'right' });
    });
  const cm = a => Math.round(a * R / 100);
  table(doc, 'Payment Statement', ['Debtor', 'Date', 'Amount', `Commission (${R}%)`, 'Owed to Client'], [54, 250, 380, 470, 558], ['l', 'l', 'r', 'r', 'r'],
    pays.map(p => [p.debtor, mdy(p.date), money(p.amount), money(cm(p.amount)), money(p.amount - cm(p.amount))]),
    ['Totals', '', money(st.rec), money(pays.reduce((a, p) => a + cm(p.amount), 0)), money(pays.reduce((a, p) => a + p.amount - cm(p.amount), 0))]);
  table(doc, 'Billed Cost Statement', ['Debtor', 'Date', 'Description', 'Amount'], [54, 230, 310, 558], ['l', 'l', 'l', 'r'],
    costs.map(k => [k.debtor, mdy(k.date), k.desc.slice(0, 40), money(k.amount)]), ['Total', '', '', money(st.cost)]);
  costs.forEach(k => k.billed = true);
  S.reports = S.reports.filter(r => !(r.clientId == c.id && r.period == PERIOD));   // unique (ClientID, ReportPeriod)
  const data = doc.output('datauristring');
  S.reports.push({ clientId: c.id, period: PERIOD, data });
  save();
  if (download) {
    const a = document.createElement('a');
    a.href = data; a.download = `${c.name.replace(/\W+/g, '_')}_${pm}.pdf`; a.click();
  }
  return true;
}
async function genAll() {
  const rows = pageRows(), blocked = [];
  for (const c of rows) {
    try { if (!(await makeReport(c))) blocked.push(c.name); }
    catch (e) { toast(e.message, 'error'); return; }
    await new Promise(r => setTimeout(r, 400));      // space out downloads so the browser allows them all
  }
  toast(blocked.length ? `Reports blocked until a commission rate is set for: ${blocked.join(', ')}` : 'Reports generated.', blocked.length ? 'error' : 'success');
  renderHome();
}

/* ---------- CSV import ---------- */
function parseCSV(t) {
  const rows = []; let r = [], f = '', q = false;
  for (let i = 0; i < t.length; i++) {
    const ch = t[i];
    if (q) { if (ch == '"' && t[i + 1] == '"') { f += '"'; i++; } else if (ch == '"') q = false; else f += ch; }
    else if (ch == '"') q = true;
    else if (ch == ',') { r.push(f); f = ''; }
    else if (ch == '\n' || ch == '\r') { if (ch == '\r' && t[i + 1] == '\n') i++; r.push(f); f = ''; if (r.some(x => x.trim())) rows.push(r); r = []; }
    else f += ch;
  }
  if (f || r.length) { r.push(f); rows.push(r); }
  return rows;
}
function toISO(s) {
  s = s.trim();
  let m = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/); if (m) return `${m[3]}-${pad(m[1])}-${pad(m[2])}`;
  m = s.match(/^(\d{4})-(\d{2})-(\d{2})/); return m ? m[0] : null;
}
function importCSV(text) {
  // columns: Client Full Name, Account Number, Debtor, Is Payment, Date, Amount, Description
  const rows = parseCSV(text); let added = 0, bad = 0, newC = 0;
  rows.forEach((r, idx) => {
    const amt = parseFloat((r[5] || '').replace(/[$,]/g, '')), date = toISO(r[4] || '');
    if (isNaN(amt) || !date || !r[0]?.trim()) { if (idx > 0) bad++; return; }   // skips header row
    let c = S.clients.find(x => norm(x.name) == norm(r[0]));
    if (!c) { c = { id: id(), name: r[0].trim().replace(/\s+/g, ' '), rate: null, created: iso(new Date()) }; S.clients.push(c); newC++; }
    const num = (r[1] || '').trim();
    if (!S.accounts.some(a => a.clientId == c.id && a.number == num)) S.accounts.push({ id: id(), clientId: c.id, number: num });
    const base = { id: id(), clientId: c.id, acct: num, date, amount: Math.round(amt * 100), debtor: (r[2] || '').trim() };
    if (/^(1|true|yes|y|t)$/i.test((r[3] || '').trim())) S.payments.push(base);
    else S.costs.push({ ...base, billed: false, desc: (r[6] || '').trim(), due: date.slice(0, 7) + '-01' });
    added++;
  });
  save(); renderHome();
  toast(`Imported ${added} transactions, ${newC} new clients${bad ? `, ${bad} rows skipped` : ''}.`, added ? 'success' : 'error');
}

/* ---------- Dashboard (home.html) ---------- */
const selected = new Set();
let page = 0;
const sortedRows = () => S.clients.map(c => ({ c, s: stats(c) })).sort((a, b) => b.s.rec - a.s.rec);
const pageRows = () => sortedRows().slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE).map(x => x.c);

function renderHome() {
  const all = sortedRows(), pages = Math.max(1, Math.ceil(all.length / PAGE_SIZE));
  page = Math.min(page, pages - 1);
  const rows = all.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  $('#clientTableBody').innerHTML = rows.map(({ c, s }) => `<tr data-client-id="${c.id}" data-recoveries="${s.rec / 100}" data-costs="${s.cost / 100}" data-commission-rate="${c.rate ?? ''}">
    <td class="checkbox-column"><input class="client-checkbox" type="checkbox" data-id="${c.id}" aria-label="Select ${esc(c.name)}" ${selected.has(c.id) ? 'checked' : ''}></td>
    <td><a href="/client/?id=${c.id}">${esc(c.name)}</a></td>
    <td class="money">${money(s.rec)}</td>
    <td class="money cost-value ${s.red ? 'cost-flagged' : ''}" data-cost="${s.cost / 100}" data-recovery="${s.rec / 100}">${money(s.cost)}</td>
    ${c.rate == null ? '<td class="missing-value">Not Set</td><td>&mdash;</td>' : `<td class="money">${money(s.comm)}</td><td class="money">${money(s.net)}</td>`}</tr>`).join('')
    || '<tr><td colspan="6">No clients yet. Press Import Client Data to begin.</td></tr>';
  $('#pageIndicator').textContent = `${page + 1} of ${pages}`;
  $('#previousPageBtn').disabled = page == 0;
  $('#nextPageBtn').disabled = page >= pages - 1;
  $('#generateAllReportsBtn').disabled = !rows.length;
}
function initHome() {
  $('#reportingPeriodText').textContent = `Showing clients for ${label(PERIOD).replace(',', '')}`;
  $('#importClientDataBtn').addEventListener('click', () => $('#csvFileInput').click());
  $('#csvFileInput').addEventListener('change', async e => {
    const file = e.target.files[0]; if (!file) return;
    importCSV(await file.text()); e.target.value = '';
  });
  $('#rolloverSelectedBtn').addEventListener('click', rollSel);
  $('#rolloverAllBtn').addEventListener('click', rollAll);
  $('#generateAllReportsBtn').addEventListener('click', genAll);
  $('#previousPageBtn').addEventListener('click', () => { page--; renderHome(); });
  $('#nextPageBtn').addEventListener('click', () => { page++; renderHome(); });
  $('#clientTableBody').addEventListener('change', e => {
    const cb = e.target.closest('.client-checkbox'); if (!cb) return;
    cb.checked ? selected.add(+cb.dataset.id) : selected.delete(+cb.dataset.id);
  });
  renderHome();
}

/* ---------- Sample data (delete this block when wired to MySQL) ---------- */
function seed() {
  const m = PERIOD.slice(0, 7), d = n => `${m}-${pad(n)}`;
  [['Northgate Medical Group', 25, [[900000, 3], [400000, 9]], [[150000, 2], [180000, 5], [120000, 11]]],
   ['Bayou City Credit Union', 20, [[1250000, 4]], [[80000, 3], [60000, 8]]],
   ['Summit Property Mgmt', null, [[300000, 6]], [[90000, 4]]],
   ['Lone Star Utilities', 30, [], [[25000, 2]]]].forEach(([name, rate, p, k], i) => {
    const c = { id: i + 1, name, rate, created: iso(new Date()) }; S.clients.push(c);
    S.accounts.push({ id: i + 1, clientId: c.id, number: `AC-${1000 + i}` });
    p.forEach(([a, day]) => S.payments.push({ id: id(), clientId: c.id, acct: `AC-${1000 + i}`, date: d(day), amount: a, debtor: 'Debtor ' + day }));
    k.forEach(([a, day]) => S.costs.push({ id: id(), clientId: c.id, acct: `AC-${1000 + i}`, date: d(day), amount: a, billed: false, desc: 'Court filing fee', due: m + '-01', debtor: 'Debtor ' + day }));
  });
}
if (!load()) { seed(); save(); }
if ($('#clientTableBody')) initHome();   // home.html loads this file with defer, so the table already exists