# Charmed Solutions

Regent & Associates monthly remittance application built with Django, MySQL, and ReportLab. The browser interface supports CSV imports, client commission rates, monthly dashboard totals, cost rollover, PDF reports, report history, and confirmed client deletion.

## Development prerequisites

- Python 3.14 and Git; VS Code is optional.
- Access to the team's MySQL server and the `remittance` database.
- Database password supplied privately by the team; never put it in this repository, a README, or a committed configuration file.
- Run all commands from the `CharmedSolutions` repository root. Each developer creates their own `.venv`.

The current settings select MySQL only when `MYSQL_HOST` is set. Otherwise Django falls back to SQLite, which does not contain the accounting tables. Installing `python-dotenv` alone does not load an `.env` file; the current settings read process environment variables.

## Windows PowerShell

### First-time dependency setup

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Connect and run (each new terminal session)

```powershell
$env:MYSQL_HOST = "cis4375fall26.cjluoecnlrur.us-east-1.rds.amazonaws.com"
$env:MYSQL_PORT = "3306"
$env:MYSQL_DATABASE = "remittance"
$env:MYSQL_USER = "admincharmed"
$credential = Get-Credential -UserName $env:MYSQL_USER -Message "Enter the MySQL password"
$env:MYSQL_PASSWORD = $credential.GetNetworkCredential().Password
Remove-Variable credential

.\.venv\Scripts\python.exe backend/manage.py shell -c "from django.db import connection; print('Database:', connection.vendor); print('Name:', connection.settings_dict['NAME'])"
.\.venv\Scripts\python.exe backend/manage.py check
.\.venv\Scripts\python.exe backend/manage.py runserver
```

The database check must print `mysql` and `remittance`. Open http://127.0.0.1:8000/ and keep the terminal running. Press Ctrl+C to stop. Restart the server after changing database environment variables. The password remains available only to this terminal session and its child processes; closing the terminal clears that session.

## macOS (Bash)

Open Terminal in the repository root. Run `bash` first for the password-prompt syntax below.

### First-time dependency setup

```bash
python3.14 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
```

`mysqlclient` may require MySQL client development libraries and build tools on the Mac. If installation fails, retain the error output for the team rather than changing the pinned dependency versions.

### Connect and run (each new terminal session)

```bash
export MYSQL_HOST='cis4375fall26.cjluoecnlrur.us-east-1.rds.amazonaws.com'
export MYSQL_PORT='3306'
export MYSQL_DATABASE='remittance'
export MYSQL_USER='admincharmed'
read -r -s -p 'MySQL password: ' MYSQL_PASSWORD
printf '\n'
export MYSQL_PASSWORD

./.venv/bin/python backend/manage.py shell -c "from django.db import connection; print('Database:', connection.vendor); print('Name:', connection.settings_dict['NAME'])"
./.venv/bin/python backend/manage.py check
./.venv/bin/python backend/manage.py runserver
```

Confirm `mysql` and `remittance`, then open http://127.0.0.1:8000/. Press Control+C to stop.

## Database setup and updates

The core accounting models map to existing MySQL tables and use `managed=False`. Django `migrate` does **not** create or update those accounting tables. A new database needs the team's reviewed SQL schema for `Client`, `CollectionAccount`, `Payment`, `Cost`, `Remittance`, and any other required core tables. Never rerun a destructive schema script against the populated shared database. `CollectionAccount.DebtorName` must support 255 characters.

The CSV import feature also needs `ImportBatch` and `ImportRow`. After configuring MySQL, run once per database:

```powershell
.\.venv\Scripts\python.exe backend/manage.py setup_import_tables
```

On macOS substitute `./.venv/bin/python`. The command creates missing import audit tables and skips existing ones; it does not validate or repair existing table definitions. On the team's current database these tables have already been set up.

Django's own authentication/session/admin tables, when needed, are created using `backend/manage.py migrate` after selecting the correct database. Coordinate schema changes on the shared database with the team.

## Application workflow

1. **Import Client Data:** upload a UTF-8 CSV containing one reporting month. The latest successful import determines the active dashboard month; there is no month selector.
2. **Clients:** set each client's commission percentage and save. Enter `25` for 25%, not `0.25`. Imported clients start with no commission rate.
3. **Dashboard:** review recoveries, applied costs, deferred costs, commission, and net remittance. Clients are displayed in pages of ten.
4. **Rollover:** the selected-client action processes selected clients; **Roll Over All** processes eligible clients across pages. Rollover defers excess costs without marking them billed. Original cost dates remain intact.
5. **Generate Selected Report:** select one client to download its monthly PDF. **Generate All Reports (This Page)** downloads a ZIP for clients on the visible page. Missing commission rates block creation of the affected batch before changes are committed.
6. **Report History:** open a client and download its saved monthly report. Existing reports reuse their original PDF and stored totals. Generation bills included costs and defers excess costs atomically; downloading saved PDFs does not bill again.
7. **Delete Client:** review the confirmation counts. Confirming permanently deletes that client's accounts, payments, costs, and saved reports. Import audit history remains with deletion metadata.

