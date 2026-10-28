# Charmed Solutions

## Windows Development setup

Requires Python 3.14 and Git.

Open the project in VS Code, then select Terminal → New Terminal.
Use PowerShell and make sure you are in the project's root folder
(`CharmedSolutions`).

### First-time setup

Check that Python 3.14 and Git are installed:

```powershell
py -3.14 --version
git --version
```

Create a virtual environment:

```powershell
py -3.14 -m venv .venv
```

Install the project dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Apply database migrations:

```powershell
.\.venv\Scripts\python.exe backend/manage.py migrate
```

Start the development server:

```powershell
.\.venv\Scripts\python.exe backend/manage.py runserver
```

Open http://127.0.0.1:8000/ in your browser.

Press Ctrl + C in the terminal to stop the server.


### Running the project again

From the project's root folder:

```powershell
.\.venv\Scripts\python.exe backend/manage.py runserver
```

You do not need to recreate the virtual environment each time.

### Updating dependencies

After pulling changes that update requirements.txt, run:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Applying database updates

After pulling changes that include new Django migrations, run:

```powershell
.\.venv\Scripts\python.exe backend/manage.py migrate
```

---------------------------------------------------------------------------

## MAC OS development setup

Requires Python 3.14 and Git.

Open Terminal in the project's root folder (`CharmedSolutions`).

### First-time setup

Create a virtual environment:

```bash
python3.14 -m venv .venv
```

Install the project dependencies:

```bash
./.venv/bin/python -m pip install -r requirements.txt
```

Apply database migrations:

```bash
./.venv/bin/python backend/manage.py migrate
```

Start the development server:

```bash
./.venv/bin/python backend/manage.py runserver
```

Open http://127.0.0.1:8000/ in your browser.
Press Control + C in Terminal to stop the server.

### Running the project again

From the project's root folder:

```bash
./.venv/bin/python backend/manage.py runserver
```

### Updating dependencies

After pulling changes that update requirements.txt, run:

```bash
./.venv/bin/python -m pip install -r requirements.txt
```

Each developer creates their own virtual environment. Do not commit
the .venv folder to Git.

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
