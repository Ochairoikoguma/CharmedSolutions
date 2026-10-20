# Charmed Solutions

## Development setup

Requires Python 3.14 and Git.

After cloning the repository, run these commands from its root folder:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe backend/manage.py migrate
.\.venv\Scripts\python.exe backend/manage.py runserver
```

Open http://127.0.0.1:8000/.

## Project structure

- backend/accounting: application logic and database models
- backend/config: Django settings and URL configuration
- backend/templates: HTML pages
- backend/static/css: stylesheets
- backend/static/js: JavaScript

## Team workflow

Work on your assigned branch. Commit and push changes, then open a pull
request into main for review.

Do not commit passwords, client data, local databases, or virtual environments.

## Current status

Starter Django application with a working homepage.
Business features are not implemented yet.
The starter configuration uses SQLite for local development.