Reports download through the browser. Extract ZIP downloads into the desired folder yourself; the application does not automatically write a folder on the desktop.

### CSV format

Required headers (an optional first line containing `simplicity_export` is accepted):

```csv
Client Full Name,Account Number,Debtor First/Company Name,Trans. Is Payment,Trans. Date,Trans. Amount,Trans. Description Name
```

- `Trans. Is Payment`: `TRUE` for a payment, `FALSE` for a cost.
- Date format: `MM/DD/YYYY`; all transactions must share one month.
- Amount: nonnegative decimal with at most two decimal places; no currency symbols or thousands separators.
- Client name: at most 150 characters; account number: 20; debtor and description: 255.
- File size limit: 5 MB.
- Account numbers identify accounts and cannot be assigned to conflicting clients/debtors.
- Matching rows within the file remain distinct transactions. Reuploading a file before finalization can add the same transactions again: upload each export only once.
- Importing into a month with an existing report for an affected client is blocked to preserve the finalized report.

### Current calculation behavior

Costs are limited to 20% of monthly recoveries. Eligible unbilled costs are considered in original date and numeric ID order. An oversized cost is skipped while later fitting costs may be included; individual costs are not partially applied. Deferred costs carry forward.

Commission is calculated on each payment using the client's percentage, rounded to cents, then summed. Net remittance is recoveries minus commission minus applied costs. Confirm these implemented rules against the sponsor-approved requirements before final acceptance.

## Verification

Run in a terminal configured for MySQL:

```powershell
.\.venv\Scripts\python.exe backend/manage.py check
.\.venv\Scripts\python.exe backend/manage.py verify_csv_import
.\.venv\Scripts\python.exe backend/manage.py verify_dashboard_actions
.\.venv\Scripts\python.exe backend/manage.py verify_client_deletion
```

On macOS substitute `./.venv/bin/python`. These verification commands use temporary test records and roll back their data changes, restoring the active reporting month. MySQL auto-increment sequences can still advance, leaving harmless ID gaps. Run when teammates are not modifying the same database so count checks remain meaningful. A `Ran 0 tests` message from another test command is not evidence that a test suite passed.

Browser checks completed with two dedicated October 2026 test clients: import, rate saving, dashboard totals, individual PDF generation, saved PDF download. The saved Alpha download was byte-identical to its original. Temporary browser-test clients were deleted afterward. Automated checks also covered batch rollback, rollover rules, ZIP contents, saved-report reuse, and deletion isolation. These checks do not replace final requirements acceptance or a clean-machine installation check.

## Updating the application

Work on your assigned branch. Fetch and merge reviewed main changes, resolve conflicts, and commit/push through a pull request. After dependencies change, reinstall `requirements.txt` with the same environment's Python. Restart the server after Python changes; hard-refresh the browser after JavaScript changes.

Do not commit passwords, `.env`, `.venv`, real client exports, local databases, or generated reports.

## Troubleshooting

- **SQLite / no such table: Client:** configure all MySQL environment variables in the same terminal used to start Django; restart the process. Do not create replacement SQLite accounting tables.
- **MySQL table missing:** verify the database name is `remittance`. `collection_db.transactions` is a source-data table and does not replace the application's accounting schema.
- **Access denied / cannot connect:** verify the password, hostname, and approved network access with the database owner.
- **Import audit table missing:** run `setup_import_tables` after confirming the database connection.
- **main.js must be loaded before client.js:** save the HTML file, ensure main.js appears before client.js with separate script tags, then hard-refresh.
- **Commission Not Set:** save a valid commission rate on the client's page before generating a new report.
- **Stale reporting month:** refresh the dashboard after another successful import changes the active month.

## Project structure

- `backend/accounting/`: models, views, services, and verification commands.
- `backend/config/`: Django settings and routes.
- `backend/templates/`: HTML pages.
- `backend/static/`: CSS and JavaScript.

## Delivery status

The main import-to-report workflow has been exercised on the team's MySQL database. Remaining handoff work includes reviewing the requirements matrix against the final code, documenting any gaps, confirming the target-machine database arrangement, and checking installation on a teammate's clean environment. The checked-in configuration is a development configuration; the team's current RDS connection requires network access and is not an offline local database deployment.
